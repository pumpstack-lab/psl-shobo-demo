# 消防点検ツール改善 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 消火器のみの点検ツールを、自動火災報知設備・誘導灯・屋内消火栓の3設備を追加した実用品質のデモツールに拡張する。

**Architecture:** 設備種別を`equipment_types`テーブルでDB管理し、チェック項目をJSON schemaで定義。点検入力フォームはJSで動的生成。既存の消火器ロジックは維持しつつ設備タイプを抽象化する。

**Tech Stack:** Python/Flask, SQLite, Jinja2, vanilla JS

---

## File Structure

**Modify:**
- `app/app.py` — DB初期化・マイグレーション・ルート追加
- `app/templates/dashboard.html` — PSLフッター追加
- `app/templates/inspect.html` — 設備タイプ選択＋動的フォーム
- `app/templates/report_preview.html` — 設備別テーブル切り替え・PSLフッター
- `app/templates/report_share.html` — 設備別テーブル・PSLフッター
- `app/templates/property_form.html` — PSLフッター追加

**Create:**
- `app/templates/history.html` — 物件ごとの点検履歴一覧

---

### Task 1: DBマイグレーション — equipment_typesテーブル追加

**Files:**
- Modify: `app/app.py`

- [ ] **Step 1: `init_db()`に`equipment_types`テーブル作成SQLを追加**

`app/app.py`の`init_db()`内の`db.executescript()`に以下を追記：

```python
    CREATE TABLE IF NOT EXISTS equipment_types (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        check_schema TEXT NOT NULL,
        sort_order INTEGER DEFAULT 0
    );
```

- [ ] **Step 2: `inspection_items`に`equipment_type`カラムを追加するマイグレーション関数を追加**

`init_db()`の後ろに以下を追加：

```python
def migrate_equipment_type_col(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(inspection_items)").fetchall()]
    if "equipment_type" not in cols:
        db.execute("ALTER TABLE inspection_items ADD COLUMN equipment_type TEXT DEFAULT 'extinguisher'")
        db.commit()
```

- [ ] **Step 3: `equipment_types`のseedデータ関数を追加**

```python
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
    db.commit()
```

- [ ] **Step 4: `init_db()`の末尾でマイグレーションとseedを呼び出す**

`init_db()`内の`db.commit()`の直前に追加：

```python
    migrate_equipment_type_col(db)
    seed_equipment_types(db)
```

- [ ] **Step 5: 動作確認**

```bash
cd "/Users/Yutalow420/Library/Mobile Documents/iCloud~md~obsidian/Documents/事業計画トータルフォルダ/相談_脳内整理/部下_プロトタイプ/13_消防点検デモ/app"
python3 -c "from app import init_db; init_db(); import sqlite3; db=sqlite3.connect('shobo.db'); print([r[0] for r in db.execute('SELECT id FROM equipment_types').fetchall()])"
```

期待出力: `['extinguisher', 'fire_alarm', 'guidance_light', 'hydrant']`

- [ ] **Step 6: commit**

```bash
git add app/app.py
git commit -m "feat: equipment_typesテーブル追加・設備4種のseedデータ投入"
```

---

### Task 2: 点検履歴ルート追加

**Files:**
- Modify: `app/app.py`
- Create: `app/templates/history.html`

- [ ] **Step 1: `app.py`に`/property/<pid>/history`ルートを追加**

`report_share`関数の後に追加：

```python
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
```

- [ ] **Step 2: `history.html`を作成**

