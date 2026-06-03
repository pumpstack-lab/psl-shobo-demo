import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app as flask_app, init_db

@pytest.fixture
def client(tmp_path):
    db_path = str(tmp_path / "test.db")
    flask_app.config["TESTING"] = True
    import app as app_module
    orig = app_module.DB_PATH
    app_module.DB_PATH = db_path
    with flask_app.app_context():
        init_db()
    with flask_app.test_client() as c:
        yield c
    app_module.DB_PATH = orig


class TestRoutes:
    def test_dashboard(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "PumpStack Lab" in r.data.decode()

    def test_property_new(self, client):
        r = client.get("/property/new")
        assert r.status_code == 200

    def test_property_history(self, client):
        r = client.get("/property/1/history")
        assert r.status_code == 200

    def test_property_history_notfound(self, client):
        r = client.get("/property/9999/history")
        assert r.status_code == 404

    def test_inspect_extinguisher(self, client):
        r = client.get("/inspect/1?type=extinguisher")
        assert r.status_code == 200
        assert "消火器" in r.data.decode()

    def test_inspect_fire_alarm(self, client):
        r = client.get("/inspect/1?type=fire_alarm")
        assert r.status_code == 200
        assert "自動火災報知設備" in r.data.decode()

    def test_inspect_guidance_light(self, client):
        r = client.get("/inspect/1?type=guidance_light")
        assert r.status_code == 200
        assert "誘導灯" in r.data.decode()

    def test_inspect_hydrant(self, client):
        r = client.get("/inspect/1?type=hydrant")
        assert r.status_code == 200
        assert "屋内消火栓" in r.data.decode()

    def test_inspect_invalid_type_returns_empty_form(self, client):
        r = client.get("/inspect/1?type=invalid")
        assert r.status_code == 200


class TestInspectionPost:
    def _post_inspection(self, client, equip_type, extra_fields=None):
        data = {
            "inspected_at": "2026-06-04",
            "inspector_name": "テスト太郎",
            "inspector_num": "第12345号",
            "period_from": "R6.1.1",
            "period_to": "R6.6.30",
            "count": "1",
            "equipment_type": equip_type,
            "location_1": "1F廊下",
            "outer_1": "正常",
            "judgment_1": "適",
            "note_1": "",
        }
        if extra_fields:
            data.update(extra_fields)
        return client.post("/inspect/1", data=data, follow_redirects=False)

    def test_post_extinguisher(self, client):
        r = self._post_inspection(client, "extinguisher", {
            "type_1": "粉末ABC型", "capacity_1": "ABC-3",
            "year_1": "2020", "pressure_1": "0.85"
        })
        assert r.status_code == 302

    def test_post_fire_alarm_saves_extra_data(self, client):
        r = self._post_inspection(client, "fire_alarm", {
            "device_type_1": "差動式感知器",
            "detach_1": "なし",
            "dirt_1": "正常",
            "action_test_1": "正常",
        })
        assert r.status_code == 302
        token = r.headers["Location"].split("/")[-1]
        r2 = client.get(f"/report/{token}")
        body = r2.data.decode()
        assert "自動火災報知設備" in body
        assert "作動試験" in body
        assert "差動式感知器" in body

    def test_post_guidance_light_saves_extra_data(self, client):
        r = self._post_inspection(client, "guidance_light", {
            "device_type_1": "避難口誘導灯",
            "light_1": "正常点灯",
            "battery_1": "正常",
        })
        assert r.status_code == 302
        token = r.headers["Location"].split("/")[-1]
        r2 = client.get(f"/report/{token}")
        body = r2.data.decode()
        assert "誘導灯" in body
        assert "点灯確認" in body

    def test_post_hydrant_saves_extra_data(self, client):
        r = self._post_inspection(client, "hydrant", {
            "device_type_1": "1号消火栓",
            "valve_1": "正常",
            "water_test_1": "正常",
        })
        assert r.status_code == 302
        token = r.headers["Location"].split("/")[-1]
        r2 = client.get(f"/report/{token}")
        body = r2.data.decode()
        assert "屋内消火栓" in body
        assert "放水試験" in body


class TestEquipmentTypes:
    def test_four_types_seeded(self, client):
        import sqlite3
        import app as app_module
        db = sqlite3.connect(app_module.DB_PATH)
        ids = [r[0] for r in db.execute("SELECT id FROM equipment_types ORDER BY sort_order").fetchall()]
        db.close()
        assert ids == ["extinguisher", "fire_alarm", "guidance_light", "hydrant"]

    def test_check_schema_valid_json(self, client):
        import sqlite3, json
        import app as app_module
        db = sqlite3.connect(app_module.DB_PATH)
        for row in db.execute("SELECT id, check_schema FROM equipment_types").fetchall():
            schema = json.loads(row[1])
            assert "fields" in schema
            assert len(schema["fields"]) > 0
        db.close()
