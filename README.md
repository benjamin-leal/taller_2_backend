# CRUD Students & Pets (FastAPI)

Proyecto FastAPI que implementa un **CRUD** para la entidad `Student` y sus `Pet`, con **persistencia en PostgreSQL mediante SQLAlchemy**. Las migraciones se gestionan con Alembic y los datos se conservan en un volumen de Docker.

## Tecnologías

- Python 3.13
- FastAPI + SQLAlchemy
- PostgreSQL 17, Alembic y psycopg
- Docker Compose y Adminer
- HTML + JS + Tailwind CSS (frontend estático)

## Resumen funcional

La API expone operaciones CRUD completas sobre estudiantes y mascotas:

**Estudiantes** — `/api/students`

- **Crear**: `POST /api/students` (opcionalmente con `pets[]` para crear el estudiante y sus mascotas en una sola petición)
- **Listar**: `GET /api/students`
- **Buscar por id**: `GET /api/students/:id`
- **Actualizar**: `PATCH /api/students/:id`
- **Eliminar**: `DELETE /api/students/:id` (elimina también sus mascotas)

**Mascotas** — `/api/students/:studentId/pets`

- **Listar**: `GET /api/students/:studentId/pets`
- **Crear**: `POST /api/students/:studentId/pets`
- **Actualizar**: `PATCH /api/students/:studentId/pets/:petId`
- **Eliminar**: `DELETE /api/students/:studentId/pets/:petId`

### Alta de estudiante con mascotas

`POST /api/students` acepta un arreglo opcional `pets`:

```json
{
	"name": "Ana Pérez",
	"username": "ana_perez",
	"email": "ana@example.com",
	"age": 21,
	"pets": [
		{ "name": "Firulais", "species": "perro", "age": 3 },
		{ "name": "Michi", "species": "gato" }
	]
}
```

Si no se envía `pets` (o se envía vacío), el comportamiento es exactamente el mismo de antes.

> **Transacción:** el estudiante y sus mascotas se guardan en una sola transacción. Si una mascota viola una restricción, se ejecuta rollback y no queda guardado ningún registro de esa petición. Los errores de unicidad se devuelven como HTTP 409 con el campo `errors`. El borrado de un estudiante elimina sus mascotas en cascada.

### Modelo de datos

| Estudiante | Mascota        |
| ---------- | -------------- |
| id (UUID)  | id (UUID)      |
| name       | studentId      |
| username   | name           |
| email      | species        |
| age        | age (opcional) |
| createdAt  | createdAt      |
| updatedAt  | updatedAt      |

### Validación y unicidad

La validación se realiza con Pydantic v2:

- `name` (estudiante): texto de 3 a 100 caracteres, sin etiquetas HTML.
- `username`: texto de 3 a 30 caracteres, solo minúsculas, números y guiones bajos (`^[a-z0-9_]+$`).
- `email`: dirección de correo electrónico válida.
- `age` (estudiante): entero entre 18 y 99.
- `name` / `species` (mascota): texto de 1 a 50 caracteres, sin etiquetas HTML.
- `age` (mascota): entero entre 0 y 100 (opcional).

Unicidad (rechazado con `409 Conflict`):

- Estudiante: `email` y `username` deben ser únicos.
- Mascota: `name` debe ser único dentro de un mismo estudiante.

## Estándar de respuesta JSON

Toda respuesta de la API — exitosa o de error — usa el mismo **envelope** `ApiResponse`, definido en [`app/shared/api_response.py`](app/shared/api_response.py). Esto permite que el frontend interprete cualquier respuesta de forma uniforme.

### Envelope común

| Campo       | Tipo                | Descripción                                                               |
| ----------- | ------------------- | ------------------------------------------------------------------------- |
| `code`      | `number`            | Código de estado HTTP (coincide con el status de la respuesta).           |
| `success`   | `boolean`           | `true` si la operación se completó, `false` si hubo error.                |
| `message`   | `string`            | Resumen legible del resultado (varía según el método HTTP).               |
| `timestamp` | `string`            | Fecha/hora en ISO 8601 de la respuesta.                                   |
| `data`      | `object \| null`    | Datos de la operación. Presente en éxito; `null` en errores.              |
| `error`     | `string` (opcional) | Mensaje de error para errores simples (404, 500).                         |
| `errors`    | `object` (opcional) | Errores por campo para validación (400) y conflicto (409). Ver más abajo. |

### Respuestas de éxito

Un middleware global ([`api_response.py`](app/shared/api_response.py)) envuelve el retorno de los controladores en `data`:

- **Recurso único** (`GET :id`, `POST`, `PATCH`, `DELETE`): `data` contiene la entidad directamente.
- **Listado** (`GET` colección): `data` contiene `{ total, items }`.

