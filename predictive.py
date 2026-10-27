import math
import random
from datetime import datetime, timedelta, timezone

from database import get_connection
from machine_profiles import diagnostic_for


WEIGHTS = {
    "vibration": 0.25, "temperature": 0.20, "current": 0.17,
    "rpm": 0.14, "usage": 0.12, "pressure": 0.12,
}
LABELS = {
    "usage": "Horas de uso", "vibration": "Vibración", "temperature": "Temperatura",
    "current": "Corriente", "rpm": "Desviación de RPM", "pressure": "Presión",
}
CONDITION_PROFILES = [
    0.28, 0.82, 0.48, 0.94, 0.36, 0.69, 0.22, 0.57, 0.76, 0.31,
    0.44, 0.88, 0.25, 0.63, 0.72, 0.39, 0.91, 0.53, 0.18, 0.66,
]

def rule_score(ratio):
    ratio = max(0.0, ratio)
    if ratio <= 0.60:
        return 0.0
    if ratio <= 0.80:
        return (ratio - 0.60) / 0.20 * 25.0
    if ratio <= 1.00:
        return 25.0 + (ratio - 0.80) / 0.20 * 45.0
    if ratio <= 1.15:
        return 70.0 + (ratio - 1.00) / 0.15 * 30.0
    return 100.0


def calculate_risk(machine, values):
    ratios = {
        "usage": values["usage_hours"] / machine["max_usage_hours"],
        "vibration": values["vibration"] / machine["max_vibration"],
        "temperature": values["temperature"] / machine["max_temperature"],
        "current": values["current"] / machine["rated_current"],
        "rpm": abs(values["rpm"] - machine["nominal_rpm"]) / max(machine["nominal_rpm"], 1) / 0.20,
        "pressure": values["pressure"] / max(machine["max_pressure"], 0.01),
    }
    scores = {key: rule_score(value) for key, value in ratios.items()}
    contributions = {key: scores[key] * WEIGHTS[key] for key in scores}
    risk = sum(contributions.values())
    exceeded = sum(value >= 1.0 for value in ratios.values())
    if any(value >= 1.15 for value in ratios.values()):
        risk = max(risk, 75.0)
    elif exceeded >= 2:
        risk = max(risk, 70.0)
    elif exceeded == 1:
        risk = max(risk, 45.0)
    risk = round(min(99.0, max(1.0, risk)), 1)
    status = "critical" if risk >= 70 else "warning" if risk >= 40 else "healthy"
    factors = sorted(
        ({"key": key, "label": LABELS[key], "score": round(scores[key], 1), "contribution": round(contributions[key], 1)} for key in scores),
        key=lambda item: item["contribution"], reverse=True,
    )
    explanation = f"Factores principales: {factors[0]['label']} ({factors[0]['contribution']} puntos) y {factors[1]['label']} ({factors[1]['contribution']} puntos)."
    return risk, status, explanation, factors


def bounded(value, lower, upper, decimals=2):
    return round(max(lower, min(upper, value)), decimals)


def values_from_condition(machine, level, rng, usage_hours=None, phase=0.0):
    load = max(0.12, min(1.08, level + math.sin(phase) * 0.035 + rng.gauss(0, 0.025)))
    if rng.random() < 0.025:
        load = min(1.12, load + rng.uniform(0.06, 0.14))
    direction = -1 if rng.random() < 0.5 else 1
    hours = usage_hours if usage_hours is not None else machine["max_usage_hours"] * (0.30 + load * 0.70)
    return {
        "usage_hours": bounded(hours, 0, machine["max_usage_hours"] * 1.15, 1),
        "vibration": bounded(machine["max_vibration"] * (0.30 + load * 0.72) + rng.gauss(0, machine["max_vibration"] * 0.015), 0, machine["max_vibration"] * 1.15),
        "temperature": bounded(machine["max_temperature"] * (0.42 + load * 0.61) + rng.gauss(0, machine["max_temperature"] * 0.01), 0, machine["max_temperature"] * 1.15, 1),
        "current": bounded(machine["rated_current"] * (0.36 + load * 0.68) + rng.gauss(0, machine["rated_current"] * 0.012), 0, machine["rated_current"] * 1.15, 1),
        "rpm": bounded(machine["nominal_rpm"] * (1 + direction * load * 0.20) + rng.gauss(0, max(machine["nominal_rpm"] * 0.008, 0.1)), machine["nominal_rpm"] * 0.72, machine["nominal_rpm"] * 1.28, 0),
        "pressure": bounded(machine["max_pressure"] * (0.34 + load * 0.70) + rng.gauss(0, machine["max_pressure"] * 0.012), 0, machine["max_pressure"] * 1.15),
    }


def insert_reading(cursor, machine, recorded_at, values):
    risk, status, explanation, _ = calculate_risk(machine, values)
    cursor.execute(
        """INSERT INTO machine_readings
        (machine_id,recorded_at,usage_hours,vibration,temperature,current_amps,rpm,pressure,failure_probability,health_status,explanation)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (machine_id,recorded_at) DO NOTHING""",
        (machine["id"], recorded_at, values["usage_hours"], values["vibration"], values["temperature"], values["current"], values["rpm"], values["pressure"], risk, status, explanation),
    )