```html
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>点検履歴 | {{ prop.name }}</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Hiragino Sans', 'Meiryo', sans-serif; background: #f0f2f5; min-height: 100vh; }
.topbar {
  background: #c0392b; color: white; padding: 0 20px; height: 52px;
  display: flex; align-items: center; gap: 12px; position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
}
.topbar .logo { font-size: 18px; font-weight: 800; }
.topbar .spacer { flex: 1; }
.topbar a {
  background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.3);
  color: white; padding: 7px 14px; border-radius: 5px; text-decoration: none;
  font-size: 13px; font-weight: 600;
}
.topbar a:hover { background: rgba(255,255,255,0.28); }
.container { max-width: 900px; margin: 0 auto; padding: 24px 16px 60px; }
.prop-header {
  background: white; border-radius: 10px; padding: 16px 20px;
  margin-bottom: 20px; box-shadow: 0 1px 6px rgba(0,0,0,0.07);
}
.prop-header h2 { font-size: 18px; font-weight: 800; color: #2c3e50; margin-bottom: 4px; }
.prop-header p { font-size: 13px; color: #888; }
.history-list { display: flex; flex-direction: column; gap: 10px; }
.history-card {
  background: white; border-radius: 10px; padding: 16px 20px;
  box-shadow: 0 1px 6px rgba(0,0,0,0.07);
  display: flex; align-items: center; gap: 16px;
  border-left: 5px solid #c0392b;
}
.hist-info { flex: 1; }
.hist-date { font-size: 16px; font-weight: 700; color: #2c3e50; margin-bottom: 4px; }
.hist-meta { font-size: 12px; color: #888; display: flex; gap: 12px; flex-wrap: wrap; }
.hist-actions { display: flex; gap: 8px; flex-shrink: 0; }
.act-btn {
  padding: 7px 14px; border-radius: 5px; font-size: 12px; font-weight: 600;
  cursor: pointer; border: none; text-decoration: none; font-family: inherit;
  display: inline-flex; align-items: center; gap: 4px;
}
.act-btn.view { background: #c0392b; color: white; }
.act-btn.view:hover { background: #a93226; }
.empty-state { text-align: center; padding: 60px 20px; color: #aaa; }
.empty-state .icon { font-size: 48px; margin-bottom: 12px; }
.footer {
  text-align: center; padding: 24px 16px; font-size: 11px; color: #bbb;
  border-top: 1px solid #eee; margin-top: 40px;
}
</style>
</head>
<body>
<div class="topbar">
  <span class="logo">🔥 消防点検</span>
  <span class="spacer"></span>
  <a href="/">← ダッシュボード</a>
</div>
<div class="container">
  <div class="prop-header">
    <h2>{{ prop.name }}</h2>
    <p>{{ prop.address or '' }}　点検履歴 {{ inspections|length }}件</p>
  </div>
  {% if inspections %}
  <div class="history-list">
    {% for insp in inspections %}
    <div class="history-card">
      <div class="hist-info">
        <div class="hist-date">{{ insp.inspected_at or '日付未記録' }}</div>
        <div class="hist-meta">
          <span>点検者：{{ insp.inspector_name or '未記録' }}</span>
          <span>点検本数：{{ insp.item_count }}本</span>
          {% if insp.period_from %}<span>対象期間：{{ insp.period_from }}〜{{ insp.period_to }}</span>{% endif %}
        </div>
      </div>
      <div class="hist-actions">
        <a href="/report/{{ insp.share_token }}" class="act-btn view">📋 点検票を見る</a>
      </div>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <div class="empty-state">
    <div class="icon">📋</div>
    <p>まだ点検記録がありません。</p>
  </div>
  {% endif %}
</div>
<div class="footer">Powered by PumpStack Lab.</div>
</body>
</html>
```

- [ ] **Step 3: ダッシュボードの各物件カードに「履歴」ボタンを追加**

`dashboard.html`の`.prop-actions`内、削除ボタンの前に追加：

```html
<a href="/property/{{ p.id }}/history" class="act-btn history">📋 履歴</a>
```

- [ ] **Step 4: 動作確認**

```bash
python3 -c "
from app import app, init_db
init_db()
with app.test_client() as c:
    r = c.get('/property/1/history')
    print('status:', r.status_code)
    print('ok' if '点検履歴' in r.data.decode() else 'NG')
"
```

期待出力: `status: 200` / `ok`

- [ ] **Step 5: commit**

```bash
git add app/app.py app/templates/history.html app/templates/dashboard.html
git commit -m "feat: 物件ごとの点検履歴画面を追加"
```

---

### Task 3: 点検入力 — 設備タイプ選択UI追加

**Files:**
- Modify: `app/app.py`
- Modify: `app/templates/inspect.html`

- [ ] **Step 1: `app.py`の`inspect`ルートのGETに設備タイプ一覧を渡す**

`inspect`関数のrender_template呼び出しを以下に変更：

```python
    db2 = get_db()
    equip_types = [dict(r) for r in db2.execute(
        "SELECT id, name FROM equipment_types ORDER BY sort_order"
    ).fetchall()]
    selected_type = request.args.get("type", "extinguisher")
    return render_template("inspect.html", prop=prop,
                           extinguisher_types=EXTINGUISHER_TYPES,
                           check_options=CHECK_OPTIONS,
                           equip_types=equip_types,
                           selected_type=selected_type)
```

- [ ] **Step 2: `inspect.html`のtopbarの下に設備タイプ選択タブを追加**

`<div class="container">`の直前（`</div><!-- topbar -->`の後）に挿入：

```html
<div class="type-tabs">
  {% for et in equip_types %}
  <a href="/inspect/{{ prop.id }}?type={{ et.id }}"
     class="type-tab {% if selected_type == et.id %}active{% endif %}">
    {{ et.name }}
  </a>
  {% endfor %}
</div>
```

- [ ] **Step 3: `inspect.html`のstyleに設備タブのCSSを追加**

`</style>`の直前に追加：

