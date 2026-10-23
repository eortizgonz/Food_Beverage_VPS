import math
import random
from datetime import datetime


MACHINES = [
    ("RM-101", "Recepción de materia prima", "Transportador de recepción"),
    ("WS-110", "Lavado", "Lavadora rotativa"),
    ("CR-120", "Preparación", "Triturador industrial"),
    ("MX-130", "Mezcla", "Mezclador de alto corte"),
    ("PS-140", "Proceso térmico", "Pasteurizador tubular"),
    ("HM-150", "Homogeneización", "Homogeneizador"),
    ("TK-160", "Almacenamiento", "Tanque de proceso"),
    ("PU-170", "Transferencia", "Bomba sanitaria"),
    ("FL-210", "Llenado", "Llenadora rotativa"),
    ("CP-220", "Tapado", "Taponadora"),
    ("LB-230", "Etiquetado", "Etiquetadora"),
    ("PK-240", "Empaque", "Empacadora flow-pack"),
    ("CS-250", "Encajado", "Encajonadora automática"),
    ("PL-260", "Paletizado", "Paletizador robotizado"),
    ("CV-310", "Transporte", "Banda transportadora"),
    ("AC-320", "Servicios", "Compresor de aire"),
    ("CH-330", "Refrigeración", "Chiller de proceso"),
    ("BL-340", "Servicios", "Caldera de vapor"),
    ("CIP-350", "Limpieza", "Sistema CIP"),
    ("EX-360", "Extracción", "Extractor de aire"),
]

WEIGHTS = {"vibration": 0.25, "temperature": 0.20, "current": 0.17, "rpm": 0.14, "usage": 0.12, "pressure": 0.12}
LABELS = {"vibration": "Vibración", "temperature": "Temperatura", "current": "Corriente", "rpm": "RPM", "usage": "Uso", "pressure": "Presión"}


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def risk_level(score):
    if score >= 70:
        return "critical"
    if score >= 45:
        return "warning"
    return "healthy"


def simulated_machines():
    result = []
    for index, (machine_id, area, name) in enumerate(MACHINES):
        rng = random.Random(360_000 + index)
        age = rng.uniform(0.22, 0.96)
        vibration = round(1.2 + age * 6.9 + rng.uniform(-0.7, 0.7), 2)
        temperature = round(42 + age * 54 + rng.uniform(-6, 6), 1)
        current = round(12 + age * 42 + rng.uniform(-4, 4), 1)
        nominal_rpm = rng.choice([720, 960, 1200, 1450, 1750])
        rpm = int(nominal_rpm * (1 + rng.uniform(-0.13, 0.1)))
        usage_hours = int(900 + age * 8500 + rng.uniform(-300, 300))
        pressure = round(1.1 + age * 3.1 + rng.uniform(-0.35, 0.35), 2)
        normalized = {
            "vibration": clamp((vibration - 1.5) / 6.0 * 100),
            "temperature": clamp((temperature - 45) / 55 * 100),
            "current": clamp((current - 12) / 45 * 100),
            "rpm": clamp(abs(rpm - nominal_rpm) / nominal_rpm * 500),
            "usage": clamp(usage_hours / 10000 * 100),
            "pressure": clamp((pressure - 1.2) / 3.5 * 100),
        }
        score = round(sum(normalized[key] * WEIGHTS[key] for key in WEIGHTS), 1)
        level = risk_level(score)
        factors = sorted(
            ({"key": key, "label": LABELS[key], "score": round(value, 1), "contribution": round(value * WEIGHTS[key], 1)} for key, value in normalized.items()),
            key=lambda item: item["contribution"], reverse=True,
        )
        days = max(2, int(45 * math.pow(max(1, 100 - score) / 100, 1.7)))
        action = {
            "critical": "Programar inspección prioritaria, validar condición física y preparar mantenimiento en la próxima ventana disponible.",
            "warning": "Aumentar frecuencia de monitoreo y revisar los dos factores con mayor contribución.",
            "healthy": "Mantener plan preventivo y frecuencia normal de monitoreo.",
        }[level]
        result.append({
            "id": machine_id, "name": name, "area": area, "usage_hours": usage_hours,
            "vibration": vibration, "temperature": temperature, "current": current,
            "rpm": rpm, "nominal_rpm": nominal_rpm, "pressure": pressure,
            "risk": score, "status": level, "factors": factors,
            "recommended_action": action, "intervention_horizon_days": days,
        })
    return sorted(result, key=lambda machine: machine["risk"], reverse=True)


def predictive_payload():
    machines = simulated_machines()
    counts = {level: sum(machine["status"] == level for machine in machines) for level in ("healthy", "warning", "critical")}
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "model": "Modelo demostrativo ponderado v1",
        "weights": [{"key": key, "label": LABELS[key], "weight": int(value * 100)} for key, value in WEIGHTS.items()],
        "summary": {**counts, "average_risk": round(sum(machine["risk"] for machine in machines) / len(machines), 1)},
        "recommended": machines[0], "machines": machines,
    }
