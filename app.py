import csv
import hashlib
import json
import os
import random
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path

import psycopg
import click
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import (
    create_user,
    create_password_reset_token,
    consume_password_reset_token,
    database_status,
    find_user_by_identity,
    find_user_by_email,
    find_user_for_login,
    get_public_user,
    list_users,
    password_reset_token_is_valid,
)
from mailer import mail_configured, send_password_reset
from predictive import append_snapshot, predictive_payload


BASE = Path(__file__).parent
DATA = BASE / "data"
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-development-change-me")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return error("Debes iniciar sesión.", 401)
            return redirect(url_for("auth_page"))
        return view(*args, **kwargs)

    return wrapped


def read_json(filename):
    with (DATA / filename).open(encoding="utf-8") as file:
        return json.load(file)


def load_questions():
    with (DATA / "questions.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    required = {"area", "question", "answer", "action", "value", "source"}
    if any(set(row) != required or None in row for row in rows):
        raise ValueError("questions.csv contiene columnas inválidas")
    return rows


def simulated_snapshot():
    data = read_json("production_floor.json")
    data["shift"]["actual_units"] += random.randint(0, 8)
    data["shift"]["current_rate"] = round(
        max(0, data["shift"]["current_rate"] + random.uniform(-1.2, 1.2)), 1
    )
    data["oee"]["performance"] = round(
        max(0, min(100, data["oee"]["performance"] + random.uniform(-0.4, 0.4))), 1
    )
    data["oee"]["oee"] = round(
        data["oee"]["availability"]
        * data["oee"]["performance"]
        * data["oee"]["quality"]
        / 10000,
        1,
    )
    data["shift"]["completion_pct"] = round(
        data["shift"]["actual_units"] / data["shift"]["plan_units"] * 100, 1
    )
    data["generated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    return data


def error(message, status=400):
    return jsonify({"error": message}), status


@app.get("/")
@login_required
def index():
    return render_template("index.html")


@app.get("/login")
def auth_page():
    if "user_id" in session:
        return redirect(url_for("index"))
    return render_template("login.html")


@app.post("/api/auth/login")
def auth_login():
    body = request.get_json(silent=True) or {}
    identity = body.get("identity", "").strip() if isinstance(body.get("identity"), str) else ""
    password = body.get("password", "") if isinstance(body.get("password"), str) else ""
    if not identity or not password:
        return error("Usuario/correo y contraseña son obligatorios.")
    try:
        user = find_user_for_login(identity)
    except RuntimeError:
        app.logger.error("Login rejected: database is not configured")
        return error("La base de datos no está configurada. Revisa DB_PASSWORD en .env.", 503)
    except psycopg.Error:
        app.logger.exception("Login rejected: database connection error")
        return error("No fue posible conectar con la base de datos.", 503)
    if not user or not check_password_hash(user["password_hash"], password):
        app.logger.warning("Login rejected: invalid credentials")
        return error("Credenciales incorrectas.", 401)
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]
    session.permanent = bool(body.get("remember"))
    app.logger.info("Login successful: user_id=%s", user["id"])
    return jsonify({"id": user["id"], "name": user["name"], "username": user["username"]})


@app.post("/api/auth/logout")
def auth_logout():
    user_id = session.get("user_id")
    session.clear()
    if user_id:
        app.logger.info("Logout successful: user_id=%s", user_id)
    return jsonify({"status": "ok"})


def token_digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@app.get("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")


@app.post("/api/auth/forgot-password")
def forgot_password_request():
    body = request.get_json(silent=True) or {}
    email = body.get("email", "").strip() if isinstance(body.get("email"), str) else ""
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        return error("Ingresa un correo válido.")
    generic = {"message": "Si el correo está registrado, recibirás un enlace de recuperación."}
    try:
        user = find_user_by_email(email)
        if user:
            token = secrets.token_urlsafe(32)
            create_password_reset_token(
                user["id"], token_digest(token), datetime.now(timezone.utc) + timedelta(minutes=30)
            )
            base_url = os.environ.get("APP_BASE_URL", request.host_url.rstrip("/")).rstrip("/")
            send_password_reset(user["email"], f"{base_url}/reset-password/{token}")
    except Exception:
        app.logger.exception("No fue posible procesar la recuperación de contraseña")
    return jsonify(generic)


@app.get("/reset-password/<token>")
def reset_password_page(token):
    try:
        valid = password_reset_token_is_valid(token_digest(token))
    except (psycopg.Error, RuntimeError):
        valid = False
    return render_template("reset_password.html", token=token, valid=valid)


@app.post("/api/auth/reset-password")
def reset_password_submit():
    body = request.get_json(silent=True) or {}
    token = body.get("token", "") if isinstance(body.get("token"), str) else ""
    password = body.get("password", "") if isinstance(body.get("password"), str) else ""
    if len(password) < 10:
        return error("La contraseña debe tener al menos 10 caracteres.")
    try:
        changed = consume_password_reset_token(token_digest(token), generate_password_hash(password))
    except (psycopg.Error, RuntimeError):
        return error("No fue posible actualizar la contraseña.", 503)
    if not changed:
        return error("El enlace es inválido, expiró o ya fue utilizado.", 400)
    session.clear()
    return jsonify({"message": "Contraseña actualizada correctamente."})


@app.get("/api/auth/me")
@login_required
def auth_me():
    try:
        user = get_public_user(session["user_id"])
        if not user:
            session.clear()
            return error("La sesión ya no es válida.", 401)
        return jsonify(user)
    except (psycopg.Error, RuntimeError):
        return error("No fue posible consultar la sesión.", 503)


@app.get("/api/floor")
@login_required
def floor_snapshot():
    return jsonify(simulated_snapshot())


@app.get("/api/predictive")
@login_required
def predictive_index():
    return jsonify(predictive_payload())


@app.get("/api/predictive/<machine_id>")
@login_required
def predictive_machine(machine_id):
    machine = next((item for item in predictive_payload(refresh=False)["machines"] if item["id"] == machine_id.upper()), None)
    if not machine:
        return error("Máquina no encontrada.", 404)
    return jsonify(machine)


@app.get("/api/kpis")
@login_required
def kpis():
    """Compatibilidad con la versión anterior del prototipo."""
    return jsonify(read_json("kpis.json"))


@app.get("/api/questions")
@login_required
def questions():
    area = request.args.get("area", "Todos")
    rows = load_questions()
    if area != "Todos":
        rows = [row for row in rows if row["area"] == area]
    return jsonify(rows)


@app.post("/api/answer")
@login_required
def answer():
    body = request.get_json(silent=True) or {}
    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        return error("El campo 'question' es obligatorio.")

    normalized = question.strip().casefold()
    for row in load_questions():
        candidate = row["question"].strip().casefold()
        if normalized == candidate or (len(normalized) >= 8 and normalized in candidate):
            return jsonify(row)
    return jsonify({
        "area": "General",
        "question": question.strip(),
        "answer": "No hay una regla configurada para esta pregunta.",
        "action": "Selecciona una pregunta sugerida o escala el análisis al líder de turno.",
        "value": "Evita presentar una inferencia como un hecho medido.",
        "source": "Sin fuente disponible",
    })


@app.get("/api/shift-handover")
@login_required
def shift_handover():
    snapshot = read_json("production_floor.json")
    return jsonify({
        "shift": snapshot["context"]["shift"],
        "summary": [
            f"Producción: {snapshot['shift']['actual_units']:,} de {snapshot['shift']['plan_units']:,} unidades.",
            f"OEE: {snapshot['oee']['oee']}%. Principal pérdida: microparadas en empacadora.",
            "Lote FB-2405-L3 retenido preventivamente por control de peso.",
            "Quedan 3 acciones abiertas; 1 requiere atención inmediata.",
        ],
        "open_actions": snapshot["actions"],
        "next_shift_priority": "Verificar dosificador antes de liberar el lote y recuperar velocidad de empaque.",
    })


@app.get("/api/button-execute/<button_id>")
@login_required
def button_execute(button_id):
    allowed = {
        "parada": "Se abrió el flujo de atención de parada y escalamiento.",
        "calidad": "Se preparó el control de calidad del lote activo.",
        "mantenimiento": "Se notificó al técnico de mantenimiento de turno.",
        "replanificar": "Se generó una recomendación de recuperación del plan.",
    }
    if button_id not in allowed:
        return error("Acción no reconocida.", 404)
    return jsonify({
        "button": button_id,
        "status": "Simulado",
        "message": allowed[button_id],
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "requires_confirmation": True,
    })


@app.get("/api/users")
@login_required
def users_index():
    try:
        return jsonify(list_users())
    except RuntimeError:
        return error("La base de datos no está configurada. Revisa DB_PASSWORD en .env.", 503)
    except psycopg.Error:
        return error("No fue posible consultar la base de datos.", 503)


@app.post("/api/users")
def users_create():
    body = request.get_json(silent=True) or {}
    values = {
        key: body.get(key, "").strip() if isinstance(body.get(key), str) else ""
        for key in ("name", "email", "username", "password")
    }
    if not all(values.values()):
        return error("name, email, username y password son obligatorios.")
    if len(values["name"]) > 120 or len(values["email"]) > 255 or len(values["username"]) > 80:
        return error("Uno o más campos exceden la longitud permitida.")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", values["email"]):
        return error("El email no tiene un formato válido.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,80}", values["username"]):
        return error("El username debe tener entre 3 y 80 caracteres válidos.")
    if len(values["password"]) < 10:
        return error("La contraseña debe tener al menos 10 caracteres.")

    try:
        if find_user_by_identity(values["email"], values["username"]):
            return error("El email o username ya está registrado.", 409)
        user = create_user(
            values["name"],
            values["email"].lower(),
            values["username"],
            generate_password_hash(values["password"]),
        )
        return jsonify(user), 201
    except psycopg.errors.UniqueViolation:
        return error("El email o username ya está registrado.", 409)
    except RuntimeError:
        return error("La base de datos no está configurada. Revisa DB_PASSWORD en .env.", 503)
    except psycopg.Error:
        return error("No fue posible guardar el usuario.", 503)


@app.get("/health")
def health():
    return jsonify({"status": "ok", "database": database_status(), "mail": {"configured": mail_configured()}})


@app.cli.command("capture-machine-readings")
def capture_machine_readings():
    """Inserta una lectura simulada para cada máquina activa."""
    append_snapshot(minimum_interval_seconds=0)
    click.echo("Lecturas predictivas capturadas correctamente")


@app.cli.command("run-reading-collector")
@click.option("--interval-seconds", type=click.IntRange(min=10), default=lambda: int(os.environ.get("PREDICTIVE_CAPTURE_INTERVAL", "900")), show_default=True)
def run_reading_collector(interval_seconds):
    """Ejecuta el colector predictivo de manera continua."""
    click.echo(f"Colector predictivo iniciado; intervalo={interval_seconds}s", err=True)
    while True:
        try:
            append_snapshot(minimum_interval_seconds=0)
            click.echo(f"{datetime.now(timezone.utc).isoformat()} · lecturas capturadas", err=True)
        except Exception as exc:
            app.logger.exception("Predictive collector failed: %s", exc)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
