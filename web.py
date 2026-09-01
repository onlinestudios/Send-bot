
import os, json, random, string, secrets
from pathlib import Path
from urllib.parse import urlencode

import requests
from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash

BASE = Path(__file__).parent
DATA = BASE / "data"
APPS_FILE = DATA / "apps.json"
UPLOADS = BASE / "static" / "uploads"
DATA.mkdir(exist_ok=True)
UPLOADS.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", secrets.token_hex(32))

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID") or "1544335328599343236"
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")

def load_apps():
    if not APPS_FILE.exists():
        APPS_FILE.write_text("{}", encoding="utf-8")
    try:
        return json.loads(APPS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_apps(data):
    APPS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def make_code(name):
    used = load_apps()
    clean = "".join(ch for ch in name if ch.isalnum() or ch in "_-").strip() or "App"
    while True:
        code = f"{clean}#{random.randint(0, 9999):04d}"
        if code not in used:
            return code

def discord_authorize_url():
    params = {
        "client_id": DISCORD_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "identify",
    }
    return "https://discord.com/oauth2/authorize?" + urlencode(params)

def current_user():
    return session.get("discord_user")

@app.context_processor
def inject_globals():
    return {"discord_user": current_user()}

@app.route("/")
def index():
    return render_template("index.html", invite_url=(
        f"https://discord.com/oauth2/authorize?client_id={DISCORD_CLIENT_ID}"
        f"&permissions=19456&scope=bot%20applications.commands"
        if DISCORD_CLIENT_ID else "#"
    ))

@app.route("/login")
def login():
    if not DISCORD_CLIENT_ID or not DISCORD_CLIENT_SECRET:
        flash("Discord login is not configured yet. Add the OAuth environment variables on your host.")
        return redirect(url_for("index"))
    return redirect(discord_authorize_url())

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect(url_for("index"))
    token_resp = requests.post(
        "https://discord.com/api/oauth2/token",
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    token_resp.raise_for_status()
    token = token_resp.json()["access_token"]
    user_resp = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    user_resp.raise_for_status()
    session["discord_user"] = user_resp.json()
    return redirect(url_for("dashboard"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if not current_user():
        return redirect(url_for("login"))
    all_apps = load_apps()
    uid = str(current_user()["id"])
    mine = [(code, info) for code, info in all_apps.items() if str(info.get("owner_discord_id")) == uid]
    return render_template("dashboard.html", apps=mine, max_apps=10)

@app.route("/dashboard/create", methods=["POST"])
def create_app():
    if not current_user():
        return redirect(url_for("login"))
    all_apps = load_apps()
    uid = str(current_user()["id"])
    mine = [x for x in all_apps.values() if str(x.get("owner_discord_id")) == uid]
    if len(mine) >= 10:
        flash("You have reached the 10 app limit.")
        return redirect(url_for("dashboard"))

    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    image = request.files.get("image")

    if not name or not description:
        flash("Complete first: name and description are required.")
        return redirect(url_for("dashboard"))

    code = make_code(name)
    filename = ""
    if image and image.filename:
        ext = Path(image.filename).suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
            flash("Profile picture must be PNG, JPG, JPEG, or WEBP.")
            return redirect(url_for("dashboard"))
        filename = f"{secrets.token_hex(12)}{ext}"
        image.save(UPLOADS / filename)

    all_apps[code] = {
        "name": name[:32],
        "description": description[:500],
        "image": filename,
        "owner_discord_id": uid,
    }
    save_apps(all_apps)
    flash(f"Saved! Your app code is {code}.")
    return redirect(url_for("dashboard"))

@app.route("/dashboard/delete/<path:code>", methods=["POST"])
def delete_app(code):
    if not current_user():
        return redirect(url_for("login"))
    all_apps = load_apps()
    item = all_apps.get(code)
    if item and str(item.get("owner_discord_id")) == str(current_user()["id"]):
        all_apps.pop(code)
        save_apps(all_apps)
    return redirect(url_for("dashboard"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