```json
{
  "code": 201,
  "success": true,
  "message": "Recurso creado",
  "timestamp": "2026-09-09T16:49:33.368Z",
  "data": {
    "id": "c3600646-abe8-4be3-8096-d6ad629388e2",
    "name": "Juan Pérez",
    "username": "juanperez",
    "email": "juan@example.com",
    "age": 20,
    "createdAt": "2026-09-09T16:49:33.000Z",
    "updatedAt": "2026-09-09T16:49:33.000Z"
  }
}
```

`message` según el método HTTP:

| Método   | `message`             | `code` |
| -------- | --------------------- | ------ |
| `GET`    | `Operación exitosa`   | 200    |
| `POST`   | `Recurso creado`      | 201    |
| `PATCH`  | `Recurso actualizado` | 200    |
| `DELETE` | `Recurso eliminado`   | 200    |

### Errores simples (404, 500)

Los errores sin detalle por campo usan el campo `error`:

```json
{
  "code": 404,
  "success": false,
  "message": "Estudiante no encontrado",
  "timestamp": "2026-09-09T16:49:53.816Z",
  "data": null,
  "error": "Estudiante no encontrado"
}
```

### Validación (400) y conflicto (409)

Ambos casos comparten el **mismo esquema** para que el frontend los trate igual: el campo `errors` es un mapa `{ campo: { message } }`, donde la clave es el nombre del campo que falla.

```json
{
  "code": 400,
  "success": false,
  "message": "Error de validación",
  "timestamp": "2026-09-09T16:39:30.397Z",
  "data": null,
  "errors": {
    "name": { "message": "El nombre debe tener entre 3 y 100 caracteres" },
    "email": { "message": "El correo electrónico no es válido" }
  }
}
```

```json
{
  "code": 409,
  "success": false,
  "message": "Conflicto con datos existentes",
  "timestamp": "2026-09-09T16:49:45.110Z",
  "data": null,
  "errors": {
    "email": { "message": "El correo electrónico ya está en uso" }
  }
}
```

- `400 Bad Request`: cuando falla la validación. Los DTOs replican las reglas y mensajes de class-validator (NestJS) en español; el handler global ([`exceptions.py`](app/shared/exceptions.py)) convierte los errores al mapa `{ campo: { message } }` (si un campo falla varias reglas, los mensajes se concatenan con `", "`; las propiedades no permitidas devuelven `errors: {}`).
- `409 Conflict`: cuando se viola una restricción de unicidad. Los servicios lanzan una `HTTPException` con el mismo mapa `errors`, por lo que es indistinguible de una validación a nivel de estructura.

### Interpretación en el frontend

El cliente estático (`public/`) consume este estándar de forma uniforme:

- `public/js/api.js` expone `api()` (hace `fetch` y devuelve `data` en éxito o lanza el envelope en error) y `normalizeErrors()` (convierte `{ campo: { message } }` en `{ campo: message }`).
- En los formularios, si la respuesta trae `errors`, cada mensaje se muestra bajo su input correspondiente; si trae `error`, se muestra como notificación global (toast).

## Contexto técnico

- **Backend**: FastAPI
- **Persistencia**: PostgreSQL con repositorios SQLAlchemy y migraciones Alembic
- **Validación**: Pydantic v2
- **Frontend**: archivos estáticos en `public/` (Alpine.js + Tailwind CSS + vanilla-sonner, vía CDN)
- **Gestor de dependencias**: uv
- **Documentación**: Swagger en `/docs`

## Ejecución local (API fuera de Docker)

Para ejecutar todos los servicios en contenedores, usa la sección siguiente
«Ejecución con Docker». Para desarrollar la API en el equipo:

1. Prepara `.env` desde `.env.example` como se explica abajo y arranca solo la BD:

   ```bash
   docker compose up -d db --wait
   uv sync --frozen
   ```

2. Exporta una URL con tus credenciales reales y el puerto publicado de PostgreSQL.
   Desde el equipo el servidor es `localhost`; dentro de Docker es `db`.
   Sustituye `usuario`, `clave` y `base` en este ejemplo (codifica la contraseña
   para URL si contiene caracteres especiales):

   ```bash
   export DATABASE_URL='postgresql+psycopg://usuario:clave@localhost:5432/base'
   uv run alembic upgrade head
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
   ```

La aplicación queda en http://localhost:3000 y Swagger en
http://localhost:3000/docs. Reiniciar la API no borra los datos de PostgreSQL.

## Comandos útiles

- `make install` — sincroniza dependencias con uv
- `make dev` — arranca uvicorn en modo reload
- `make lint` — ejecuta Ruff (con autocorrección)
- `make format` — formatea el código con Ruff
- `make format-check` — verifica el formato
- `make clean` — elimina `.venv`, cachés y artefactos

