"""Fuel analysis engine (pandas / NumPy). Used by the Flask API.

full_tank   : distance between consecutive valid full-tank fills / all litres bought in between (accurate)
approximate : distance since previous valid reading / litres of a partial fill (estimate only)
invalid     : zero/missing litres, cost or odometer, or odometer not above previous valid reading
"""
import json
import numpy as np
import pandas as pd

COLS = ["record_id", "vehicle_id", "fill_date", "odometer_km", "litres", "total_cost", "full_tank_flag",
        "status", "reason", "distance_km", "interval_litres", "interval_cost",
        "vehicle_code", "vehicle_type", "fuel_type", "mileage_kmpl", "cost_per_km", "month"]


def ratio(a, b, nd=2):
    return round(float(a) / float(b), nd) if b else None


def rows(df):
    return json.loads(df.to_json(orient="records"))


def analyse(vehicles, records):
    if records.empty:
        return pd.DataFrame(columns=COLS)
    out = []
    for _, g in records.sort_values(["vehicle_id", "fill_date", "record_id"]).groupby("vehicle_id"):
        last = last_full = None
        lit_since = cost_since = 0.0
        for r in g.itertuples(index=False):
            d = r._asdict()
            d.update(status="", reason="", distance_km=np.nan, interval_litres=np.nan, interval_cost=np.nan)
            if not (r.litres > 0 and r.total_cost > 0 and r.odometer_km > 0):
                d.update(status="invalid", reason="Litres, cost or odometer is zero/missing")
            elif last is not None and r.odometer_km <= last:
                d.update(status="invalid", reason=f"Odometer {r.odometer_km} km not above previous valid reading ({last} km)")
            else:
                gap = None if last is None else r.odometer_km - last
                lit_since += r.litres
                cost_since += r.total_cost
                if r.full_tank_flag == 1:
                    if last_full is None:
                        d["status"] = "baseline"
                    else:
                        d.update(status="full_tank", distance_km=r.odometer_km - last_full,
                                 interval_litres=lit_since, interval_cost=cost_since)
                    last_full, lit_since, cost_since = r.odometer_km, 0.0, 0.0
                elif gap is not None:
                    d.update(status="approximate", distance_km=gap, interval_litres=r.litres, interval_cost=r.total_cost)
                else:
                    d["status"] = "baseline"
                last = r.odometer_km
            out.append(d)
    df = pd.DataFrame(out).merge(vehicles, on="vehicle_id")
    df["mileage_kmpl"] = np.divide(df["distance_km"], df["interval_litres"])
    df["cost_per_km"] = np.divide(df["interval_cost"], df["distance_km"])
    df["month"] = df["fill_date"].dt.to_period("M").astype(str)
    return df


def _tot(s):
    return s["distance_km"].sum(), s["interval_litres"].sum(), s["interval_cost"].sum()


def _kinds(inc):
    return ["full_tank"] + (["approximate"] if inc else [])


def records_out(df):
    if df.empty:
        return []
    d = df.copy()
    d["fill_date"] = d["fill_date"].dt.strftime("%Y-%m-%d")
    d = d.sort_values(["fill_date", "record_id"], ascending=False)
    return rows(d[COLS])


def dashboard(df, inc=False):
    if df.empty:
        return {"kpis": {"fleet_mileage": None, "total_spend": 0, "cost_per_km": None, "best_vehicle": None,
                         "best_mileage": None, "records": 0, "invalid": 0},
                "by_vehicle": [], "months": [], "monthly_mileage": {}, "monthly_cost": {}}
    valid, use = df[df.status != "invalid"], df[df.status.isin(_kinds(inc))]
    d, l, c = _tot(use)
    by = []
    for code, g in use.groupby("vehicle_code"):
        gd, gl, gc = _tot(g)
        by.append({"code": code, "mileage": ratio(gd, gl), "cpk": ratio(gc, gd)})
    best = max(by, key=lambda x: x["mileage"], default=None)
    months = sorted(valid["month"].unique().tolist())
    codes = df.drop_duplicates("vehicle_id").sort_values("vehicle_id")["vehicle_code"].tolist()
    mm, mc = {}, {}
    for code in codes:
        mm[code], mc[code] = [], []
        for m in months:
            gd, gl, _ = _tot(use[(use.vehicle_code == code) & (use.month == m)])
            mm[code].append(ratio(gd, gl))
            mc[code].append(round(float(valid[(valid.vehicle_code == code) & (valid.month == m)]["total_cost"].sum())))
    return {"kpis": {"fleet_mileage": ratio(d, l), "total_spend": round(float(valid["total_cost"].sum())),
                     "cost_per_km": ratio(c, d), "best_vehicle": best and best["code"],
                     "best_mileage": best and best["mileage"], "records": len(df),
                     "invalid": int((df.status == "invalid").sum())},
            "by_vehicle": by, "months": months, "monthly_mileage": mm, "monthly_cost": mc}


def reports(df, inc=False):
    if df.empty:
        return {"mileage": [], "expenses": {"codes": [], "rows": []}, "invalid": []}
    mil = []
    for code, g in df.groupby("vehicle_code"):
        fd, fl, fc = _tot(g[g.status.isin(_kinds(inc))])
        ad, al, _ = _tot(g[g.status == "approximate"])
        mil.append({"vehicle_code": code, "fuel_type": g.fuel_type.iloc[0], "vehicle_type": g.vehicle_type.iloc[0],
                    "mileage_kmpl": ratio(fd, fl), "cost_per_km": ratio(fc, fd), "distance_km": round(float(fd)),
                    "intervals": int(g.status.isin(_kinds(inc)).sum()),
                    "approx_mileage_kmpl": ratio(ad, al), "approx_intervals": int((g.status == "approximate").sum())})
    mil.sort(key=lambda x: x["mileage_kmpl"] or 0, reverse=True)
    for i, m in enumerate(mil, 1):
        m["rank"] = i if m["mileage_kmpl"] else None
    valid = df[df.status != "invalid"]
    codes = df.drop_duplicates("vehicle_id").sort_values("vehicle_id")["vehicle_code"].tolist()
    exp = []
    for m, g in valid.groupby("month"):
        exp.append({"month": m, "costs": {c: round(float(g[g.vehicle_code == c]["total_cost"].sum())) for c in codes},
                    "total_cost": round(float(g["total_cost"].sum())), "total_litres": round(float(g["litres"].sum()), 1)})
    bad = df[df.status == "invalid"].copy()
    bad["fill_date"] = bad["fill_date"].dt.strftime("%Y-%m-%d")
    return {"mileage": mil, "expenses": {"codes": codes, "rows": exp},
            "invalid": rows(bad[["record_id", "vehicle_code", "fill_date", "odometer_km", "litres", "total_cost", "reason"]])}


def history(df, vid, record_id=0):
    rs = df[df.vehicle_id == vid].sort_values(["fill_date", "record_id"]) if not df.empty else df
    if rs.empty:
        return {"summary": None, "records": [], "selected": False}
    valid = rs[rs.status != "invalid"]
    d, l, c = _tot(rs[rs.status == "full_tank"])
    summary = {"fills": len(rs), "litres": round(float(valid.litres.sum()), 1), "spend": round(float(valid.total_cost.sum())),
               "span": int(valid.odometer_km.max() - valid.odometer_km.min()) if len(valid) else None,
               "mileage": ratio(d, l), "cpk": ratio(c, d), "invalid": int((rs.status == "invalid").sum())}
    sel = rs[rs.record_id == record_id] if record_id else rs
    return {"summary": summary, "records": records_out(sel)[::-1], "selected": bool(record_id)}
