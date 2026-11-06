"""Fuel Consumption Analysis System - Flask REST backend (also serves ../frontend).

Run:  python app.py        ->  http://127.0.0.1:5000
DB :  SQLite by default. For MySQL set DATABASE_URL, e.g.
      mysql+pymysql://root:password@localhost/fuel_db
"""
import csv
import io
import os
import random
import tempfile
from datetime import date, timedelta

import pandas as pd
from flask import Flask, Response, jsonify, request
from flask_sqlalchemy import SQLAlchemy

import analysis

db = SQLAlchemy()


class Vehicle(db.Model):
    __tablename__ = "vehicles"
    vehicle_id = db.Column(db.Integer, primary_key=True)
    vehicle_code = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(30), nullable=False)
    fuel_type = db.Column(db.String(20), nullable=False)
    records = db.relationship("FuelRecord", cascade="all, delete-orphan", backref="vehicle")

    def to_dict(self):
        return {"vehicle_id": self.vehicle_id, "vehicle_code": self.vehicle_code, "vehicle_type": self.vehicle_type,
                "fuel_type": self.fuel_type, "record_count": len(self.records)}


class FuelRecord(db.Model):
    __tablename__ = "fuel_records"
    record_id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey("vehicles.vehicle_id"), nullable=False)
    fill_date = db.Column(db.Date, nullable=False)
    odometer_km = db.Column(db.Integer, nullable=False)
    litres = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    full_tank_flag = db.Column(db.Integer, nullable=False, default=1)


SAMPLE = [("CAR-01", "Hatchback", "Petrol", 17, 37, 105, 24800), ("BIKE-01", "Motorcycle", "Petrol", 52, 10, 105, 11200),
          ("SUV-01", "SUV", "Diesel", 12.5, 55, 92, 48650), ("VAN-01", "Van", "Diesel", 14, 45, 92, 63400)]


def reset_sample():
    """Replace all data with sample vehicles/records (includes a few deliberately invalid readings)."""
    db.session.query(FuelRecord).delete()
    db.session.query(Vehicle).delete()
    rng = random.Random(7)
    for code, vtype, fuel, eff, tank, price, odo in SAMPLE:
        v = Vehicle(vehicle_code=code, vehicle_type=vtype, fuel_type=fuel)
        db.session.add(v)
        db.session.flush()
        d, recs = date(2026, 6, 4), []
        for i in range(10):
            km = round(tank * eff * (.55 + rng.random() * .35))
            litres = round(km / (eff * (.92 + rng.random() * .16)), 2)
            odo += km
            d += timedelta(days=10 + rng.randint(0, 8))
            recs.append(FuelRecord(vehicle_id=v.vehicle_id, fill_date=d, odometer_km=odo, litres=litres,
                                   total_cost=round(litres * (price + rng.random() * 3)),
                                   full_tank_flag=0 if i in (3, 7) else 1))
        if code == "CAR-01": recs[5].odometer_km -= 900          # odometer goes backwards
        if code == "BIKE-01": recs[8].total_cost = 0             # zero cost
        if code == "SUV-01": recs[6].odometer_km = recs[5].odometer_km  # repeated reading
        if code == "VAN-01": recs[4].litres = 0                  # zero litres
        db.session.add_all(recs)
    db.session.commit()


def parse_record(data, rec=None):
    """Validate input types/ranges. Zero values are allowed on purpose: they are stored and flagged as invalid readings."""
    p = {}
    try:
        p["vehicle_id"] = int(data.get("vehicle_id", rec.vehicle_id if rec else None))
        p["fill_date"] = date.fromisoformat(str(data.get("fill_date", rec.fill_date.isoformat() if rec else "")))
        p["odometer_km"] = int(float(data.get("odometer_km", rec.odometer_km if rec else None)))
        p["litres"] = float(data.get("litres", rec.litres if rec else None))
        p["total_cost"] = float(data.get("total_cost", rec.total_cost if rec else None))
        p["full_tank_flag"] = 1 if int(data.get("full_tank_flag", rec.full_tank_flag if rec else 1)) else 0
    except (TypeError, ValueError):
        raise ValueError("Missing or invalid field (need vehicle_id, fill_date YYYY-MM-DD, odometer_km, litres, total_cost)")
    if min(p["odometer_km"], p["litres"], p["total_cost"]) < 0:
        raise ValueError("Odometer, litres and cost cannot be negative")
    if not db.session.get(Vehicle, p["vehicle_id"]):
        raise ValueError("Vehicle does not exist")
    return p


def default_db_uri():
    """DATABASE_URL (Postgres/MySQL on a host) or a SQLite file. Fixes the URL prefixes hosts commonly give."""
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    elif url.startswith("mysql://"):
        url = "mysql+pymysql://" + url[len("mysql://"):]
    if url:
        return url
    here = os.path.dirname(os.path.abspath(__file__))
    folder = here if os.access(here, os.W_OK) else tempfile.gettempdir()  # read-only hosts -> /tmp
    return "sqlite:///" + os.path.join(folder, "fuel.db").replace("\\", "/")