## Ejecución con Docker

Requisitos: Docker Desktop abierto.

1. Crea la configuración local si todavía no tienes `.env`:

   ```bash
   cp .env.example .env
   ```

   Si ya existe, consérvalo. Configura `POSTGRES_DB`, `POSTGRES_USER`,
   `POSTGRES_PASSWORD` y `DATABASE_URL`. Dentro de Docker, la URL debe usar
   `postgresql+psycopg://`, el servidor `db` y el puerto `5432`.
   El ejemplo interpola las variables con Docker Compose. Si la contraseña
   contiene caracteres especiales como `@`, `:` o `/`, escribe la URL completa
   con la contraseña codificada para URL. No subas `.env` al repositorio.
   `POSTGRES_PORT`, `ADMINER_PORT` y `API_PORT` cambian los puertos del equipo;
   si los modificas, ajusta también las direcciones que abres en el navegador.

2. Valida la configuración:

   ```bash
   docker compose config --quiet
   ```

3. Construye e inicia los servicios:

   ```bash
   docker compose up -d --build --wait
   ```

4. Comprueba su estado:

   ```bash
   docker compose ps
   ```

### Acceso a los servicios

- API y frontend: http://localhost:3000
- Documentación Swagger: http://localhost:3000/docs
- Estado de la conexión a la base de datos: http://localhost:3000/api/health
- Adminer: http://localhost:8080

En Adminer, selecciona PostgreSQL como sistema y utiliza `db` como servidor. Introduce el usuario, contraseña y base de datos definidos en `.env`.

### Persistencia y detención

Los datos de PostgreSQL se guardan en el volumen `postgres_data`.

Para detener los servicios sin borrar los datos:

```bash
docker compose down
```

**Precaución:** `docker compose down -v` elimina también el volumen de datos.

### Evidencia de rollback

Verificado el **28 de octubre de 2026** sobre `main`, commit `e69ce87`,
con Docker y una base PostgreSQL temporal inicialmente vacía. La API aplicó
la migración `dbc21c130308` al arrancar. No se usaron datos de trabajo.

Se envió `POST /api/students` con dos mascotas del mismo nombre:

```json
{
  "name": "Prueba Rollback",
  "username": "rollback_final",
  "email": "rollback@example.com",
  "age": 22,
  "pets": [
    {"name": "Luna", "species": "gato"},
    {"name": "Luna", "species": "perro"}
  ]
}
```

Respuesta real: **HTTP 409**.

```json
{
  "code": 409,
  "success": false,
  "message": "Conflicto con datos existentes",
  "timestamp": "2026-10-28T23:08:46.200Z",
  "data": null,
  "errors": {
    "name": {"message": "Ya tienes una mascota con ese nombre"}
  }
}
```

Después se consultaron ambas tablas directamente en PostgreSQL:

```sql
SELECT (SELECT count(*) FROM students) AS students,
       (SELECT count(*) FROM pets) AS pets;
```

Resultado real en esa base vacía de pruebas:

```text
 students | pets
----------+------
        0 |    0
(1 row)
```

La restricción de nombre repetido provoca el rollback de toda la petición:
no se conserva ni el estudiante ni la primera mascota. Para repetirlo,
usa una base exclusiva de pruebas y envía el JSON desde Swagger. En Adminer
puedes ejecutar la consulta anterior; los ceros solo se esperan si la base
estaba vacía antes de la prueba.

### Pruebas automatizadas

Las pruebas requieren una base **desechable** cuyo nombre empiece por
`taller_test_`. Vacían las tablas Student y Pet de esa base entre casos;
no apuntes la URL a una base de trabajo. Con PostgreSQL iniciado, crea una
base separada (ejecutar una sola vez):

```bash
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" taller_test_api'
uv sync --frozen
```

Configura las credenciales reales del mismo servidor y su puerto publicado:

```bash
export TEST_DATABASE_URL='postgresql+psycopg://usuario:clave@localhost:5432/taller_test_api'
DATABASE_URL="$TEST_DATABASE_URL" uv run pytest -q
```

Las pruebas aplican Alembic a la base de pruebas. Resultado comprobado en
`e69ce87`: **20 passed**. Incluyen CRUD de Student y Pet, propiedad de las
mascotas, unicidad, rollback, cascada, validación y conexión a la BD.
Se observó un aviso de compatibilidad futura de AnyIO con pytest 10,
sin fallos de pruebas.

También se verificó el arranque con `docker compose up -d --build --wait`,
HTTP 200 en `/api/health`, `/api/students` y `/docs`, y `alembic check` sin
cambios pendientes. Al detener la BD temporal, `/api/health` devolvió 503.
