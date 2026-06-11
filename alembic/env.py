import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import create_engine, pool

from app.db.base import Base
from app.db.models import Task

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Читаем переменные напрямую из окружения.
# Внутри Docker это будут значения из docker-compose.yml (POSTGRES_HOST=db)
# Локально это будут значения из .env (POSTGRES_HOST=localhost)
# Это полностью обходит баги парсинга .env файлов на Windows (ошибка 0xc2)
db_user = os.getenv("POSTGRES_USER", "postgres")
db_pass = os.getenv("POSTGRES_PASSWORD", "password")
db_host = os.getenv("POSTGRES_HOST", "db")  # 'db' по умолчанию для Docker
db_port = os.getenv("POSTGRES_PORT", "5432")
db_name = os.getenv("POSTGRES_DB", "task_service")

sync_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
config.set_main_option("sqlalchemy.url", sync_url)

def run_migrations_offline() -> None:
    context.configure(
        url=sync_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = create_engine(sync_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()