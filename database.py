import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row


BASE = Path(__file__).parent
load_dotenv(BASE / ".env")


def database_url():
    explicit_url = os.environ.get("DATABASE_URL", "").strip()
    if explicit_url:
        return explicit_url
    password = os.environ.get("DB_PASSWORD", "").strip()
    if not password or password == "CHANGE_ME":
        return ""
    return make_conninfo(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ.get("DB_NAME", "Food_Beverage"),
        user=os.environ.get("DB_USER", "postgres"),
        password=password,
        sslmode=os.environ.get("DB_SSLMODE", "prefer"),
    )


def get_connection():
    url = database_url()
    if not url:
        raise RuntimeError("DATABASE_URL no está configurada")
    return psycopg.connect(url, row_factory=dict_row)


def database_status():
    if not database_url():
        return {"status": "not_configured"}
    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_database() AS database, current_user AS username")
                result = cursor.fetchone()
        return {"status": "ok", **result}
    except psycopg.Error:
        return {"status": "unavailable"}


def list_users():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, email, username, created_at
                FROM public.users
                ORDER BY created_at DESC, id DESC
                """
            )
            return cursor.fetchall()


def find_user_by_identity(email, username):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM public.users
                WHERE lower(email) = lower(%s) OR lower(username) = lower(%s)
                LIMIT 1
                """,
                (email, username),
            )
            return cursor.fetchone()


def find_user_for_login(identity):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, email, username, password_hash, created_at
                FROM public.users
                WHERE lower(email) = lower(%s) OR lower(username) = lower(%s)
                LIMIT 1
                """,
                (identity, identity),
            )
            return cursor.fetchone()


def get_public_user(user_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, email, username, created_at
                FROM public.users WHERE id = %s
                """,
                (user_id,),
            )
            return cursor.fetchone()


def find_user_by_email(email):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, email FROM public.users WHERE lower(email) = lower(%s) LIMIT 1",
                (email,),
            )
            return cursor.fetchone()


def create_password_reset_token(user_id, token_hash, expires_at):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE public.password_reset_tokens
                SET used_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND used_at IS NULL
                """,
                (user_id,),
            )
            cursor.execute(
                """
                INSERT INTO public.password_reset_tokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, token_hash, expires_at),
            )


def password_reset_token_is_valid(token_hash):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id FROM public.password_reset_tokens
                WHERE token_hash = %s AND used_at IS NULL AND expires_at > CURRENT_TIMESTAMP
                LIMIT 1
                """,
                (token_hash,),
            )
            return cursor.fetchone() is not None


def consume_password_reset_token(token_hash, password_hash):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, user_id FROM public.password_reset_tokens
                WHERE token_hash = %s AND used_at IS NULL AND expires_at > CURRENT_TIMESTAMP
                FOR UPDATE
                """,
                (token_hash,),
            )
            token = cursor.fetchone()
            if not token:
                return False
            cursor.execute(
                "UPDATE public.users SET password_hash = %s WHERE id = %s",
                (password_hash, token["user_id"]),
            )
            cursor.execute(
                "UPDATE public.password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE id = %s",
                (token["id"],),
            )
            return True


def create_user(name, email, username, password_hash):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO public.users (name, email, username, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id, name, email, username, created_at
                """,
                (name, email, username, password_hash),
            )
            return cursor.fetchone()


def list_work_shifts():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, code, name,
                       to_char(start_time, 'HH24:MI') AS start_time,
                       to_char(end_time, 'HH24:MI') AS end_time,
                       planned_minutes, active
                FROM public.work_shifts
                ORDER BY start_time, code
                """
            )
            return cursor.fetchall()


def get_current_work_shift(current_time):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, code, name,
                       to_char(start_time, 'HH24:MI') AS start_time,
                       to_char(end_time, 'HH24:MI') AS end_time,
                       planned_minutes, active
                FROM public.work_shifts
                WHERE active = true
                  AND (
                    (start_time < end_time AND %s::time >= start_time AND %s::time < end_time)
                    OR
                    (start_time > end_time AND (%s::time >= start_time OR %s::time < end_time))
                  )
                ORDER BY start_time DESC
                LIMIT 1
                """,
                (current_time, current_time, current_time, current_time),
            )
            return cursor.fetchone()


def create_work_shift(code, name, start_time, end_time, planned_minutes, active):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO public.work_shifts
                    (code, name, start_time, end_time, planned_minutes, active)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, code, name,
                          to_char(start_time, 'HH24:MI') AS start_time,
                          to_char(end_time, 'HH24:MI') AS end_time,
                          planned_minutes, active
                """,
                (code, name, start_time, end_time, planned_minutes, active),
            )
            return cursor.fetchone()


def update_work_shift(shift_id, code, name, start_time, end_time, planned_minutes, active):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE public.work_shifts
                SET code = %s, name = %s, start_time = %s, end_time = %s,
                    planned_minutes = %s, active = %s
                WHERE id = %s
                RETURNING id, code, name,
                          to_char(start_time, 'HH24:MI') AS start_time,
                          to_char(end_time, 'HH24:MI') AS end_time,
                          planned_minutes, active
                """,
                (code, name, start_time, end_time, planned_minutes, active, shift_id),
            )
            return cursor.fetchone()


def delete_work_shift(shift_id):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM public.work_shifts WHERE id = %s RETURNING id", (shift_id,))
            return cursor.fetchone() is not None
