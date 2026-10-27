from database import get_connection
from machine_profiles import manual_sections
from rag_service import ingest_text


def manual_name(machine):
    return f"MAN-EQP-{machine['code']}_mantenimiento_predictivo.md"


def manual_text(machine):
    process, diagnostic_sections = manual_sections(machine)
    return f"""# Manual de mantenimiento predictivo {machine['code']} — {machine['name']}
Área: {machine['area']}. Tipo: {machine['machine_type']}. Función: {process}.

## Seguridad e inocuidad
Solo personal autorizado puede intervenir. Aplicar parada segura, bloqueo y etiquetado LOTO, verificar energía cero y proteger o retener el producto expuesto. Nunca anular guardas, enclavamientos ni alarmas. Documentar hallazgos y liberar el equipo conforme al procedimiento de planta.

## Límites de referencia
Uso: {machine['max_usage_hours']} h. Vibración: {machine['max_vibration']} mm/s. Temperatura: {machine['max_temperature']} °C. Corriente nominal: {machine['rated_current']} A. Velocidad nominal: {machine['nominal_rpm']} rpm. Presión máxima: {machine['max_pressure']} bar. Los límites son demostrativos y deben validarse contra el fabricante y el proceso real.

## Diagnóstico por variable
{diagnostic_sections}

## Decisión según probabilidad de falla
- Menor de 40 % — Condición estable: continuar operación, confirmar tendencia y mantener la ronda preventiva.
- Entre 40 % y 69.9 % — Degradación incipiente: aumentar la frecuencia de medición y programar inspección en la próxima ventana.
- Desde 70 % — Riesgo alto: evaluar parada controlada, aplicar LOTO y escalar a Mantenimiento y Producción.

Confirmar cualquier lectura con instrumento verificado y revisar tendencia, alarmas, orden activa e historial antes de concluir. Calidad debe evaluar el producto cuando pueda afectarse temperatura, presión, dosificación, sellado o limpieza.

## Retorno a servicio
Retirar herramientas y materiales, reinstalar protecciones, ejecutar prueba sin producto cuando corresponda, confirmar variables estables, completar registro y obtener autorización del responsable del área."""


def ingest_machine_manuals():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM machines WHERE active ORDER BY code")
            machines = cursor.fetchall()
    if not machines:
        raise ValueError("No existen máquinas activas para generar manuales.")
    chunks = 0
    for machine in machines:
        chunks += ingest_text(manual_name(machine), manual_text(machine))
    return len(machines), chunks
