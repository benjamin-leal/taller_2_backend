# CRUD Students & Pets (FastAPI)

Proyecto FastAPI que implementa un **CRUD** para la entidad `Student` y sus `Pet`, con **almacenamiento en memoria** a través de repositorios respaldados por diccionarios. Los datos viven mientras el proceso esté corriendo.

## Tecnologías

- Python 3.13
- FastAPI + repositorios en memoria
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

> **Punto de transacción:** este endpoint realiza varias escrituras (el estudiante y cada mascota). Con un ORM/SQL, todas deben ejecutarse dentro de una transacción: si una mascota falla (por ejemplo, por nombre duplicado), el estudiante y las mascotas anteriores no deben quedar guardados. En esta versión en memoria la implementación es secuencial y **no** hace rollback, a propósito, para que la actividad de ORM/transacciones parta de ese problema.

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
- **Persistencia**: en memoria (repositorios respaldados por diccionarios); los datos se pierden al reiniciar
- **Validación**: Pydantic v2
- **Frontend**: archivos estáticos en `public/` (Alpine.js + Tailwind CSS + vanilla-sonner, vía CDN)
- **Gestor de dependencias**: uv
- **Documentación**: Swagger en `/docs`

## Ejecución local

### Taller II: PostgreSQL y Adminer con Docker (parte 1)

Esta parte prepara la infraestructura de base de datos. **El CRUD todavía
guarda los datos en memoria**. La parte 2, descrita abajo, incorpora la conexión
con SQLAlchemy y la migración inicial; reemplazar los repositorios y aplicar
las transacciones de los endpoints queda para la siguiente entrega.

