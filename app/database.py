import os
# pyrefly: ignore [missing-import]
from tortoise import Tortoise

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite://db.sqlite3")

TORTOISE_ORM = {
    "connections": {"default": DATABASE_URL},
    "apps": {
        "models": {
            "models": ["app.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}

async def init_db():
    await Tortoise.init(config=TORTOISE_ORM)
    # Generate schemas automatically for quick setup without aerich
    await Tortoise.generate_schemas()

async def close_db():
    await Tortoise.close_connections()
