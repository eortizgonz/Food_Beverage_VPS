RISK_LEVELS = {
    "healthy": {
        "label": "Condición estable",
        "strategy": "Continuar operación y confirmar la tendencia en la ronda preventiva.",
        "priority": "Seguimiento",
    },
    "warning": {
        "label": "Degradación incipiente",
        "strategy": "Programar inspección en la próxima ventana y aumentar la frecuencia de medición.",
        "priority": "Planificar",
    },
    "critical": {
        "label": "Riesgo alto de falla",
        "strategy": "Evaluar parada controlada, aplicar LOTO y escalar de inmediato a Mantenimiento y Producción.",
        "priority": "Intervenir",
    },
}


MACHINE_PROFILES = {
    "RM-101": ("recepción y alimentación de materia prima", "banda de recepción", "rodillos de carga", "motorreductor", "tambor motriz", "tensor neumático", "rodamientos de cabecera"),
    "WS-110": ("lavado rotativo de materia prima", "tambor y apoyos", "circuito de aspersión", "motor de giro", "transmisión del tambor", "bomba de lavado", "sellos y chumaceras"),
    "CR-120": ("reducción de tamaño", "rotor y cuchillas", "cámara de trituración", "motor principal", "acople de transmisión", "criba de descarga", "rodamientos del rotor"),
    "MX-130": ("mezcla de alto corte", "eje e impulsor", "sello mecánico", "motor del mezclador", "variador y acople", "circuito de recirculación", "reductor principal"),
    "PS-140": ("tratamiento térmico", "bomba de producto", "intercambiador tubular", "accionamiento de circulación", "control de caudal", "circuito de producto", "placas y juntas sanitarias"),
    "HM-150": ("homogeneización a presión", "cabezal homogeneizador", "bloque de válvulas", "motor principal", "cigüeñal y transmisión", "pistones de alta presión", "cojinetes del cigüeñal"),
    "TK-160": ("almacenamiento y agitación", "agitador superior", "sello del eje", "motor del agitador", "reductor de baja velocidad", "venteos y línea de retorno", "apoyo del eje"),
    "PU-170": ("transferencia sanitaria", "impulsor y eje", "sello mecánico", "motor de la bomba", "acople bomba-motor", "succión e impulsión", "rodamientos del conjunto"),
    "FL-210": ("llenado volumétrico", "carrusel de llenado", "válvulas dosificadoras", "motor del carrusel", "sincronismo de estrellas", "colector de producto", "transmisión central"),
    "CP-220": ("aplicación y torque de tapas", "cabezales de tapado", "embragues de torque", "motor de la taponadora", "sincronismo con transportador", "alimentador de tapas", "rodamientos de cabezales"),
    "LB-230": ("aplicación de etiquetas", "rodillos de arrastre", "aplicador y adhesivo", "servomotor de avance", "encoder de sincronismo", "tensión de bobina", "cojinetes de rodillos"),
    "PK-240": ("formado, sellado y corte", "mordazas de sellado", "resistencias y termopares", "motor de arrastre", "sincronismo de corte", "neumática de mordazas", "cadenas y rodamientos"),
    "CS-250": ("formado y cerrado de cajas", "brazos y guías", "sistema de vacío", "servomotor de empuje", "sincronismo de actuadores", "circuito neumático", "reductores de ejes"),
    "PL-260": ("paletizado robotizado", "ejes y reductores", "servomotores", "controladores de eje", "calibración cinemática", "efector y circuito de vacío", "reductor del eje principal"),
    "CV-310": ("transporte entre procesos", "banda modular", "rodillos de retorno", "motorreductor", "tambor y encoder", "tensor de banda", "chumaceras motrices"),
    "AC-320": ("generación de aire comprimido", "elemento compresor", "enfriador y lubricación", "motor eléctrico", "acople del elemento", "separador y red de descarga", "rodamientos del tornillo"),
    "CH-330": ("refrigeración de proceso", "compresor frigorífico", "condensador", "motor del compresor", "control de capacidad", "circuito refrigerante", "bomba y rodamientos"),
    "BL-340": ("generación de vapor", "ventilador y quemador", "hogar y superficies térmicas", "motor del ventilador", "control de combustión", "circuito agua-vapor", "bomba de alimentación"),
    "CIP-350": ("limpieza en sitio", "bomba de impulsión CIP", "calentador de solución", "motor de recirculación", "secuencia de válvulas", "retorno y concentración", "sello y rodamientos de bomba"),
    "EX-360": ("extracción y renovación de aire", "impulsor del extractor", "filtros y ductos", "motor del ventilador", "correas y poleas", "compuertas de descarga", "rodamientos del ventilador"),
}


