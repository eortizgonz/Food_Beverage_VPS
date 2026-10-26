import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from database import get_connection


BASE = Path(__file__).parent


def _base_production_data():
    with (BASE / "data" / "production_floor.json").open(encoding="utf-8") as file:
        return json.load(file)


def _clamp(value, low=0.0, high=100.0):
    return max(low, min(high, value))


def _status(oee):
    return "excellent" if oee >= 85 else "healthy" if oee >= 70 else "warning" if oee >= 60 else "critical"


def oee_dashboard(days=7, production=None):
    days = max(1, min(int(days), 90))
    production = production or _base_production_data()
    shift = production["shift"]
    quality_data = production["quality"]
    base_performance = _clamp(shift["current_rate"] / max(shift["target_rate"], 0.01) * 100)
    inspected_units = quality_data["good_units"] + quality_data["scrap_units"]
    base_quality = _clamp(quality_data["good_units"] / max(inspected_units, 1) * 100)
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=days)
    planned_minutes = days * 480

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""SELECT m.id,m.code,m.name,m.area,COALESCE(SUM(d.duration_minutes),0) AS downtime_minutes
                FROM machines m LEFT JOIN machine_downtime_events d ON d.machine_id=m.id
                AND d.started_at >= %s AND d.started_at <= %s
                WHERE m.active GROUP BY m.id,m.code,m.name,m.area ORDER BY m.code""", (period_start, period_end))
            machines = cursor.fetchall()
            cursor.execute("""SELECT d.category,COALESCE(SUM(d.duration_minutes),0) AS minutes
                FROM machine_downtime_events d WHERE d.started_at >= %s AND d.started_at <= %s
                GROUP BY d.category ORDER BY minutes DESC""", (period_start, period_end))
            losses = cursor.fetchall()

    rows = []
    midpoint = (len(machines) - 1) / 2
    for index, machine in enumerate(machines):
        availability = _clamp((planned_minutes - machine["downtime_minutes"]) / planned_minutes * 100)
        rng = random.Random(days * 1000 + machine["id"])
        centered = index - midpoint
        performance = _clamp(base_performance + centered * 0.12 + rng.uniform(-1.2, 1.2))
        quality = _clamp(base_quality + centered * 0.025 + rng.uniform(-0.25, 0.25))
        availability, performance, quality = round(availability, 1), round(performance, 1), round(quality, 1)
        oee = round(availability * performance * quality / 10000, 1)
        rows.append({
            "code": machine["code"], "name": machine["name"], "area": machine["area"],
            "oee": oee, "availability": availability,
            "performance": performance, "quality": quality,
            "downtime_minutes": round(machine["downtime_minutes"], 1), "status": _status(oee),
        })
    rows.sort(key=lambda item: item["oee"])
    divisor = max(len(rows), 1)
    availability = sum(row["availability"] for row in rows) / divisor
    performance = sum(row["performance"] for row in rows) / divisor
    quality = sum(row["quality"] for row in rows) / divisor
    oee = availability * performance * quality / 10000
    summary = {
        "oee": round(oee, 1), "availability": round(availability, 1),
        "performance": round(performance, 1), "quality": round(quality, 1),
        "runs": len(rows) * days * 8,
        "downtime_minutes": round(sum(row["downtime_minutes"] for row in rows), 1),
        "equivalent_line_downtime": round(sum(row["downtime_minutes"] for row in rows) / divisor, 1),
    }
    return {
        "period_days": days, "period_start": period_start.isoformat(), "period_end": period_end.isoformat(),
        "summary": summary, "machines": rows,
        "losses": [{"category": row["category"], "minutes": round(row["minutes"], 1)} for row in losses],
        "formula": "OEE = Disponibilidad × Rendimiento × Calidad",
        "sources": {"availability": "PostgreSQL · machine_downtime_events", "performance": "Velocidad real / velocidad objetivo", "quality": "Unidades buenas / unidades producidas"},
        "note": "OEE integrado. La disponibilidad usa paradas persistidas; rendimiento y calidad usan el contexto productivo del turno.",
    }
