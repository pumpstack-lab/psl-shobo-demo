from flask import Flask, render_template, request
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "demo-secret-key-2026")

EXTINGUISHER_TYPES = [
    "粉末ABC型", "粉末BC型", "強化液型", "化学泡型",
    "機械泡型", "CO2型", "ハロン型", "水型"
]

CHECK_OPTIONS = {
    "outer":      ["正常", "変形", "腐食", "損傷"],
    "safety_pin": ["正常", "脱落", "変形", "破れ"],
    "seal":       ["正常", "破れ", "欠"],
    "body":       ["正常", "変形", "腐食", "損傷"],
    "cap":        ["正常", "変形", "腐食"],
    "hose":       ["正常", "変形", "詰まり", "損傷"],
}

@app.route("/")
def index():
    return render_template("index.html",
        extinguisher_types=EXTINGUISHER_TYPES,
        check_options=CHECK_OPTIONS,
    )

@app.route("/preview", methods=["POST"])
def preview():
    form = request.form
    try:
        count = max(0, int(form.get("count", 1)))
    except (ValueError, TypeError):
        count = 1

    header = {
        "date_y":        form.get("date_y", ""),
        "date_m":        form.get("date_m", ""),
        "date_d":        form.get("date_d", ""),
        "building_name": form.get("building_name", ""),
        "address":       form.get("address", ""),
        "owner":         form.get("owner", ""),
        "inspector_name":form.get("inspector_name", ""),
        "inspector_num": form.get("inspector_num", ""),
        "period_from":   form.get("period_from", ""),
        "period_to":     form.get("period_to", ""),
    }

    items = []
    for i in range(1, count + 1):
        judgment = form.get(f"judgment_{i}", "適")
        items.append({
            "no":         i,
            "location":   form.get(f"location_{i}", ""),
            "type":       form.get(f"type_{i}", ""),
            "capacity":   form.get(f"capacity_{i}", ""),
            "year":       form.get(f"year_{i}", ""),
            "outer":      form.get(f"outer_{i}", "正常"),
            "safety_pin": form.get(f"safety_pin_{i}", "正常"),
            "body":       form.get(f"body_{i}", "正常"),
            "cap":        form.get(f"cap_{i}", "正常"),
            "hose":       form.get(f"hose_{i}", "正常"),
            "pressure":   form.get(f"pressure_{i}", ""),
            "judgment":   judgment,
            "note":       form.get(f"note_{i}", ""),
            "is_ok":      judgment == "適",
        })

    return render_template("report.html", header=header, items=items)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
