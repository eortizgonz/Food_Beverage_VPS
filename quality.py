import random
from datetime import date, timedelta


PRODUCTS = [
    ("BFP-1L", "Bebida de fruta PET 1 L"),
    ("JUG-500", "Jugo pasteurizado 500 ml"),
    ("ISO-600", "Bebida isotónica 600 ml"),
]
LOSS_CATEGORIES = ["Peso fuera de especificación", "Sellado / tapa", "Etiquetado", "Control fisicoquímico", "Detector de metales"]


def quality_dashboard(days=7):
    days = max(1, min(int(days), 90))
    rng = random.Random(date.today().toordinal() * 100 + days)
    lot_count = max(3, min(18, days + 2))
    lots = []
    total = good = first_pass = 0
    for index in range(lot_count):
        code, product = PRODUCTS[index % len(PRODUCTS)]
        produced = rng.randint(38000, 61000)
        rejected = max(80, int(produced * rng.uniform(0.006, 0.028)))
        reworked = max(20, int(produced * rng.uniform(0.002, 0.011)))
        accepted = produced - rejected
        fpy = round((produced - rejected - reworked) / produced * 100, 1)
        quality = round(accepted / produced * 100, 1)
        status = "released" if quality >= 98.5 and fpy >= 97.8 else "review" if quality >= 98.0 else "hold"
        produced_on = date.today() - timedelta(days=index % days)
        lots.append({
            "lot": f"{code}-{produced_on:%y%m%d}-{index + 1:02d}", "product_code": code,
            "product": product, "produced": produced, "good": accepted,
            "rejected": rejected, "reworked": reworked, "fpy": fpy,
            "quality": quality, "status": status, "date": produced_on.isoformat(),
        })
        total += produced
        good += accepted
        first_pass += produced - rejected - reworked

    loss_values = []
    remaining = total - good
    weights = [0.34, 0.25, 0.18, 0.14, 0.09]
    for category, weight in zip(LOSS_CATEGORIES, weights):
        loss_values.append({"category": category, "units": round(remaining * weight)})

    trend = []
    for offset in range(min(days, 14) - 1, -1, -1):
        value = round(98.1 + rng.uniform(-0.7, 1.0), 1)
        trend.append({"date": (date.today() - timedelta(days=offset)).isoformat(), "quality": min(99.8, max(96.5, value))})

    held = sum(item["status"] == "hold" for item in lots)
    summary = {
        "quality": round(good / total * 100, 1),
        "fpy": round(first_pass / total * 100, 1),
        "rejected_units": total - good,
        "held_lots": held,
        "lots": len(lots),
        "total_units": total,
    }
    return {
        "period_days": days, "summary": summary, "lots": lots,
        "losses": loss_values, "trend": trend,
        "recommendation": f"Priorizar {loss_values[0]['category'].lower()}: concentra {loss_values[0]['units']:,} unidades rechazadas en el periodo.",
        "model_note": "Datos demostrativos; límites, estados y reglas de liberación requieren validación del área de Calidad.",
    }