No hace falta instalar PostgreSQL ni Adminer directamente en el equipo.
Instala [Docker Desktop](https://docs.docker.com/desktop/setup/install/mac-install/)
(en este Mac, la versión para Apple silicon), ábrelo y espera a que el motor
esté listo. Docker Desktop incluye Docker Compose.

Desde la carpeta del proyecto:

```bash
docker --version
docker compose version
cp .env.example .env
```

Copia el archivo solo si todavía no tienes `.env`. Edita `POSTGRES_PASSWORD`
para elegir tu contraseña local. No subas `.env` al repositorio; ya está
incluido en `.gitignore`. Las variables se leen automáticamente desde ese
archivo al ejecutar Compose. Si un puerto está ocupado, cambia
`POSTGRES_PORT` o `ADMINER_PORT` en `.env`.

```bash
docker compose config --quiet
docker compose up -d --wait
docker compose ps
```

El servicio `db` debe aparecer saludable (`healthy`) y `adminer` en ejecución.
Compose espera a que PostgreSQL esté listo antes de iniciar Adminer.

Abre <http://localhost:8080> (o el puerto elegido en `ADMINER_PORT`) y entra con:

| Campo de Adminer | Valor |
| --- | --- |
| Sistema | PostgreSQL |
| Servidor | `db` |
| Usuario | El valor de `POSTGRES_USER` |
| Contraseña | El valor de `POSTGRES_PASSWORD` |
| Base de datos | El valor de `POSTGRES_DB` |

Los contenedores comparten la red `backend`: Adminer encuentra PostgreSQL
con el nombre `db` y su puerto interno `5432`. Una API ejecutada directamente
en el equipo usará `localhost` y `POSTGRES_PORT` cuando implementemos la
conexión. Los puertos publicados solo aceptan conexiones desde este equipo.

#### Comprobar que los datos persisten

En la opción **Comando SQL** de Adminer, ejecuta:

```sql
CREATE TABLE prueba_persistencia (id integer PRIMARY KEY, mensaje text NOT NULL);
INSERT INTO prueba_persistencia VALUES (1, 'Los datos persisten');
```

Luego, en la terminal:

```bash
docker compose down
docker compose up -d --wait
```

Vuelve a entrar a Adminer y ejecuta:

```sql
SELECT * FROM prueba_persistencia;
DROP TABLE prueba_persistencia;
```

El `SELECT` debe mostrar la fila creada; el `DROP` limpia solo esta tabla de
prueba. Los datos de PostgreSQL se guardan en el volumen `postgres_data`.
`docker compose down` conserva ese volumen; **añadir `-v` borra sus datos**.
Las credenciales iniciales se aplican cuando el volumen está vacío: editar
`.env` después no cambia automáticamente la contraseña de una base existente.

Para revisar problemas de arranque:

```bash
docker compose logs db adminer
```

Referencias: [imagen oficial PostgreSQL](https://hub.docker.com/_/postgres) e
[imagen oficial Adminer](https://hub.docker.com/_/adminer).

### Taller II: conexión y migraciones (parte 2)

Se agregaron SQLAlchemy (ORM), psycopg (conector PostgreSQL), Alembic
(migraciones) y pydantic-settings (configuración desde `.env`).
La estructura sigue la [guía de SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
y el [tutorial de Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

Con Docker abierto y desde la carpeta del proyecto:

```bash
uv sync
docker compose up -d --wait
uv run alembic upgrade head
uv run alembic current
uv run alembic check
```

`upgrade head` crea las tablas `students` y `pets` y registra la revisión en
`alembic_version`. Ejecutarlo nuevamente no recrea las tablas ni borra datos.
`check` confirma que los modelos coinciden con las migraciones aplicadas.
Las tablas no se crean automáticamente al iniciar FastAPI: se administran
mediante las migraciones guardadas en `alembic/versions/`.

- `app/database.py`: lee las credenciales de `.env` y proporciona una sesión
  por petición. `POSTGRES_HOST` es `localhost` por defecto; si más adelante
  la API corre en la misma red de Docker, deberá ser `db`.
- `app/models.py`: define estudiantes y mascotas, UUID, fechas con zona horaria,
  edades válidas, email y username únicos y nombre de mascota único por dueño.
  La relación impide mascotas sin estudiante y elimina sus mascotas en cascada.
- `GET /api/health/database`: ejecuta una consulta real; devuelve `200` con
  `data: {"database": "ok"}` o `503` si la base no está disponible.

Después de iniciar FastAPI puedes comprobar la conexión en
<http://localhost:3000/api/health/database> y ver las tablas desde Adminer.
**Esta comprobación no significa que el CRUD ya use PostgreSQL**: en esta
entrega los endpoints de estudiantes y mascotas siguen usando sus repositorios
en memoria. La sustitución y sus transacciones se harán en la parte 3.

#### Pruebas

```bash
uv run python -m pytest -q
```

Sin una base de pruebas, solo se ejecutan las pruebas independientes y se
omiten las de integración. Para ejecutarlas todas, crea una base dedicada
(solo la primera vez), usando las credenciales de tu contenedor:

```bash
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" taller_test_local'
TEST_POSTGRES_DB=taller_test_local uv run python -m pytest -q
```

Las pruebas aplican las migraciones en esa base, comprueban las restricciones
y revierten los registros de prueba. Solo aceptan nombres que empiecen por
`taller_test_`. No uses una base con información que quieras conservar.
Se prueba el rollback al insertar mascotas duplicadas mediante el ORM; el
rollback de los endpoints se incorporará cuando migremos el CRUD.

### Ejecutar FastAPI

1. Instalar dependencias:

    ```bash
    make install
    ```

    O directamente con uv:

    ```bash
    uv sync
    ```

2. Levantar el servidor en modo desarrollo:

    ```bash
    make dev
    ```

    O usando uv:

    ```bash
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 3000
    ```

La aplicación queda disponible en:

- `http://localhost:3000`
- `http://localhost:3000/docs`

> Al ser un almacenamiento en memoria, los datos se pierden cada vez que se reinicia el servidor (incluido el reload de desarrollo).

## Comandos útiles

- `make install` — sincroniza dependencias con uv
- `make dev` — arranca uvicorn en modo reload
- `make lint` — ejecuta Ruff (con autocorrección)
- `make format` — formatea el código con Ruff
- `make format-check` — verifica el formato
- `make clean` — elimina `.venv`, cachés y artefactos
