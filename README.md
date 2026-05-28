# ApuestaReto

> Proyecto Django para gestionar apuestas.

## Resumen

Este repo contiene una aplicación Django llamada **ApuestaReto** con varias apps enfocadas en gestión de usuarios, cuentas, eventos y apuestas. Es una plantilla funcional lista para ejecutar localmente o con Docker.

## Apps principales

- `apuestaAPP`: lógica de apuestas y vistas relacionadas.
- `eventoAPP`: modelos y vistas de eventos.
- `cuentaAPP`: gestión de cuentas/monedero.
- `userAPP`: modelo de usuario personalizado (`AUTH_USER_MODEL = 'userAPP.User'`).
- `coreAPP`: vistas y utilidades centrales.

## Estructura importante

- Archivo principal de gestión: `manage.py`.
- Configuración: `config/settings.py`.
- Plantillas: `templates/`.
- Archivos estáticos: `static/`.
- Migrations: en cada app dentro de `*/migrations/`.
- Docker: `Dockerfile` y `docker-compose.yml` disponibles.

## Dependencias

Las dependencias principales (según `requirements.txt`) incluyen:

- Django ~6.0
- psycopg2-binary (Postgres)
- python-decouple (manejo de variables de entorno)
- tzdata, sqlparse, asgiref, etc.

Instálalas con:

```bash
python -m venv .venv
source .venv/bin/activate   # Unix/macOS
.venv\Scripts\activate     # Windows PowerShell
pip install -r requirements.txt
```

## Variables de entorno (relevantes)

La configuración usa `python-decouple`. Asegúrate de definir al menos:

- `SECRET_KEY` — clave secreta de Django.
- `DEBUG` — `True` o `False`.
- `DB_ENGINE` — motor de base de datos (ej. `django.db.backends.postgresql`).
- `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — conexión a la DB.
- `ALLOWED_HOSTS` — hosts permitidos (coma-separados).

Por defecto `config/settings.py` espera un servicio de base de datos en `HOST=db` y `PORT=5432`.

## Ejecutar localmente (sin Docker)

1. Configura y activa entorno virtual.
2. Instala dependencias: `pip install -r requirements.txt`.
3. Crea archivo `.env` con las variables requeridas (ver sección anterior).
4. Ejecuta migraciones:

```bash
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre `http://127.0.0.1:8000/`.

## Ejecutar con Docker

Si quieres usar Docker, hay configuración presente:

```bash
docker compose up --build
```

Esto levantará los servicios definidos en `docker-compose.yml` (posible servicio de Postgres bajo el nombre `db`).

## Tests

Ejecuta la suite de tests con:

```bash
python manage.py test
```

## Rutas y vistas

Las rutas principales están definidas en `config/urls.py` y cada app puede registrar sus propias URLs en `*/urls.py`. Revisa las vistas en:

- `apuestaAPP/views.py`
- `eventoAPP/views.py`
- `cuentaAPP/views.py`
- `userAPP/views.py`

## Notas de desarrollo

- `AUTH_USER_MODEL` está personalizado en `userAPP`.
- Archivos estáticos se sirven desde `static/` y se recolectan en `staticfiles` cuando se ejecuta `collectstatic`.
- La configuración usa `python-decouple` para leer valores sensibles desde el entorno.

## Contribuir

1. Haz fork y branch con cambios claros.
2. Asegura que las migraciones necesarias estén incluidas.
3. Añade tests y documentación mínima para nuevas funciones.

---

reto apuesta
