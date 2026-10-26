import random
from datetime import date

from database import get_connection


LOSS_CATEGORIES = ["Avería", "Configuración", "Microparada", "Calidad", "Materiales"]


def oee_dashboard(days=7):
    days = max(1, min(int(days), 90))
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT code,name,area FROM machines WHERE active ORDER BY code")
            machines = cursor.fetchall()

    rows = []
    for index, machine in enumerate(machines):
        rng = random.Random(date.today().toordinal() * 10000 + days * 100 + index)
        availability = round(rng.uniform(86.0, 97.5), 1)
        performance = round(rng.uniform(76.0, 96.0), 1)
        quality = round(rng.uniform(94.5, 99.4), 1)
        oee = round(availability * performance * quality / 10000, 1)
        status = "excellent" if oee >= 85 else "healthy" if oee >= 70 else "warning" if oee >= 60 else "critical"
        rows.append({**machine, "oee": oee, "availability": availability, "performance": performance, "quality": quality, "status": status})
    rows.sort(key=lambda item: item["oee"])

    divisor = max(len(rows), 1)
    summary = {
        "oee": round(sum(row["oee"] for row in rows) / divisor, 1),
        "availability": round(sum(row["availability"] for row in rows) / divisor, 1),
        "performance": round(sum(row["performance"] for row in rows) / divisor, 1),
        "quality": round(sum(row["quality"] for row in rows) / divisor, 1),
        "runs": len(rows) * max(1, days) * 8,
    }
    loss_rng = random.Random(date.today().toordinal() + days * 31)
    losses = sorted(
        ({"category": category, "minutes": round(loss_rng.uniform(18, 65) * days, 1)} for category in LOSS_CATEGORIES),
        key=lambda item: item["minutes"], reverse=True,
    )
    return {
        "period_days": days, "summary": summary, "machines": rows, "losses": losses,
        "note": "Datos demostrativos. Los umbrales y pérdidas deben validarse antes de utilizarlos para decisiones operativas reales.",
    }
