import random
from datetime import date, datetime, time, timedelta, timezone

from database import get_connection

CAUSES = [("BRK", "Avería", "Falla mecánica", False), ("MIC", "Microparada", "Atasco o bloqueo de producto", False), ("SET", "Configuración", "Cambio de formato y ajuste", True), ("MAT", "Materiales", "Espera de material o empaque", False), ("QUA", "Calidad", "Inspección y retención preventiva", False), ("CLN", "Limpieza", "Limpieza y sanitización programada", True)]


def _ensure_demo_runs(cursor):
    cursor.execute("SELECT id FROM products WHERE code='BFP-1L'")
    product_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM work_shifts WHERE code='A'")
    shift_id = cursor.fetchone()["id"]
    start, end = datetime.now(timezone.utc) - timedelta(days=90), datetime.now(timezone.utc) + timedelta(days=365)
    cursor.execute("""INSERT INTO production_orders (order_number,product_id,planned_quantity,planned_start,planned_end,status,priority)
        VALUES ('DEMO-DOWNTIME',%s,9999999,%s,%s,'in_progress','normal') ON CONFLICT (order_number) DO UPDATE SET planned_end=EXCLUDED.planned_end RETURNING id""", (product_id, start, end))
    order_id = cursor.fetchone()["id"]
    cursor.execute("""INSERT INTO production_batches (batch_number,production_order_id,planned_quantity,actual_quantity,started_at,status)
        VALUES ('DEMO-DOWNTIME-BATCH',%s,9999999,0,%s,'in_progress') ON CONFLICT (batch_number) DO UPDATE SET production_order_id=EXCLUDED.production_order_id RETURNING id""", (order_id, start))
    batch_id = cursor.fetchone()["id"]
    cursor.execute("SELECT id FROM machines WHERE active ORDER BY id")
    for sequence, machine in enumerate(cursor.fetchall(), 1):
        cursor.execute("SELECT id FROM production_runs WHERE production_order_id=%s AND machine_id=%s LIMIT 1", (order_id, machine["id"]))
        if not cursor.fetchone():
            cursor.execute("""INSERT INTO production_runs (production_order_id,batch_id,product_id,machine_id,shift_id,operation_sequence,started_at,planned_minutes,ideal_cycle_time_seconds,status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,655200,1,'running')""", (order_id, batch_id, product_id, machine["id"], shift_id, sequence, start))


def append_random_downtime(probability=1.0, occurred_at=None):
    rng = random.SystemRandom()
    if rng.random() > probability:
        return 0
    with get_connection() as connection:
        with connection.cursor() as cursor:
            _ensure_demo_runs(cursor)
            cursor.execute("""SELECT r.id AS run_id,m.id AS machine_id FROM production_runs r JOIN machines m ON m.id=r.machine_id
                JOIN production_orders o ON o.id=r.production_order_id WHERE o.order_number='DEMO-DOWNTIME' AND m.active ORDER BY m.id""")
            run = rng.choice(cursor.fetchall())
            reason_code, category, description, planned = rng.choice(CAUSES)
            duration = round(rng.uniform(2, 18) if category == "Microparada" else rng.uniform(12, 145), 1)
            started = occurred_at or datetime.now(timezone.utc) - timedelta(minutes=duration)
            ended = None if occurred_at is None and rng.random() < 0.08 else started + timedelta(minutes=duration)
            cursor.execute("""INSERT INTO machine_downtime_events
                (production_run_id,machine_id,started_at,ended_at,duration_minutes,reason_code,reason_description,category,is_planned)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (run["run_id"], run["machine_id"], started, ended, duration, reason_code, description, category, planned))
    return 1


def seed_random_downtimes(count=90, days=30):
    rng = random.SystemRandom()
    return sum(append_random_downtime(1.0, datetime.now(timezone.utc) - timedelta(seconds=rng.uniform(0, max(1, days) * 86400))) for _ in range(max(0, count)))


def downtime_dashboard(days=30, date_from=None, date_to=None, machine=None, category=None, status=None):
    days = max(1, min(int(days), 90))
    start = date.fromisoformat(date_from) if date_from else date.today() - timedelta(days=days - 1)
    end = date.fromisoformat(date_to) if date_to else date.today()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT code,name FROM machines WHERE active ORDER BY code")
            machines = cursor.fetchall()
            cursor.execute("""SELECT d.id,m.code AS machine_code,m.name AS machine_name,m.area,d.started_at,d.ended_at,d.duration_minutes,d.category,
                d.reason_description AS cause,d.is_planned AS planned,CASE WHEN d.ended_at IS NULL THEN 'open' ELSE 'closed' END AS status
                FROM machine_downtime_events d JOIN machines m ON m.id=d.machine_id WHERE d.started_at >= %s AND d.started_at < %s ORDER BY d.started_at DESC""",
                (datetime.combine(start, time.min, tzinfo=timezone.utc), datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)))
            events = cursor.fetchall()
    filtered = [event for event in events if (not machine or machine == "all" or event["machine_code"] == machine) and (not category or category == "all" or event["category"] == category) and (not status or status == "all" or event["status"] == status)]
    serialized = [{**event, "started_at": event["started_at"].isoformat(), "ended_at": event["ended_at"].isoformat() if event["ended_at"] else None} for event in filtered]
    total = round(sum(event["duration_minutes"] for event in filtered), 1)
    by_category = []
    for _, name, _, _ in CAUSES:
        matches = [event for event in filtered if event["category"] == name]
        if matches:
            by_category.append({"category": name, "events": len(matches), "minutes": round(sum(event["duration_minutes"] for event in matches), 1)})
    by_category.sort(key=lambda item: item["minutes"], reverse=True)
    machine_minutes = {}
    for event in filtered:
        machine_minutes[event["machine_code"]] = machine_minutes.get(event["machine_code"], 0) + event["duration_minutes"]
    return {"filters": {"date_from": start.isoformat(), "date_to": end.isoformat(), "machine": machine or "all", "category": category or "all", "status": status or "all"}, "options": {"machines": machines, "categories": [item[1] for item in CAUSES]}, "summary": {"events": len(filtered), "total_minutes": total, "average_minutes": round(total / len(filtered), 1) if filtered else 0, "open_events": sum(item["status"] == "open" for item in filtered), "top_machine": max(machine_minutes, key=machine_minutes.get) if machine_minutes else "—"}, "events": serialized, "by_category": by_category, "note": "Eventos almacenados en PostgreSQL · machine_downtime_events."}
