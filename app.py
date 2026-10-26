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
from werkzeug.utils import secure_filename

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
from machine_manuals import ingest_machine_manuals
from rag_service import ALLOWED_DOCUMENT_EXTENSIONS, answer_chat, delete_document, ingest_document, list_documents
from quality import quality_dashboard
from oee import oee_dashboard
from downtime import append_random_downtime, downtime_dashboard, seed_random_downtimes


BASE = Path(__file__).parent
DATA = BASE / "data"
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "local-development-change-me")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
    PERMANENT_SESSION_LIFETIME=timedelta(seconds=int(os.environ.get("SESSION_IDLE_TIMEOUT_SECONDS", "1800"))),
    MAX_CONTENT_LENGTH=100 * 1024 * 1024,
)


@app.before_request
def enforce_idle_session_timeout():
    if "user_id" not in session:
        return None
    now = datetime.now(timezone.utc)
    last_activity = session.get("last_activity")
    if last_activity:
        try:
            elapsed = (now - datetime.fromisoformat(last_activity)).total_seconds()
        except (TypeError, ValueError):
            elapsed = 0
        if elapsed > int(os.environ.get("SESSION_IDLE_TIMEOUT_SECONDS", "1800")):
            session.clear()
            if request.path.startswith("/api/"):
                return error("La sesión expiró por inactividad.", 401)
            return redirect(url_for("auth_page"))
    session["last_activity"] = now.isoformat()
    return None


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
    integrated_oee = oee_dashboard(1, data)["summary"]
    data["oee"] = {key: integrated_oee[key] for key in ("oee", "availability", "performance", "quality")}
    data["downtime"]["minutes_today"] = integrated_oee["equivalent_line_downtime"]
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
    session["last_activity"] = datetime.now(timezone.utc).isoformat()
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


@app.get("/api/quality")
@login_required
def quality_summary():
    days = request.args.get("days", 7, type=int)
    return jsonify(quality_dashboard(days))


@app.get("/api/oee")
@login_required
def oee_summary():
    days = request.args.get("days", 7, type=int)
    return jsonify(oee_dashboard(days))


@app.get("/api/downtime")
@login_required
def downtime_summary():
    try:
        return jsonify(downtime_dashboard(
            request.args.get("days", 30, type=int), request.args.get("date_from"),
            request.args.get("date_to"), request.args.get("machine"),
            request.args.get("category"), request.args.get("status"),
        ))
    except ValueError:
        return error("El rango de fechas no es válido.")


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


@app.post("/api/copilot/chat")
@login_required
def copilot_chat():
    body = request.get_json(silent=True) or {}
    question = body.get("question", "").strip() if isinstance(body.get("question"), str) else ""
    mode = body.get("mode", "auto")
    if len(question) < 5 or len(question) > 2000:
        return error("La pregunta debe tener entre 5 y 2000 caracteres.")
    if mode not in {"auto", "manuals", "troubleshooting", "predictive"}:
        return error("Modo de consulta inválido.")
    try:
        response, sources, resolved_mode = answer_chat(question, mode)
        return jsonify({"answer": response, "sources": sources, "mode": resolved_mode})
    except ValueError as exc:
        return error(str(exc))
    except RuntimeError as exc:
        app.logger.exception("Ollama no disponible")
        return error(str(exc), 503)
    except (psycopg.Error, RuntimeError):
        app.logger.exception("Error de base de datos en el copiloto")
        return error("No fue posible consultar la base documental.", 503)
    except Exception:
        app.logger.exception("Error procesando el chat del copiloto")
        return error("No fue posible procesar la consulta.", 500)


@app.get("/api/documents")
@login_required
def documents_index():
    try:
        return jsonify(list_documents())
    except (psycopg.Error, RuntimeError):
        return error("No fue posible consultar los documentos indexados.", 503)


@app.post("/api/documents")
@login_required
def documents_upload():
    files = [item for item in request.files.getlist("files") if item and item.filename]
    if not files:
        return error("Selecciona al menos un documento.")
    if len(files) > 20:
        return error("Puedes cargar hasta 20 documentos por operación.")
    results = []
    try:
        for uploaded in files:
            filename = secure_filename(uploaded.filename)
            extension = Path(filename).suffix.lower()
            if not filename or extension not in ALLOWED_DOCUMENT_EXTENSIONS:
                raise ValueError(f"Archivo no compatible: {uploaded.filename}")
            raw = uploaded.read()
            if not raw:
                raise ValueError(f"El archivo {filename} está vacío.")
            if len(raw) > 25 * 1024 * 1024:
                raise ValueError(f"El archivo {filename} supera el límite de 25 MB.")
            results.append({"document_name": filename, "chunks": ingest_document(filename, raw)})
        return jsonify({"documents": results, "total": len(results)}), 201
    except ValueError as exc:
        return error(str(exc))
    except RuntimeError as exc:
        app.logger.exception("Ollama no disponible durante la indexación")
        return error(str(exc), 503)
    except Exception:
        app.logger.exception("No fue posible indexar documentos")
        return error("No fue posible procesar los documentos.", 500)


@app.delete("/api/documents/<path:document_name>")
@login_required
def documents_delete(document_name):
    try:
        deleted = delete_document(secure_filename(document_name))
        if not deleted:
            return error("Documento no encontrado.", 404)
        return jsonify({"deleted_chunks": deleted})
    except (psycopg.Error, RuntimeError):
        return error("No fue posible eliminar el documento.", 503)


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


@app.cli.command("ingest-machine-manuals")
def ingest_machine_manuals_command():
    """Genera e indexa en pgvector un manual para cada máquina activa."""
    machines, chunks = ingest_machine_manuals()
    click.echo(f"Manuales indexados: {machines} máquinas, {chunks} fragmentos")


@app.cli.command("seed-random-downtimes")
@click.option("--count", type=click.IntRange(min=1, max=1000), default=90, show_default=True)
@click.option("--days", type=click.IntRange(min=1, max=90), default=30, show_default=True)
def seed_random_downtimes_command(count, days):
    """Genera un histórico aleatorio de paradas en PostgreSQL."""
    inserted = seed_random_downtimes(count, days)
    click.echo(f"Paradas aleatorias insertadas: {inserted}")


@app.cli.command("run-downtime-collector")
@click.option("--interval-seconds", type=click.IntRange(min=10), default=lambda: int(os.environ.get("DOWNTIME_CAPTURE_INTERVAL", "900")), show_default=True)
@click.option("--probability", type=click.FloatRange(min=0, max=1), default=lambda: float(os.environ.get("DOWNTIME_EVENT_PROBABILITY", "0.35")), show_default=True)
def run_downtime_collector(interval_seconds, probability):
    """Genera paradas aleatorias periódicamente."""
    click.echo(f"Colector de paradas iniciado; intervalo={interval_seconds}s; probabilidad={probability}", err=True)
    while True:
        try:
            inserted = append_random_downtime(probability)
            click.echo(f"{datetime.now(timezone.utc).isoformat()} · paradas insertadas={inserted}", err=True)
        except Exception as exc:
            app.logger.exception("Downtime collector failed: %s", exc)
        time.sleep(interval_seconds)


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