MACHINE_RISK_GUIDANCE = {
    "RM-101": {
        "healthy": ("La banda conserva alineación y tensión; no hay indicios de pérdida de tracción.", "Confirmar centrado, limpiar derrames y registrar tensión en la ronda de recepción."),
        "warning": ("Se perfila desalineación de banda o rodillo de carga con fricción creciente.", "Programar ajuste de tensores y revisar giro libre de rodillos antes del siguiente lote."),
        "critical": ("Existe riesgo de salida de banda, atasco de materia prima o falla del rodamiento de cabecera.", "Detener alimentación de forma controlada, aplicar LOTO y corregir alineación, tensor y rodamiento afectado."),
    },
    "WS-110": {
        "healthy": ("El tambor gira estable y el circuito de lavado mantiene una carga normal.", "Verificar boquillas, drenaje y apoyos durante la limpieza programada."),
        "warning": ("El tambor puede estar cargándose de forma desigual o presentar apoyo/boquilla restringida.", "Vaciar el tambor, limpiar boquillas y comprobar transmisión, apoyos y caudal de lavado."),
        "critical": ("Hay riesgo de bloqueo del tambor, daño de transmisión o pérdida de caudal sanitario.", "Suspender ingreso de producto, retener material expuesto y revisar tambor, bomba, transmisión y drenajes bajo LOTO."),
    },
    "CR-120": {
        "healthy": ("Rotor, cuchillas y criba trabajan dentro del patrón esperado de trituración.", "Mantener inspección de filo, fijaciones y ausencia de cuerpos extraños."),
        "warning": ("Se anticipa desgaste de cuchillas, criba parcialmente obstruida o alimentación excesiva.", "Reducir carga, inspeccionar filo y luz de cuchillas, y limpiar la criba en ventana segura."),
        "critical": ("El rotor puede sufrir atasco severo, impacto por cuerpo extraño o daño de rodamiento.", "Parar de inmediato la alimentación, aislar energías e inspeccionar rotor, cuchillas, criba y cojinetes."),
    },
    "MX-130": {
        "healthy": ("La mezcla mantiene carga homogénea sin señales de desbalance del impulsor.", "Confirmar receta, nivel, sello y lubricación del reductor."),
        "warning": ("La viscosidad/carga puede estar elevada o el impulsor empieza a perder alineación.", "Validar receta y nivel; programar revisión de impulsor, sello, acople y reductor."),
        "critical": ("Existe riesgo de falla del sello, contacto del impulsor o sobrecarga del motor.", "Detener mezcla de forma controlada, retener el lote y revisar eje, impulsor, sello y accionamiento bajo LOTO."),
    },
    "PS-140": {
        "healthy": ("El circuito térmico conserva estabilidad compatible con el tratamiento del producto.", "Continuar control de tiempo, temperatura, caudal y diferencial de presión."),
        "warning": ("Puede existir incrustación tubular, caudal reducido o deriva de control térmico.", "Aumentar muestreo, validar sensores y programar inspección/CIP del intercambiador."),
        "critical": ("Hay riesgo de pérdida del tratamiento térmico o contaminación cruzada por fuga interna.", "Desviar y retener producto, detener el proceso y verificar intercambiador, válvulas, bomba y sensores antes de liberar."),
    },
    "HM-150": {
        "healthy": ("El cabezal y las válvulas sostienen una homogeneización estable.", "Registrar presión por etapa y verificar lubricación y fugas del cabezal."),
        "warning": ("Se anticipa desgaste de válvula, cavitación o degradación de sello/pistón.", "Reducir carga si procede y revisar alimentación, válvulas, sellos y lubricación en la próxima ventana."),
        "critical": ("Existe riesgo de falla del cabezal de alta presión o daño de cigüeñal.", "Despresurizar, aplicar LOTO y realizar inspección prioritaria de válvulas, pistones, cabezal y transmisión."),
    },
    "TK-160": {
        "healthy": ("El agitador mantiene movimiento estable y el tanque conserva condición sanitaria.", "Comprobar nivel, venteo, sello y ausencia de acumulación en el eje."),
        "warning": ("Se perfila desbalance del agitador, sello fatigado o nivel operativo inadecuado.", "Corregir nivel y programar revisión del eje, paletas, sello y reductor."),
        "critical": ("Hay riesgo de rotura del sello, contacto del agitador o contaminación del producto.", "Detener agitación, retener el lote y revisar integridad de eje, sello, apoyos y tanque bajo procedimiento sanitario."),
    },
    "PU-170": {
        "healthy": ("La bomba mantiene transferencia estable sin evidencia consistente de cavitación.", "Verificar nivel de succión, ausencia de fugas y condición del sello en la ronda."),
        "warning": ("Se anticipa cavitación incipiente, restricción de succión o desgaste del sello mecánico.", "Comprobar NPSH disponible, limpiar filtro y programar inspección de impulsor, sello y alineación."),
        "critical": ("La bomba presenta riesgo de cavitación severa, falla del sello o daño de impulsor/rodamiento.", "Cambiar a bomba de respaldo si existe, aislar la PU-170 y revisar succión, impulsor, sello, acople y rodamientos."),
    },
    "FL-210": {
        "healthy": ("Carrusel y válvulas dosificadoras conservan sincronismo de llenado.", "Mantener control de volumen, limpieza de boquillas y verificación de estrellas."),
        "warning": ("Puede existir fricción del carrusel, válvula dosificadora lenta o pérdida de sincronismo.", "Incrementar muestreo de volumen y programar limpieza y revisión de válvulas, guías y transmisión."),
        "critical": ("Existe riesgo de atasco del carrusel, sobrellenado/subllenado o daño de transmisión.", "Detener ingreso de envases, retener producción desde el último control conforme y revisar carrusel, dosificadores y sincronismo."),
    },
    "CP-220": {
        "healthy": ("Los cabezales aplican tapas con torque y sincronismo estables.", "Confirmar torque por muestreo y limpiar alimentador y guías."),
        "warning": ("Se anticipa desgaste de cabezal, embrague desajustado o atasco en el alimentador.", "Aumentar control de torque y programar ajuste de cabezales, embragues y guías."),
        "critical": ("Hay riesgo de tapas flojas, deformadas o bloqueo del conjunto de tapado.", "Parar la taponadora, segregar envases desde la última muestra conforme y revisar cabezales, torque y alimentación."),
    },
    "LB-230": {
        "healthy": ("La etiqueta avanza centrada y sincronizada con el envase.", "Limpiar sensores y rodillos y verificar tensión de bobina."),
        "warning": ("Puede haber deslizamiento de rodillo, encoder inestable o tensión incorrecta de bobina.", "Revisar adhesivo, tensión, rodillos, fotocelda y calibración del encoder."),
        "critical": ("Existe riesgo de etiquetado fuera de posición, rotura continua de banda o atasco del aplicador.", "Detener alimentación, separar producto no identificable y corregir aplicador, arrastre, sensores y sincronismo."),
    },
    "PK-240": {
        "healthy": ("Arrastre, mordazas y corte operan con un patrón estable de empaque.", "Verificar temperatura de sellado, centrado de film y limpieza de mordazas."),
        "warning": ("Se perfila desalineación del film, termopar inestable o desgaste de cadena/mordaza.", "Aumentar pruebas de sello y programar ajuste de film, mordazas, resistencias y transmisión."),
        "critical": ("Hay riesgo de sello abierto, corte fuera de fase o atrapamiento de producto en mordazas.", "Detener la empacadora, retener paquetes desde la última prueba conforme y revisar sellado, corte, arrastre y neumática."),
    },
    "CS-250": {
        "healthy": ("La encajonadora mantiene vacío, guiado y secuencia de empuje estables.", "Comprobar ventosas, guías, sensores y calidad del cartón."),
        "warning": ("Se anticipa pérdida de vacío, cartón deformado o servo con carga creciente.", "Limpiar ventosas, ajustar guías y revisar actuadores y corriente del servomotor."),
        "critical": ("Existe riesgo de colisión de brazos, atasco de caja o falla del sistema de vacío.", "Parar entrada de producto, retirar atasco bajo LOTO y verificar brazos, guías, vacío, sensores y servo."),
    },
    "PL-260": {
        "healthy": ("Los ejes del robot conservan repetibilidad y carga dentro de la trayectoria validada.", "Revisar alarmas, efector, mangueras y fijaciones en la inspección de celda."),
        "warning": ("Puede existir holgura de reductor, servo sobrecargado o pérdida de vacío del efector.", "Reducir velocidad si está autorizado y programar calibración de ejes, revisión de reductores y prueba del efector."),
        "critical": ("Hay riesgo de pérdida de posición, caída de carga o colisión dentro de la celda.", "Aislar y delimitar la celda; descargar el robot y revisar ejes, frenos, reductores, efector y controlador."),
    },
    "CV-310": {
        "healthy": ("La banda modular mantiene velocidad, centrado y retorno uniformes.", "Retirar acumulaciones y verificar tensor, rodillos y guardas."),
        "warning": ("Se perfila banda destensada, rodillo trabado o desgaste del motorreductor.", "Programar tensado y alineación; revisar rodillos de retorno y lubricación de chumaceras."),
        "critical": ("Existe riesgo de rotura/salida de banda o bloqueo del transporte entre procesos.", "Detener equipos aguas arriba, aplicar LOTO y reparar banda, tambor, tensor y chumaceras antes de reiniciar."),
    },
    "AC-320": {
        "healthy": ("El compresor sostiene presión y temperatura compatibles con la demanda de planta.", "Revisar nivel de aceite, diferencial de filtros, purgas y fugas de red."),
        "warning": ("Se anticipa filtro restringido, enfriamiento deficiente o desgaste del elemento compresor.", "Reducir demanda no crítica y programar revisión de filtros, aceite, radiador, separador y fugas."),
        "critical": ("Hay riesgo de alta temperatura, arrastre de aceite o falla del elemento de tornillo.", "Transferir carga al compresor de respaldo, detener AC-320 y revisar lubricación, enfriador, separador y rodamientos."),
    },
    "CH-330": {
        "healthy": ("El chiller mantiene circulación y rechazo térmico estables.", "Registrar temperaturas de entrada/salida y limpiar filtros según plan."),
        "warning": ("Puede existir condensador sucio, caudal bajo o carga de refrigerante insuficiente.", "Programar limpieza del condensador y comprobar bomba, filtros, presiones y sobrecalentamiento."),
        "critical": ("Existe riesgo de disparo del compresor y pérdida de refrigeración del proceso.", "Proteger el producto sensible, transferir carga térmica si es posible y revisar compresor, refrigerante, condensador y bomba."),
    },
    "BL-340": {
        "healthy": ("La caldera conserva combustión, nivel y presión de vapor estables.", "Continuar pruebas de nivel, purga, conductividad y dispositivos de seguridad."),
        "warning": ("Se anticipa incrustación, combustión deficiente o inestabilidad de alimentación de agua.", "Escalar al operador autorizado para revisar tratamiento, quemador, purgas, bomba y controles."),
        "critical": ("Hay riesgo de pérdida de nivel, sobrepresión o falla grave de combustión.", "Ejecutar parada segura por operador autorizado y bloquear rearme hasta verificar nivel, quemador, válvulas y protecciones."),
    },
    "CIP-350": {
        "healthy": ("El sistema CIP mantiene secuencia y recirculación compatibles con la limpieza validada.", "Confirmar tiempo, temperatura, concentración, caudal y conductividad de retorno."),
        "warning": ("Puede existir retorno restringido, concentración baja o válvula que no completa su carrera.", "Suspender liberación sanitaria y revisar receta CIP, químicos, válvulas, bomba y retorno."),
        "critical": ("Existe riesgo de ciclo CIP ineficaz y liberación de equipo sin condición sanitaria.", "Invalidar el ciclo, bloquear liberación de línea y repetirlo solo después de corregir bomba, calentamiento, dosificación y válvulas."),
    },
    "EX-360": {
        "healthy": ("El extractor mantiene giro y flujo de aire sin desbalance apreciable.", "Limpiar filtros y comprobar correas, compuertas y fijaciones."),
        "warning": ("Se anticipa saturación de filtros, correa floja o acumulación en el impulsor.", "Programar cambio de filtros y revisar tensión de correas, limpieza y alineación del ventilador."),
        "critical": ("Hay riesgo de rotura de correa, contacto del impulsor o pérdida total de extracción.", "Aislar el extractor, controlar el área afectada y reparar impulsor, correas, rodamientos y ductos antes de operar."),
    },
}


