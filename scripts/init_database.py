import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.conninfo import make_conninfo


BASE = Path(__file__).resolve().parents[1]
load_dotenv(BASE / ".env")
DATABASE_NAME = os.environ.get("DB_NAME", "Food_Beverage")


def connection_info(database):
    password = os.environ.get("DB_PASSWORD", "").strip()
    if not password or password == "CHANGE_ME":
        raise SystemExit("Configura DB_PASSWORD en el archivo .env antes de continuar.")
    return make_conninfo(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        dbname=database,
        user=os.environ.get("DB_USER", "postgres"),
        password=password,
        sslmode=os.environ.get("DB_SSLMODE", "prefer"),
    )


def main():
    admin_info = connection_info(os.environ.get("DB_ADMIN_NAME", "postgres"))
    with psycopg.connect(admin_info, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DATABASE_NAME,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DATABASE_NAME)))
                print(f"Base de datos creada: {DATABASE_NAME}")
            else:
                print(f"Base de datos existente: {DATABASE_NAME}")

    target_info = connection_info(DATABASE_NAME)
    with psycopg.connect(target_info) as connection:
        with connection.cursor() as cursor:
            for migration in sorted((BASE / "sql").glob("*.sql")):
                cursor.execute(migration.read_text(encoding="utf-8"))
                print(f"Migración aplicada: {migration.name}")
    print("Migraciones de base de datos aplicadas correctamente")
    print("La aplicación usará automáticamente la configuración de .env")


if __name__ == "__main__":
    main()