def create_app(db_uri=None):
    frontend = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")
    app = Flask(__name__, static_folder=frontend, static_url_path="")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri or default_db_uri()
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    db.init_app(app)
    with app.app_context():
        db.create_all()
        if not Vehicle.query.first():
            reset_sample()

    def frames():
        v = pd.DataFrame([{"vehicle_id": x.vehicle_id, "vehicle_code": x.vehicle_code, "vehicle_type": x.vehicle_type,
                           "fuel_type": x.fuel_type} for x in Vehicle.query.all()],
                         columns=["vehicle_id", "vehicle_code", "vehicle_type", "fuel_type"])
        r = pd.DataFrame([{"record_id": x.record_id, "vehicle_id": x.vehicle_id, "fill_date": x.fill_date,
                           "odometer_km": x.odometer_km, "litres": x.litres, "total_cost": x.total_cost,
                           "full_tank_flag": x.full_tank_flag} for x in FuelRecord.query.all()],
                         columns=["record_id", "vehicle_id", "fill_date", "odometer_km", "litres", "total_cost", "full_tank_flag"])
        r["fill_date"] = pd.to_datetime(r["fill_date"])
        return v, r

    def analysed():
        return analysis.analyse(*frames())

    inc = lambda: request.args.get("include_approx") == "1"

    @app.errorhandler(ValueError)
    def bad_request(e):
        return jsonify(error=str(e)), 400

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    # ---- vehicles ----
    @app.get("/api/vehicles")
    def list_vehicles():
        return jsonify([v.to_dict() for v in Vehicle.query.order_by(Vehicle.vehicle_id)])

    @app.post("/api/vehicles")
    def add_vehicle():
        d = request.get_json(silent=True) or {}
        code, vtype, fuel = (str(d.get(k, "")).strip() for k in ("vehicle_code", "vehicle_type", "fuel_type"))
        if not (code and vtype and fuel):
            raise ValueError("vehicle_code, vehicle_type and fuel_type are required")
        if Vehicle.query.filter_by(vehicle_code=code).first():
            raise ValueError(f"Vehicle code {code} already exists")
        v = Vehicle(vehicle_code=code, vehicle_type=vtype, fuel_type=fuel)
        db.session.add(v)
        db.session.commit()
        return jsonify(v.to_dict()), 201

    @app.delete("/api/vehicles/<int:vid>")
    def delete_vehicle(vid):
        v = db.get_or_404(Vehicle, vid)
        db.session.delete(v)
        db.session.commit()
        return jsonify(deleted=vid)

    # ---- fuel records ----
    @app.get("/api/records")
    def list_records():
        return jsonify(analysis.records_out(analysed()))

    @app.post("/api/records")
    def add_record():
        r = FuelRecord(**parse_record(request.get_json(silent=True) or {}))
        db.session.add(r)
        db.session.commit()
        return jsonify(record_id=r.record_id), 201

    @app.put("/api/records/<int:rid>")
    def update_record(rid):
        r = db.get_or_404(FuelRecord, rid)
        for k, val in parse_record(request.get_json(silent=True) or {}, r).items():
            setattr(r, k, val)
        db.session.commit()
        return jsonify(record_id=rid)

    @app.delete("/api/records/<int:rid>")
    def delete_record(rid):
        db.session.delete(db.get_or_404(FuelRecord, rid))
        db.session.commit()
        return jsonify(deleted=rid)

    # ---- analysis ----
    @app.get("/api/dashboard")
    def dashboard():
        return jsonify(analysis.dashboard(analysed(), inc()))

    @app.get("/api/reports")
    def reports():
        return jsonify(analysis.reports(analysed(), inc()))

    @app.get("/api/history/<int:vid>")
    def history(vid):
        v = db.get_or_404(Vehicle, vid)
        h = analysis.history(analysed(), vid, request.args.get("record_id", 0, type=int))
        h["vehicle"] = {k: getattr(v, k) for k in ("vehicle_id", "vehicle_code", "vehicle_type", "fuel_type")}
        return jsonify(h)

    @app.get("/api/export/<name>.csv")
    def export(name):
        rep = analysis.reports(analysed(), inc())
        if name == "mileage":
            data = rep["mileage"]
        elif name == "invalid":
            data = rep["invalid"]
        elif name == "expenses":
            data = [{"month": r["month"], **r["costs"], "total_cost": r["total_cost"], "total_litres": r["total_litres"]}
                    for r in rep["expenses"]["rows"]]
        else:
            return jsonify(error="Unknown report"), 404
        buf = io.StringIO()
        if data:
            w = csv.DictWriter(buf, fieldnames=list(data[0].keys()))
            w.writeheader()
            w.writerows(data)
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={name}_report.csv"})

    @app.post("/api/reset-sample")
    def reset():
        reset_sample()
        return jsonify(ok=True)

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