CAUSE_TEMPLATES = {
    "vibration": "Vibración asociada a holgura, desalineación o desgaste en {component}.",
    "temperature": "Temperatura elevada por fricción, suciedad o transferencia térmica deficiente en {component}.",
    "current": "Demanda eléctrica anormal por sobrecarga, atasco o deterioro en {component}.",
    "rpm": "Desviación de velocidad por pérdida de sincronismo, deslizamiento o control inestable en {component}.",
    "pressure": "Presión fuera de régimen por restricción, fuga, cavitación o regulación deficiente en {component}.",
    "usage": "Desgaste acumulado por horas de servicio en {component}.",
}


ACTION_TEMPLATES = {
    "vibration": "Medir vibración axial/radial, revisar fijaciones, alineación, lubricación y condición de {component}.",
    "temperature": "Confirmar temperatura con instrumento verificado; limpiar y revisar lubricación, flujo y condición de {component}.",
    "current": "Medir corriente por fase, verificar carga, aislamiento, conexiones y libertad de movimiento de {component}.",
    "rpm": "Contrastar RPM con tacómetro; revisar consigna, encoder, acople y sincronización de {component}.",
    "pressure": "Verificar manómetros, válvulas, filtros, fugas y condición hidráulica/neumática de {component}.",
    "usage": "Revisar historial, holguras, lubricación y vida útil; programar recambio preventivo de {component}.",
}


