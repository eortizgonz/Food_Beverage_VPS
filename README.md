# Copiloto de Producción para Alimentos y Bebidas

MVP orientado al supervisor de piso de una planta de alimentos. Presenta el contexto del turno, plan contra producción real, OEE, velocidad, paradas, controles de calidad e inocuidad, alertas, acciones y entrega de turno.

Los datos actuales son demostrativos y ninguna acción modifica equipos ni sistemas SAP.

## Ejecutar localmente

```bash
pip install -r requirements.txt
python app.py
```

Abrir `http://127.0.0.1:5000`.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

## PostgreSQL

La aplicación carga la configuración desde `.env` y almacena contraseñas únicamente como hashes. Edita `.env`, reemplaza `CHANGE_ME` en `DB_PASSWORD` y ejecuta:

```powershell
python scripts/init_database.py
python app.py
```

El esquema reproducible se encuentra en `sql/001_users.sql`. El archivo `.env` está excluido de Git; `.env.example` nunca debe contener credenciales reales. En despliegues administrados, `DATABASE_URL` tiene prioridad sobre las variables locales.

### Recuperación por Gmail

Configura `MAIL_USERNAME` y `MAIL_APP_PASSWORD` en `.env`. Se utiliza Gmail SMTP con contraseña de aplicación; nunca se almacena la contraseña del correo en la base de datos. Los enlaces de recuperación vencen en 30 minutos, son de un solo uso y sus tokens se almacenan como hash.

## Endpoints principales

- `GET /api/floor`: fotografía operativa de la línea.
- `GET /api/predictive`: análisis ponderado de 20 máquinas simuladas.
- `GET /api/predictive/<machine_id>`: diagnóstico individual y factores de riesgo.
- `GET /api/questions`: preguntas sugeridas del copiloto.
- `POST /api/answer`: respuesta basada en reglas y fuentes declaradas.
- `GET /api/shift-handover`: resumen de entrega de turno.
- `GET /api/users`: usuarios sin hashes de contraseña.
- `POST /api/users`: creación segura de usuarios.
- `GET /health`: comprobación del servicio.

## Siguiente etapa

Sustituir `data/production_floor.json` por datos de historiador, PLC/MES o SAP y agregar autenticación, persistencia de eventos, catálogo de causas, auditoría y flujos de aprobación.