def append_snapshot(minimum_interval_seconds=10):
    now = datetime.now(timezone.utc)
    seed_interval = max(1, minimum_interval_seconds)
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM machines WHERE active ORDER BY id")
            machines = cursor.fetchall()
            for index, machine in enumerate(machines):
                cursor.execute("SELECT * FROM machine_readings WHERE machine_id=%s ORDER BY recorded_at DESC LIMIT 1", (machine["id"],))
                latest = cursor.fetchone()
                if not latest:
                    for hour in range(24, 0, -1):
                        historical_at = now - timedelta(hours=hour)
                        history_rng = random.Random(2026 + machine["id"] * 100 + hour)
                        progress = (24 - hour) / 24
                        history_level = CONDITION_PROFILES[index % len(CONDITION_PROFILES)] * (0.78 + 0.22 * progress)
                        history_usage = machine["max_usage_hours"] * (0.30 + history_level * 0.70)
                        insert_reading(cursor, machine, historical_at, values_from_condition(machine, history_level, history_rng, history_usage, historical_at.timestamp() / 86400 * math.tau))
                if latest and (now - latest["recorded_at"]).total_seconds() < minimum_interval_seconds:
                    continue
                rng = random.Random(int(now.timestamp() // seed_interval) + machine["id"] * 2026)
                level = CONDITION_PROFILES[index % len(CONDITION_PROFILES)]
                usage = None
                if latest:
                    elapsed = max(0, (now - latest["recorded_at"]).total_seconds() / 3600)
                    usage = latest["usage_hours"] + elapsed
                    observed = max(latest["vibration"] / machine["max_vibration"], latest["temperature"] / machine["max_temperature"])
                    level = max(0.1, min(1.08, (observed - 0.30) / 0.72 + rng.gauss(0, 0.018)))
                insert_reading(cursor, machine, now, values_from_condition(machine, level, rng, usage, now.timestamp() / 86400 * math.tau))


def predictive_payload(refresh=False):
    if refresh:
        append_snapshot()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT ON (m.id) m.*, r.recorded_at, r.usage_hours, r.vibration,
                    r.temperature, r.current_amps, r.rpm, r.pressure,
                    r.failure_probability, r.health_status, r.explanation
                FROM machines m JOIN machine_readings r ON r.machine_id=m.id
                WHERE m.active ORDER BY m.id, r.recorded_at DESC
            """)
            rows = cursor.fetchall()
            machines = []
            for row in rows:
                values = {"usage_hours": row["usage_hours"], "vibration": row["vibration"], "temperature": row["temperature"], "current": row["current_amps"], "rpm": row["rpm"], "pressure": row["pressure"]}
                _, _, _, factors = calculate_risk(row, values)
                cursor.execute("SELECT count(*) AS samples, avg(failure_probability) AS average, min(failure_probability) AS minimum, max(failure_probability) AS maximum FROM machine_readings WHERE machine_id=%s AND recorded_at >= %s", (row["id"], row["recorded_at"] - timedelta(hours=24)))
                trend = cursor.fetchone()
                actions = {"critical": "Programar inspección prioritaria y preparar mantenimiento en la próxima ventana disponible.", "warning": "Aumentar la frecuencia de monitoreo y revisar los factores dominantes.", "healthy": "Mantener el plan preventivo y la frecuencia normal de monitoreo."}
                limits = {"usage_hours": row["max_usage_hours"], "vibration": row["max_vibration"], "temperature": row["max_temperature"], "current": row["rated_current"], "nominal_rpm": row["nominal_rpm"], "pressure": row["max_pressure"]}
                machine = {"id": row["code"], "name": row["name"], "type": row["machine_type"], "area": row["area"], **values, "limits": limits, "risk": row["failure_probability"], "status": row["health_status"], "explanation": row["explanation"], "recorded_at": row["recorded_at"], "factors": factors, "manual": diagnostic_for(row, factors, row["failure_probability"], row["health_status"], values, limits), "recommended_action": actions[row["health_status"]], "intervention_horizon_days": max(2, int(45 * math.pow(max(1, 100 - row["failure_probability"]) / 100, 1.7))), "trend_24h": {"samples": trend["samples"], "average": round(float(trend["average"] or 0), 1), "minimum": round(float(trend["minimum"] or 0), 1), "maximum": round(float(trend["maximum"] or 0), 1)}}
                machines.append(machine)
    machines.sort(key=lambda item: item["risk"], reverse=True)
    if not machines:
        return {"generated_at": None, "model": "Índice demostrativo por umbrales ponderados", "weights": [{"key": key, "label": LABELS[key], "weight": int(value * 100)} for key, value in WEIGHTS.items()], "summary": {"healthy": 0, "warning": 0, "critical": 0, "total": 0, "average_risk": 0}, "recommended": None, "machines": []}
    counts = {level: sum(machine["status"] == level for machine in machines) for level in ("healthy", "warning", "critical")}
    return {"generated_at": max(machine["recorded_at"] for machine in machines).isoformat(), "model": "Índice demostrativo por umbrales ponderados", "weights": [{"key": key, "label": LABELS[key], "weight": int(value * 100)} for key, value in WEIGHTS.items()], "summary": {**counts, "total": len(machines), "average_risk": round(sum(machine["risk"] for machine in machines) / len(machines), 1)}, "recommended": machines[0], "machines": machines}