def profile_for(machine):
    profile = MACHINE_PROFILES.get(machine["code"])
    if profile:
        process, vibration, temperature, current, rpm, pressure, usage = profile
    else:
        process = machine["machine_type"].lower()
        vibration, temperature, current = "conjunto rotativo", "sistema térmico", "accionamiento eléctrico"
        rpm, pressure, usage = "transmisión", "circuito de proceso", "componentes de desgaste"
    return {
        "process": process,
        "components": {
            "vibration": vibration, "temperature": temperature, "current": current,
            "rpm": rpm, "pressure": pressure, "usage": usage,
        },
    }


def diagnostic_for(machine, factors, risk, status, values=None, limits=None):
    profile = profile_for(machine)
    level = RISK_LEVELS[status]
    dominant = factors[:3]
    finding, primary_action = MACHINE_RISK_GUIDANCE.get(machine["code"], {}).get(
        status, (f"Condición {level['label'].lower()} en {profile['process']}.", level["strategy"])
    )
    causes = [f"Escenario para riesgo {risk}%: {finding}"]
    actions = [f"Acción principal: {primary_action}"]
    for position, factor in enumerate(dominant[:2], start=1):
        key = factor["key"]
        component = profile["components"][key]
        causes.append(f"{position}. {factor['label']} ({factor['contribution']} puntos): {CAUSE_TEMPLATES[key].format(component=component)}")
        actions.append(f"{level['priority']} · {ACTION_TEMPLATES[key].format(component=component)}")
    names = " y ".join(item["label"] for item in dominant[:2])
    diagnosis = f"{machine['code']} · riesgo {risk}% ({level['label'].lower()}). {finding} Variables dominantes: {names}."
    return {
        "diagnosis": diagnosis,
        "causes": causes,
        "actions": actions,
        "risk_level": level["label"],
        "strategy": primary_action,
        "source": f"MAN-EQP-{machine['code']}_mantenimiento_predictivo.md",
    }


def manual_sections(machine):
    profile = profile_for(machine)
    rows = []
    for key, label in (
        ("vibration", "Vibración"), ("temperature", "Temperatura"),
        ("current", "Corriente"), ("rpm", "RPM"),
        ("pressure", "Presión"), ("usage", "Horas de uso"),
    ):
        component = profile["components"][key]
        rows.append(
            f"### {label}\nComponente: {component}.\nCausa probable: "
            f"{CAUSE_TEMPLATES[key].format(component=component)}\nVerificación/solución: "
            f"{ACTION_TEMPLATES[key].format(component=component)}"
        )
    guidance = MACHINE_RISK_GUIDANCE.get(machine["code"], {})
    if guidance:
        ranges = []
        for status, range_label in (
            ("healthy", "Menor de 40 %"),
            ("warning", "Entre 40 % y 69.9 %"),
            ("critical", "Desde 70 %"),
        ):
            finding, action = guidance[status]
            ranges.append(f"### {range_label}\nEscenario: {finding}\nRespuesta: {action}")
        rows.append("## Escenarios propios según el riesgo de esta máquina\n" + "\n\n".join(ranges))
    return profile["process"], "\n\n".join(rows)
