import os
import pytest
from httpx import AsyncClient, ASGITransport
from tortoise import Tortoise

os.environ["DATABASE_URL"] = "sqlite://:memory:"

from app.main import app

import pytest_asyncio

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["app.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()

@pytest_asyncio.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

async def register_user(client: AsyncClient, email: str, password: str):
    await client.post("/auth/register", json={"email": email, "password": password})

async def auth_headers(client: AsyncClient, email: str) -> dict:
    password = email.split('@')[0]
    resp = await client.post("/auth/login", data={"username": email, "password": password})
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}
