# Despliegue en VPS Ubuntu con Docker

## 1. Descargar el proyecto

```bash
git clone URL_DEL_NUEVO_REPOSITORIO food-beverage-copilot
cd food-beverage-copilot
```

## 2. Crear la configuración privada

```bash
cp .env.vps.example .env
nano .env
```

Generar `SECRET_KEY`:

```bash
openssl rand -hex 32
```

Usar una contraseña larga y diferente para `DB_PASSWORD`. No publicar `.env`.

Si todavía no hay dominio con HTTPS, configurar temporalmente:

```env
APP_BASE_URL=http://IP_DEL_VPS:5000
SESSION_COOKIE_SECURE=0
```

Con HTTPS, utilizar el dominio y mantener `SESSION_COOKIE_SECURE=1`.

## 3. Construir y arrancar

```bash
docker compose pull
docker compose build
docker compose up -d
```

El servicio `migrate` crea las tablas y carga los datos maestros antes de iniciar la aplicación.

## 4. Validar

```bash
docker compose ps
docker compose logs migrate
docker compose logs --tail=100 app
curl http://127.0.0.1:5000/health
```

Abrir `http://IP_DEL_VPS:5000`. En producción se recomienda colocar Nginx o Caddy delante del puerto 5000 y habilitar HTTPS.

## Actualizaciones

```bash
git pull origin main
docker compose build
docker compose up -d
docker image prune -f
```

## Copia de seguridad

```bash
mkdir -p backup
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backup/food_beverage_$(date +%F_%H%M).dump"
```

## Restauración

La restauración reemplaza datos y debe ejecutarse únicamente con una copia verificada:

```bash
cat backup/ARCHIVO.dump | docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists'
```

## Operación

```bash
docker compose logs -f app
docker compose restart app
docker compose stop
docker compose up -d
```

No ejecutar `docker compose down -v` salvo que se quiera eliminar definitivamente el volumen de PostgreSQL.