```css
.type-tabs {
  background: #fff; border-bottom: 2px solid #e8e8e8;
  display: flex; overflow-x: auto; padding: 0 16px; gap: 0;
}
.type-tab {
  padding: 12px 20px; font-size: 13px; font-weight: 600; color: #888;
  text-decoration: none; white-space: nowrap; border-bottom: 3px solid transparent;
  margin-bottom: -2px;
}
.type-tab.active { color: #c0392b; border-bottom-color: #c0392b; }
.type-tab:hover { color: #c0392b; background: #fff0ef; }
```

- [ ] **Step 4: フォームにhidden inputで設備タイプを埋め込む**

`<form method="POST" id="mainForm">`の直後に追加：

```html
<input type="hidden" name="equipment_type" value="{{ selected_type }}">
```

- [ ] **Step 5: `app.py`のinspect POSTで`equipment_type`を保存**

`inspection_items`のINSERT文を以下に変更：

```python
            db.execute(
                "INSERT INTO inspection_items (inspection_id,no,location,type,capacity,year,outer,safety_pin,body,cap,hose,pressure,judgment,note,equipment_type) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (insp_id, i,
                 f.get(f"location_{i}",""), f.get(f"type_{i}",""),
                 f.get(f"capacity_{i}",""), f.get(f"year_{i}",""),
                 f.get(f"outer_{i}","正常"), f.get(f"safety_pin_{i}","正常"),
                 f.get(f"body_{i}","正常"), f.get(f"cap_{i}","正常"),
                 f.get(f"hose_{i}","正常"), f.get(f"pressure_{i}",""),
                 f.get(f"judgment_{i}","適"), f.get(f"note_{i}",""),
                 f.get("equipment_type","extinguisher"))
            )
```

- [ ] **Step 6: 動作確認**

```bash
python3 -c "
from app import app, init_db
init_db()
with app.test_client() as c:
    r = c.get('/inspect/1?type=fire_alarm')
    print('status:', r.status_code)
    print('タブあり' if '自動火災報知設備' in r.data.decode() else 'NG')
"
```

期待出力: `status: 200` / `タブあり`

- [ ] **Step 7: commit**

```bash
git add app/app.py app/templates/inspect.html
git commit -m "feat: 点検入力に設備タイプ選択タブを追加"
```

---

### Task 4: 動的フォーム — 設備ごとのチェック項目JS生成

**Files:**
- Modify: `app/templates/inspect.html`
- Modify: `app/app.py`

- [ ] **Step 1: `app.py`のinspect GETで選択設備のcheck_schemaをテンプレートに渡す**

Task 3で追加した`equip_types`取得の後に追加：

```python
    import json
    schema_row = db2.execute(
        "SELECT check_schema FROM equipment_types WHERE id=?", (selected_type,)
    ).fetchone()
    check_schema_json = schema_row["check_schema"] if schema_row else "{}"
```

render_templateに`check_schema_json=check_schema_json`を追加。

- [ ] **Step 2: `inspect.html`のJS冒頭でcheck_schemaを受け取る**

既存の`const TYPES = ...`の前に追加：

```javascript
const SCHEMA = {{ check_schema_json | tojson }};
const fields = SCHEMA.fields || [];
```

- [ ] **Step 3: `addCard()`関数をcheck_schema駆動に書き換える**

既存の`addCard()`全体を以下で置き換える：

```javascript
function addCard() {
  count++;
  const n = count;
  const div = document.createElement('div');
  div.className = 'ext-card';
  div.id = `card_${n}`;

  let fieldsHtml = '';
  fields.forEach(f => {
    const name = `${f.key}_${n}`;
    let input = '';
    if (f.type === 'select') {
      input = `<select name="${name}" class="check-sel${f.key==='judgment'?' judgment-sel ok':''}" id="${f.key==='judgment'?'jsel_'+n:''}" onchange="${f.key==='judgment'?'onJudge(this,'+n+')':''}">`;
      (f.options||[]).forEach(o => { input += `<option value="${o}">${o}</option>`; });
      input += '</select>';
    } else if (f.type === 'judgment') {
      input = `<select name="${name}" class="check-sel judgment-sel ok" id="jsel_${n}" onchange="onJudge(this,${n})">
        <option value="適">適</option><option value="否">否</option></select>`;
    } else {
      input = `<input type="text" name="${name}" class="check-input" placeholder="${f.placeholder||''}">`;
    }
    fieldsHtml += `<div class="check-group"><label>${f.label}</label>${input}</div>`;
  });

  div.innerHTML = `
    <div class="ext-card-hd">
      <span class="ext-num">No.${n}</span>
      <button type="button" class="ext-del" onclick="delCard(${n})">削除</button>
    </div>
    <div class="ext-body">
      <div class="ext-grid" style="flex-wrap:wrap;display:grid;grid-template-columns:1fr 1fr;gap:10px">
        ${fieldsHtml}
      </div>
    </div>`;
  document.getElementById('extList').appendChild(div);
  updateCount();
}
```

