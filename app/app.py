from flask import Flask, render_template, request, redirect, url_for, abort, g
import sqlite3, os, uuid, json
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "demo-psl-2026")
DB_PATH = os.path.join(os.path.dirname(__file__), "shobo.db")

EXTINGUISHER_TYPES = ["粉末ABC型", "粉末BC型", "強化液型", "化学泡型", "機械泡型", "CO2型", "ハロン型", "水型"]
CHECK_OPTIONS = {
    "outer":      ["正常", "変形", "腐食", "損傷"],
    "safety_pin": ["正常", "脱落", "変形", "破れ"],
    "body":       ["正常", "変形", "腐食", "損傷"],
    "cap":        ["正常", "変形", "腐食"],
    "hose":       ["正常", "変形", "詰まり", "損傷"],
}

# ─── DB ──────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db: db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS properties (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        owner_name TEXT,
        owner_contact TEXT,
        last_inspected DATE,
        next_inspection DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS inspections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        property_id INTEGER NOT NULL,
        inspector_name TEXT,
        inspector_num TEXT,
        inspected_at DATE,
        period_from TEXT,
        period_to TEXT,
        share_token TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (property_id) REFERENCES properties(id)
    );
    CREATE TABLE IF NOT EXISTS inspection_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inspection_id INTEGER NOT NULL,
        no INTEGER,
        location TEXT,
        type TEXT,
        capacity TEXT,
        year TEXT,
        outer TEXT,
        safety_pin TEXT,
        body TEXT,
        cap TEXT,
        hose TEXT,
        pressure TEXT,
        judgment TEXT,
        note TEXT,
        FOREIGN KEY (inspection_id) REFERENCES inspections(id)
    );
    CREATE TABLE IF NOT EXISTS equipment_types (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        check_schema TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    );
    """)
    # デモ用サンプル物件
    count = db.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
    if count == 0:
        today = date.today()
        samples = [
            ("渋谷第一ビル", "東京都渋谷区道玄坂1-2-3", "田中商事株式会社", "tanaka@example.com",
             str(today - timedelta(days=10)), str(today + timedelta(days=170))),
            ("新宿グランドマンション", "東京都新宿区西新宿2-5-10", "新宿管理組合", "shinjuku@example.com",
             str(today - timedelta(days=195)), str(today - timedelta(days=15))),
            ("品川オフィスタワー", "東京都品川区港南3-1-1", "品川開発株式会社", "shinagawa@example.com",
             str(today - timedelta(days=160)), str(today + timedelta(days=20))),
            ("池袋ショッピングモール", "東京都豊島区東池袋1-8-2", "池袋商業施設管理", "ikebukuro@example.com",
             None, None),
        ]
        for s in samples:
            db.execute(
                "INSERT INTO properties (name,address,owner_name,owner_contact,last_inspected,next_inspection) VALUES (?,?,?,?,?,?)",
                s)
    migrate_equipment_type_col(db)
    seed_equipment_types(db)
    db.commit()
    db.close()


def migrate_equipment_type_col(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(inspection_items)").fetchall()]
    if "equipment_type" not in cols:
        db.execute("ALTER TABLE inspection_items ADD COLUMN equipment_type TEXT DEFAULT 'extinguisher'")
    if "extra_data" not in cols:
        db.execute("ALTER TABLE inspection_items ADD COLUMN extra_data TEXT DEFAULT '{}'")


EQUIPMENT_TYPES = [
    {
        "id": "extinguisher",
        "name": "消火器",
        "sort_order": 0,
        "check_schema": '{"fields":[{"key":"location","label":"設置場所","type":"text","placeholder":"例）1F廊下"},{"key":"type","label":"種別","type":"select","options":["粉末ABC型","粉末BC型","強化液型","化学泡型","機械泡型","CO2型","ハロン型","水型"]},{"key":"capacity","label":"能力単位","type":"text","placeholder":"ABC-3"},{"key":"year","label":"製造年","type":"text","placeholder":"2020"},{"key":"outer","label":"外形","type":"select","options":["正常","変形","腐食","損傷"]},{"key":"safety_pin","label":"安全栓・封板","type":"select","options":["正常","脱落","変形","破れ"]},{"key":"body","label":"本体容器","type":"select","options":["正常","変形","腐食","損傷"]},{"key":"cap","label":"キャップ","type":"select","options":["正常","変形","腐食"]},{"key":"hose","label":"ホース・ノズル","type":"select","options":["正常","変形","詰まり","損傷"]},{"key":"pressure","label":"指示圧力値(MPa)","type":"text","placeholder":"0.85"},{"key":"note","label":"備考","type":"text","placeholder":"特記事項"}]}'
    },
    {
        "id": "fire_alarm",
        "name": "自動火災報知設備",
        "sort_order": 1,
        "check_schema": '{"fields":[{"key":"location","label":"設置場所","type":"text","placeholder":"例）2F会議室"},{"key":"device_type","label":"機器種別","type":"select","options":["差動式感知器","定温式感知器","光電式感知器","受信機","発信機","中継器"]},{"key":"outer","label":"外形・腐食","type":"select","options":["正常","変形","腐食","損傷"]},{"key":"detach","label":"脱落・未警戒","type":"select","options":["なし","脱落あり","未警戒あり"]},{"key":"dirt","label":"汚損・障害物","type":"select","options":["正常","汚損あり","障害物あり"]},{"key":"action_test","label":"作動試験","type":"select","options":["正常","異常","未実施"]},{"key":"note","label":"備考","type":"text","placeholder":"特記事項"}]}'
    },
    {
        "id": "guidance_light",
        "name": "誘導灯・非常照明",
        "sort_order": 2,
        "check_schema": '{"fields":[{"key":"location","label":"設置場所","type":"text","placeholder":"例）非常口上部"},{"key":"device_type","label":"種別","type":"select","options":["避難口誘導灯","通路誘導灯","客席誘導灯","非常照明"]},{"key":"outer","label":"外形・変形","type":"select","options":["正常","変形","損傷"]},{"key":"light","label":"点灯確認","type":"select","options":["正常点灯","不点灯","チラツキ"]},{"key":"battery","label":"バッテリー","type":"select","options":["正常","要交換","劣化"]},{"key":"note","label":"備考","type":"text","placeholder":"特記事項"}]}'
    },
    {
        "id": "hydrant",
        "name": "屋内消火栓",
        "sort_order": 3,
        "check_schema": '{"fields":[{"key":"location","label":"設置場所","type":"text","placeholder":"例）1F廊下"},{"key":"device_type","label":"種別","type":"select","options":["1号消火栓","2号消火栓","易操作性1号"]},{"key":"outer","label":"外形・変形","type":"select","options":["正常","変形","腐食","損傷"]},{"key":"hose","label":"ホース","type":"select","options":["正常","劣化","損傷","折れ癖"]},{"key":"nozzle","label":"ノズル","type":"select","options":["正常","変形","詰まり"]},{"key":"valve","label":"バルブ","type":"select","options":["正常","開閉不良","漏水"]},{"key":"water_test","label":"放水試験","type":"select","options":["正常","圧力不足","未実施"]},{"key":"note","label":"備考","type":"text","placeholder":"特記事項"}]}'
    },
]


def seed_equipment_types(db):
    for et in EQUIPMENT_TYPES:
        existing = db.execute("SELECT id FROM equipment_types WHERE id=?", (et["id"],)).fetchone()
        if not existing:
            db.execute(
                "INSERT INTO equipment_types (id, name, check_schema, sort_order) VALUES (?,?,?,?)",
                (et["id"], et["name"], et["check_schema"], et["sort_order"])
            )


# ─── ステータス計算 ──────────────────────────────────
def calc_status(next_inspection_str):
    if not next_inspection_str:
        return "unset", "未設定", "#95a5a6"
    try:
        nd = date.fromisoformat(next_inspection_str)
    except ValueError:
        return "unset", "未設定", "#95a5a6"
    today = date.today()
    diff = (nd - today).days
    if diff < 0:
        return "overdue", f"期限超過 {abs(diff)}日", "#c0392b"
    elif diff <= 30:
        return "warning", f"残り{diff}日", "#e67e22"
    else:
        return "ok", f"残り{diff}日", "#27ae60"

# ─── ルート ──────────────────────────────────────────
@app.route("/proposal")
def proposal():
    return render_template("proposal.html")

@app.route("/")
def dashboard():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM properties ORDER BY next_inspection ASC NULLS LAST"
    ).fetchall()
    props = []
    for r in rows:
        status, label, color = calc_status(r["next_inspection"])
        insp_count = db.execute(
            "SELECT COUNT(*) FROM inspections WHERE property_id=?", (r["id"],)
        ).fetchone()[0]
        props.append({**dict(r), "status": status, "status_label": label,
                      "status_color": color, "insp_count": insp_count})
    overdue  = sum(1 for p in props if p["status"] == "overdue")
    warning  = sum(1 for p in props if p["status"] == "warning")
    ok_count = sum(1 for p in props if p["status"] == "ok")
    return render_template("dashboard.html", props=props,
                           overdue=overdue, warning=warning, ok_count=ok_count)

@app.route("/property/new", methods=["GET", "POST"])
def property_new():
    if request.method == "POST":
        f = request.form
        next_d = f.get("next_inspection") or None
        db = get_db()
        db.execute(
            "INSERT INTO properties (name,address,owner_name,owner_contact,next_inspection) VALUES (?,?,?,?,?)",
            (f["name"], f.get("address",""), f.get("owner_name",""),
             f.get("owner_contact",""), next_d)
        )
        db.commit()
        return redirect(url_for("dashboard"))
    return render_template("property_form.html")

@app.route("/property/<int:pid>/delete", methods=["POST"])
def property_delete(pid):
    db = get_db()
    db.execute("DELETE FROM inspection_items WHERE inspection_id IN (SELECT id FROM inspections WHERE property_id=?)", (pid,))
    db.execute("DELETE FROM inspections WHERE property_id=?", (pid,))
    db.execute("DELETE FROM properties WHERE id=?", (pid,))
    db.commit()
    return redirect(url_for("dashboard"))

@app.route("/inspect/<int:pid>", methods=["GET", "POST"])
def inspect(pid):
    db = get_db()
    prop = db.execute("SELECT * FROM properties WHERE id=?", (pid,)).fetchone()
    if not prop:
        abort(404)
    if request.method == "POST":
        f = request.form
        try:
            count = max(0, int(f.get("count", 1)))
        except (ValueError, TypeError):
            count = 1
        token = str(uuid.uuid4())
        inspected_at = f.get("inspected_at") or str(date.today())
        cur = db.execute(
            "INSERT INTO inspections (property_id,inspector_name,inspector_num,inspected_at,period_from,period_to,share_token) VALUES (?,?,?,?,?,?,?)",
            (pid, f.get("inspector_name",""), f.get("inspector_num",""),
             inspected_at, f.get("period_from",""), f.get("period_to",""), token)
        )
        insp_id = cur.lastrowid
        equip_type = f.get("equipment_type", "extinguisher")
        schema_row = db.execute(
            "SELECT check_schema FROM equipment_types WHERE id=?", (equip_type,)
        ).fetchone()
        schema_fields = []
        if schema_row:
            schema_fields = json.loads(schema_row["check_schema"]).get("fields", [])
        fixed_keys = {"location","type","capacity","year","outer","safety_pin","body","cap","hose","pressure","judgment","note"}
        for i in range(1, count + 1):
            extra = {
                field["key"]: f.get(f"{field['key']}_{i}", "")
                for field in schema_fields
                if field["key"] not in fixed_keys
            }
            db.execute(
                "INSERT INTO inspection_items (inspection_id,no,location,type,capacity,year,outer,safety_pin,body,cap,hose,pressure,judgment,note,equipment_type,extra_data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (insp_id, i,
                 f.get(f"location_{i}",""), f.get(f"type_{i}",""),
                 f.get(f"capacity_{i}",""), f.get(f"year_{i}",""),
                 f.get(f"outer_{i}",""), f.get(f"safety_pin_{i}",""),
                 f.get(f"body_{i}",""), f.get(f"cap_{i}",""),
                 f.get(f"hose_{i}",""), f.get(f"pressure_{i}",""),
                 f.get(f"judgment_{i}","適"), f.get(f"note_{i}",""),
                 equip_type, json.dumps(extra, ensure_ascii=False))
            )
        # 次回点検日を6ヶ月後に自動更新
        try:
            next_d = date.fromisoformat(inspected_at) + timedelta(days=183)
        except ValueError:
            next_d = date.today() + timedelta(days=183)
        db.execute(
            "UPDATE properties SET last_inspected=?, next_inspection=? WHERE id=?",
            (inspected_at, str(next_d), pid)
        )
        db.commit()
        return redirect(url_for("report_preview", token=token))
    equip_types = [dict(r) for r in db.execute(
        "SELECT id, name FROM equipment_types ORDER BY sort_order"
    ).fetchall()]
    selected_type = request.args.get("type", "extinguisher")
    schema_row = db.execute(
        "SELECT check_schema FROM equipment_types WHERE id=?", (selected_type,)
    ).fetchone()
    _raw = schema_row["check_schema"] if schema_row else '{"fields":[]}'
    check_schema = json.loads(_raw)
    return render_template("inspect.html", prop=prop,
                           extinguisher_types=EXTINGUISHER_TYPES,
                           check_options=CHECK_OPTIONS,
                           equip_types=equip_types,
                           selected_type=selected_type,
                           check_schema=check_schema)

@app.route("/report/<token>")
def report_preview(token):
    db = get_db()
    insp = db.execute(
        "SELECT i.*, p.name as prop_name, p.address, p.owner_name "
        "FROM inspections i JOIN properties p ON i.property_id=p.id "
        "WHERE i.share_token=?", (token,)
    ).fetchone()
    if not insp:
        abort(404)
    items_raw = db.execute(
        "SELECT * FROM inspection_items WHERE inspection_id=? ORDER BY no",
        (insp["id"],)
    ).fetchall()
    items = []
    for r in items_raw:
        item = dict(r)
        item["is_ok"] = r["judgment"] == "適"
        try:
            item["extra"] = json.loads(r["extra_data"] or "{}")
        except Exception:
            item["extra"] = {}
        items.append(item)
    equip_type = items[0]["equipment_type"] if items else "extinguisher"
    schema_row = db.execute(
        "SELECT name, check_schema FROM equipment_types WHERE id=?", (equip_type,)
    ).fetchone()
    check_schema = json.loads(schema_row["check_schema"]) if schema_row else {"fields": []}
    equip_name = schema_row["name"] if schema_row else "消火器"
    share_url = request.host_url.rstrip("/") + url_for("report_share", token=token)
    return render_template("report_preview.html", insp=dict(insp),
                           items=items, share_url=share_url,
                           check_schema=check_schema, equip_name=equip_name,
                           equip_type=equip_type)

@app.route("/share/<token>")
def report_share(token):
    db = get_db()
    insp = db.execute(
        "SELECT i.*, p.name as prop_name, p.address, p.owner_name "
        "FROM inspections i JOIN properties p ON i.property_id=p.id "
        "WHERE i.share_token=?", (token,)
    ).fetchone()
    if not insp:
        abort(404)
    items_raw = db.execute(
        "SELECT * FROM inspection_items WHERE inspection_id=? ORDER BY no",
        (insp["id"],)
    ).fetchall()
    items = []
    for r in items_raw:
        item = dict(r)
        item["is_ok"] = r["judgment"] == "適"
        try:
            item["extra"] = json.loads(r["extra_data"] or "{}")
        except Exception:
            item["extra"] = {}
        items.append(item)
    equip_type = items[0]["equipment_type"] if items else "extinguisher"
    schema_row = db.execute(
        "SELECT name, check_schema FROM equipment_types WHERE id=?", (equip_type,)
    ).fetchone()
    check_schema = json.loads(schema_row["check_schema"]) if schema_row else {"fields": []}
    equip_name = schema_row["name"] if schema_row else "消火器"
    return render_template("report_share.html", insp=dict(insp), items=items,
                           check_schema=check_schema, equip_name=equip_name,
                           equip_type=equip_type)

@app.route("/property/<int:pid>/history")
def property_history(pid):
    db = get_db()
    prop = db.execute("SELECT * FROM properties WHERE id=?", (pid,)).fetchone()
    if not prop:
        abort(404)
    inspections = db.execute(
        "SELECT i.*, COUNT(ii.id) as item_count "
        "FROM inspections i "
        "LEFT JOIN inspection_items ii ON ii.inspection_id=i.id "
        "WHERE i.property_id=? "
        "GROUP BY i.id ORDER BY i.inspected_at DESC",
        (pid,)
    ).fetchall()
    return render_template("history.html", prop=dict(prop), inspections=[dict(i) for i in inspections])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

with app.app_context():
    init_db()
