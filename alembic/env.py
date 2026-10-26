from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.database import DatabaseSettings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(
        url=DatabaseSettings().url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    connection = config.attributes.get("connection")
    if connection is not None:
        # Permite migrar la base aislada de las pruebas sin cambiar .env.
        run_migrations(connection)
    else:
        engine = create_engine(DatabaseSettings().url, poolclass=pool.NullPool)
        try:
            with engine.connect() as connection:
                run_migrations(connection)
        finally:
            engine.dispose()
