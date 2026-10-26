from database import get_connection
from rag_service import ingest_text


PROFILES = {
    "Transportador": ("desalineación, tensión incorrecta, rodamiento deteriorado o acumulación de producto", "alinear y tensionar; inspeccionar rodillos, cadena, guardas y lubricación autorizada"),
    "Lavadora": ("boquillas obstruidas, bomba fuera de curva, transmisión desgastada o drenaje restringido", "verificar boquillas, caudal, bomba, filtros, transmisión y drenajes"),
    "Triturador": ("sobrecarga, cuchillas desgastadas, material extraño o rodamientos deteriorados", "aislar energías; revisar cámara, cuchillas, criba, acople y rodamientos"),
    "Mezclador": ("carga o viscosidad fuera de rango, impulsor desalineado, sello o reductor deteriorado", "confirmar receta y carga; revisar impulsor, sello, acople, reductor y rodamientos"),
    "Pasteurizador": ("incrustación, flujo insuficiente, control térmico inestable o bomba degradada", "retener producto afectado; comprobar tiempo/temperatura, caudal, intercambiador, válvulas y sensores"),
    "Homogeneizador": ("presión anormal, válvulas desgastadas, cavitación, sellos o rodamientos deteriorados", "verificar presión, alimentación, válvulas, sellos, lubricación y condición del accionamiento"),
    "Tanque": ("agitador desbalanceado, nivel anormal, sello degradado o incrustación", "verificar nivel y receta; inspeccionar agitador, sello, venteo y condición sanitaria"),
    "Bomba": ("cavitación, entrada de aire, restricción en succión o sello mecánico desgastado", "confirmar nivel y presión; revisar válvulas, filtros, impulsor, sello y alineación"),
    "Llenadora": ("dosificador desajustado, carrusel con fricción, transmisión desgastada o producto acumulado", "detener de forma segura; validar dosificación, limpiar, revisar transmisión, guías y rodamientos"),
    "Taponadora": ("torque fuera de rango, cabezal desgastado, atasco de tapas o desalineación", "retener muestras; comprobar torque, cabezales, alimentador, guías y sincronismo"),
    "Etiquetadora": ("sensor sucio, tensión de bobina incorrecta, rodillos desgastados o desincronización", "verificar sensores, bobina, rodillos, adhesivo, encoder y sincronismo"),
    "Empacadora": ("material atascado, arrastre desalineado, temperatura de sellado o transmisión anormal", "realizar despeje autorizado; revisar guías, mordazas, sellado, cadenas y sincronismo"),
    "Encajonadora": ("cartón atascado, ventosas degradadas, guías desalineadas o servomotor sobrecargado", "retirar atasco con LOTO; revisar vacío, guías, actuadores, sensores y servo"),
    "Robot": ("carga fuera de especificación, efector desajustado, eje o servo con desgaste", "delimitar la celda; revisar carga, efector, ejes, reductores, cables y alarmas del controlador"),
    "Compresor": ("filtro restringido, lubricación insuficiente, fuga, temperatura alta o elemento compresor desgastado", "comprobar presión y temperatura; revisar filtros, aceite, fugas, enfriamiento y rodamientos"),
    "Chiller": ("flujo bajo, condensador sucio, refrigerante insuficiente o bomba degradada", "verificar caudal y temperaturas; revisar filtros, bomba, condensador, presiones y fugas"),
    "Caldera": ("agua fuera de especificación, incrustación, combustión inestable o control de presión defectuoso", "escalar a operador autorizado; verificar nivel, tratamiento, combustión, purgas y protecciones"),
    "Sistema CIP": ("caudal o concentración insuficiente, retorno restringido, válvula defectuosa o temperatura baja", "verificar secuencia, concentración, tiempo, temperatura, caudal, retorno y válvulas"),
    "Extractor": ("filtros saturados, ducto restringido, ventilador desbalanceado o correa desgastada", "aislar el equipo; revisar filtros, ductos, impulsor, correas, alineación y rodamientos"),
}


def manual_name(machine):
    return f"MAN-EQP-{machine['code']}_mantenimiento_predictivo.md"


def manual_text(machine):
    failure, inspection = PROFILES.get(machine["machine_type"], ("desgaste mecánico, condición eléctrica anormal o sensor fuera de calibración", "verificar carga, sensores, conexiones, lubricación y elementos móviles"))
    return f"""# Manual de mantenimiento predictivo {machine['code']} — {machine['name']}
Área: {machine['area']}. Tipo: {machine['machine_type']}.

## Seguridad e inocuidad
Solo personal autorizado puede intervenir. Aplicar parada segura, bloqueo y etiquetado LOTO, verificar energía cero y proteger o retener el producto expuesto. Nunca anular guardas, enclavamientos ni alarmas. Documentar hallazgos y liberar el equipo conforme al procedimiento de planta.

## Límites de referencia
Uso: {machine['max_usage_hours']} h. Vibración: {machine['max_vibration']} mm/s. Temperatura: {machine['max_temperature']} °C. Corriente nominal: {machine['rated_current']} A. Velocidad nominal: {machine['nominal_rpm']} rpm. Presión máxima: {machine['max_pressure']} bar. Los límites son demostrativos y deben validarse contra el fabricante y el proceso real.

## Diagnóstico
Las causas probables incluyen {failure}. Confirmar cualquier lectura con instrumento verificado y revisar la tendencia, las alarmas, la orden activa y el historial de mantenimiento antes de concluir.

## Inspección recomendada
{inspection}. Si dos variables exceden el límite o una supera 115 %, escalar de inmediato a Mantenimiento y Producción. Calidad debe evaluar el producto cuando pueda afectarse temperatura, presión, dosificación, sellado o limpieza.

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