- [ ] **Step 4: `updateCount()`のname書き換えロジックを汎用化**

既存の`updateCount()`内の`el.name = el.name.replace(...)`は既に汎用的なので変更不要。`jsel_`のid更新部分だけ確認：

```javascript
// 既存コードのこの部分が正しく動くことを確認
c.querySelectorAll('[id^="jsel_"]').forEach(el => {
  el.id = `jsel_${i+1}`;
});
```

- [ ] **Step 5: 動作確認（消化器・火災報知設備の両方でフォームが出ることを確認）**

```bash
python3 -c "
from app import app, init_db
init_db()
with app.test_client() as c:
    r1 = c.get('/inspect/1?type=extinguisher')
    r2 = c.get('/inspect/1?type=fire_alarm')
    print('消火器schema:', 'check_schema_json' in r1.data.decode() or 'SCHEMA' in r1.data.decode())
    print('火災報知設備schema:', '作動試験' in r2.data.decode())
"
```

- [ ] **Step 6: commit**

```bash
git add app/app.py app/templates/inspect.html
git commit -m "feat: check_schema駆動の動的フォーム生成に変更"
```

---

### Task 5: PSLブランディング — 全画面にフッター追加

**Files:**
- Modify: `app/templates/dashboard.html`
- Modify: `app/templates/report_preview.html`
- Modify: `app/templates/report_share.html`
- Modify: `app/templates/property_form.html`

- [ ] **Step 1: 共通フッターCSSとHTMLを定義**

各テンプレートの`</style>`直前に追加するCSS：

```css
.psl-footer {
  text-align: center; padding: 24px 16px;
  font-size: 11px; color: #bbb; border-top: 1px solid #eee; margin-top: 40px;
}
.psl-footer a { color: #bbb; text-decoration: none; }
.psl-footer a:hover { color: #888; }
```

各テンプレートの`</body>`直前に追加するHTML：

```html
<div class="psl-footer">Powered by <a href="https://pumpstack-lab.github.io" target="_blank">PumpStack Lab.</a></div>
```

- [ ] **Step 2: `dashboard.html`に適用**

上記CSS・HTMLを`dashboard.html`に追加。

- [ ] **Step 3: `report_preview.html`に適用**（printでは非表示）

CSSの`.psl-footer`に`@media print { .psl-footer { display:none; } }`を追加してから適用。

- [ ] **Step 4: `report_share.html`・`property_form.html`に適用**

同様に追加。

- [ ] **Step 5: 動作確認**

```bash
python3 -c "
from app import app, init_db
init_db()
with app.test_client() as c:
    for path in ['/', '/property/new', '/report/dummy']:
        r = c.get(path)
        has = 'PumpStack Lab' in r.data.decode()
        print(f'{path}: {\"OK\" if has else \"missing\"} (status:{r.status_code})')
"
```

期待: `/`と`/property/new`はOK。`/report/dummy`は404なので確認不要。

- [ ] **Step 6: commit**

```bash
git add app/templates/
git commit -m "feat: 全画面にPSLフッターを追加"
```

---

### Task 6: Impeccable critique — UIデザイン改善

**Files:**
- Modify: `app/templates/dashboard.html`
- Modify: `app/templates/inspect.html`
- Modify: `app/templates/history.html`
- Modify: `app/templates/report_preview.html`

- [ ] **Step 1: Impeccable critique を実行**

`Skill("impeccable")`を呼び出し、`critique`コマンドで全テンプレートを対象に実行する。

- [ ] **Step 2: 指摘事項を自動修正**

critiqiueの結果に基づき改善を適用。

- [ ] **Step 3: commit**

```bash
git add app/templates/
git commit -m "style: Impeccable critique によるUI改善"
```

---

### Task 7: 最終確認・push

- [ ] **Step 1: アプリを起動して全画面を目視確認**

```bash
cd "/Users/Yutalow420/Library/Mobile Documents/iCloud~md~obsidian/Documents/事業計画トータルフォルダ/相談_脳内整理/部下_プロトタイプ/13_消防点検デモ/app"
python3 app.py
```

確認項目：
- ダッシュボード: 物件一覧・履歴ボタン表示
- 点検入力: 設備タイプタブ4つ・選択後フォームが変わる
- 履歴画面: 過去点検一覧
- 点検票: PSLフッター・印刷で非表示

- [ ] **Step 2: ネイト精査チェック**

- [ ] 新機能がPSL営業デモとして使えるか（設備追加で訴求力が上がっているか）
- [ ] PSLブランドが全画面に一貫して表示されているか
- [ ] デモ用サンプルデータが現実的か（東京の物件名が入っているのはデモとして適切）

- [ ] **Step 3: git push**

```bash
git push origin main
```
