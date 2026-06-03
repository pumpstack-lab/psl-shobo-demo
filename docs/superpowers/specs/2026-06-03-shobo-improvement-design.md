# 消防点検ツール 改善設計書

**日付:** 2026-06-03  
**目的:** 営業デモ品質 + 実用品質の両立。消火器のみから主要設備3種追加へ拡張。

---

## スコープ

### 追加設備種別
1. **消火器**（既存・維持）
2. **自動火災報知設備**（感知器・受信機・発信機）
3. **誘導灯・非常照明**
4. **屋内消火栓**

### 改善項目
1. 設備種別をDBで管理する設計に変更（将来拡張対応）
2. 点検開始時に設備タイプを選択
3. 設備ごとに異なる点検項目フォームを動的生成
4. 物件ごとの点検履歴画面（現状なし）
5. PSLブランディング追加
6. Impeccable critique によるUI改善

---

## データベース設計

### 新規テーブル：`equipment_types`
```sql
CREATE TABLE equipment_types (
    id TEXT PRIMARY KEY,          -- 'extinguisher', 'fire_alarm', 'guidance_light', 'hydrant'
    name TEXT NOT NULL,           -- '消火器', '自動火災報知設備' 等
    check_schema TEXT NOT NULL,   -- JSON: チェック項目定義
    sort_order INTEGER DEFAULT 0
);
```

### 既存テーブル変更：`inspection_items`
```sql
ALTER TABLE inspection_items ADD COLUMN equipment_type TEXT DEFAULT 'extinguisher';
```

### check_schema の構造（JSON）
```json
{
  "fields": [
    {"key": "location", "label": "設置場所", "type": "text", "placeholder": "1F廊下"},
    {"key": "outer", "label": "外形", "type": "select", "options": ["正常","変形","腐食","損傷"]},
    {"key": "judgment", "label": "判定", "type": "judgment"}
  ]
}
```

---

## 設備別チェック項目定義

### 消火器（既存維持）
- 設置場所・種別・能力単位・製造年
- 外形・安全栓・本体容器・キャップ・ホース
- 指示圧力値・判定・備考

### 自動火災報知設備
- 設置場所・機器種別（感知器/受信機/発信機/中継器）
- 外形・変形腐食・脱落・未警戒・汚損・障害物
- 作動試験結果・判定・備考

### 誘導灯・非常照明
- 設置場所・種別（誘導灯/非常照明）
- 外形・点灯確認・照度・電池
- 判定・備考

### 屋内消火栓
- 設置場所・種別（1号/2号/易操作）
- 外形・ホース・ノズル・バルブ・水源水量
- 放水試験・判定・備考

---

## 画面構成

### 既存（維持・改善）
- `/` ダッシュボード — 統計カード + 物件一覧
- `/property/new` 物件登録
- `/inspect/<pid>` 点検入力（設備タイプ選択を追加）
- `/report/<token>` 点検票プレビュー（印刷・共有）
- `/share/<token>` オーナー共有画面

### 新規追加
- `/property/<pid>/history` 点検履歴一覧

---

## 実装方針

### app.py
- `equipment_types` テーブルのseedデータをinit_db()に追加
- `inspection_items` に `equipment_type` カラムをマイグレーション追加
- `/inspect/<pid>` のGETに `?type=` パラメータ追加（デフォルト: extinguisher）
- `/property/<pid>/history` ルート新規追加

### テンプレート
- `inspect.html`: 設備タイプ選択タブを先頭に追加、JSで動的フォーム生成
- `report_preview.html`: 設備タイプに応じたテーブルヘッダー切り替え
- `history.html`: 新規作成
- 全テンプレート: PSLフッター追加

---

## PSLブランディング
- 全画面フッターに「Powered by PumpStack Lab.」
- ダッシュボードのtopbarロゴ横にPSLサブテキスト
- カラーテーマは現行（#c0392b）を維持

---

## ネイト精査結果
- スコープは適切。消化器のみより営業力が大幅向上
- check_schemaをJSONで管理することで将来設備追加がコード変更不要
- 履歴画面は実用に必須（現状だと点検した記録を後から見られない）
- デモとして見せる際は自動火災報知設備が最も訴求力が高い（義務設置範囲が広い）
