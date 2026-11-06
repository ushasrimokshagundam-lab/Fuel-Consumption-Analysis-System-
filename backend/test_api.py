import os, tempfile, unittest
from app import create_app

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.f = tempfile.NamedTemporaryFile(suffix=".db", delete=False); self.f.close()
        self.c = create_app("sqlite:///" + self.f.name).test_client()
    def tearDown(self): os.unlink(self.f.name)

    def test_dashboard_and_reports(self):
        d = self.c.get("/api/dashboard").get_json()
        self.assertEqual(len(d["by_vehicle"]), 4); self.assertEqual(d["kpis"]["invalid"], 4)
        r = self.c.get("/api/reports").get_json()
        self.assertEqual(len(r["invalid"]), 4); self.assertEqual(r["mileage"][0]["rank"], 1)

    def test_crud_and_validation(self):
        v = self.c.post("/api/vehicles", json={"vehicle_code": "T-1", "vehicle_type": "Van", "fuel_type": "Diesel"})
        self.assertEqual(v.status_code, 201); vid = v.get_json()["vehicle_id"]
        self.assertEqual(self.c.post("/api/vehicles", json={"vehicle_code": "T-1", "vehicle_type": "x", "fuel_type": "y"}).status_code, 400)
        base = {"vehicle_id": vid, "fill_date": "2026-10-01", "litres": 10, "total_cost": 1000, "full_tank_flag": 1}
        self.assertEqual(self.c.post("/api/records", json={**base, "odometer_km": 1000}).status_code, 201)
        self.assertEqual(self.c.post("/api/records", json={**base, "fill_date": "2026-10-10", "odometer_km": 1200, "litres": 12}).status_code, 201)
        self.assertEqual(self.c.post("/api/records", json={**base, "odometer_km": "abc"}).status_code, 400)
        rows = [r for r in self.c.get("/api/records").get_json() if r["vehicle_id"] == vid]
        full = [r for r in rows if r["status"] == "full_tank"][0]
        self.assertAlmostEqual(full["mileage_kmpl"], 200 / 12)
        h = self.c.get(f"/api/history/{vid}").get_json(); self.assertEqual(h["summary"]["fills"], 2)
        self.assertEqual(self.c.delete(f"/api/vehicles/{vid}").status_code, 200)

    def test_export_and_static(self):
        self.assertIn("vehicle_code", self.c.get("/api/export/mileage.csv").get_data(as_text=True))
        self.assertEqual(self.c.get("/").status_code, 200)
        self.assertEqual(self.c.get("/js/app.js").status_code, 200)

if __name__ == "__main__": unittest.main()
