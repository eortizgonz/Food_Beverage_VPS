from flask import Flask, render_template, jsonify, request
import csv, json, random, time
from pathlib import Path
app = Flask(__name__)
BASE = Path(__file__).parent

def load_questions():
    with open(BASE/'data/questions.csv', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def load_kpis():
    with open(BASE/'data/kpis.json', encoding='utf-8') as f:
        data=json.load(f)
    # small movement
    for group in data.values():
        for k,v in list(group.items()):
            if isinstance(v,(int,float)):
                delta = random.uniform(-1.5,1.8)
                group[k] = round(max(0, v + delta),2)
    return data

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/kpis')
def kpis(): return jsonify(load_kpis())

@app.route('/api/questions')
def questions():
    area=request.args.get('area')
    rows=load_questions()
    if area and area!='Todos': rows=[r for r in rows if r['area']==area]
    return jsonify(rows)

@app.route('/api/answer', methods=['POST'])
def answer():
    q=request.json.get('question','').strip().lower()
    for r in load_questions():
        if r['question'].strip().lower()==q or q in r['question'].lower():
            return jsonify(r)
    return jsonify({"area":"General","question":q,"answer":"La app no encontró coincidencia exacta, pero puede simular análisis de producción, OEE, calidad, inventario, finanzas y servicio al cliente.","action":"Selecciona una pregunta dinámica o ejecuta un simulador.","value":"Exploración flexible del copiloto.","source":"Motor IA simulado"})

@app.route('/api/button-execute/<button_id>')
def button_execute(button_id):
    questions=load_questions()
    mapping={
      'sap':'SAP ERP simulado: datos maestros, órdenes, clientes, inventario y finanzas sincronizados.',
      'mii':'SAP MII simulado: captura de señales de planta, producción por línea, OEE, scrap y paradas.',
      'me':'SAP ME simulado: ejecución de órdenes, trazabilidad, lotes, calidad y genealogía.',
      'cap':'SAP CAP simulado: lógica de negocio, APIs, preguntas, reglas y servicios OData.',
      'btp':'SAP BTP simulado: integración, workflow, alertas, aprobaciones y automatización.',
      'operacional':'Dashboard operacional ejecutado con producción, OEE, turnos, órdenes y cuellos de botella.',
      'financiero':'Dashboard financiero ejecutado con margen, costo, inventario, scrap, forecast y ROI.',
      'ejecutivo':'Dashboard ejecutivo ejecutado con plan vs real, OTIF, riesgos, margen y decisiones críticas.',
      'comercial':'Dashboard comercial ejecutado con pedidos, clientes, OTIF, stock y compromisos.',
      'calidad':'Calidad ejecutada con lotes, no conformidades, especificaciones y acciones correctivas.'
    }
    related=[q for q in questions if button_id.lower() in q['area'].lower() or button_id.lower() in q['source'].lower()]
    if not related: related=random.sample(questions, min(3,len(questions)))
    return jsonify({
      'button': button_id.upper(), 'status':'Ejecutado', 'progress':100,
      'message': mapping.get(button_id,'Simulación ejecutada con datos en movimiento.'),
      'kpis': load_kpis(), 'related_questions': related[:5], 'timestamp': time.strftime('%H:%M:%S')
    })

@app.route('/api/run-all-buttons')
def run_all():
    return jsonify([button_execute.__wrapped__(b) if False else {'button':b,'status':'ready'} for b in ['sap','mii','me','cap','btp','operacional','financiero','ejecutivo','comercial','calidad']])

@app.route('/XMII/Illuminator')
def mii(): return jsonify({'simulator':'SAP MII','status':'active','query':request.args.get('QueryTemplate'),'data':load_kpis()['operational']})
@app.route('/ME/api/production-orders')
def me_orders(): return jsonify({'simulator':'SAP ME','orders':[{'id':'FB-450021','line':'Linea 3','status':'Atrasada','progress':63},{'id':'FB-450022','line':'Linea 1','status':'En curso','progress':91}]})
@app.route('/cap/odata/v4/foodbeverage/$metadata')
def cap_meta(): return jsonify({'simulator':'SAP CAP','entities':['ProductionOrder','QualityEvent','Inventory','CustomerOrder','FinancialImpact']})
@app.route('/btp/destination/status')
def btp_status(): return jsonify({'simulator':'SAP BTP','destination':'active','workflow':'active','alerts':14})
@app.route('/btp/workflow/tasks')
def btp_tasks(): return jsonify({'tasks':[{'task':'Reasignar producción Línea 3','owner':'Supervisor','due':'Hoy 18:00','status':'En curso'}]})
@app.route('/health')
def health(): return 'ok'

if __name__ == '__main__': app.run(host='0.0.0.0', port=5000, debug=True)
