# 🛠️ Mini Issue Tracker API

A production-ready REST API for lightweight issue tracking and project management. Built using modern asynchronous Python, FastAPI, and Tortoise ORM.

This repository implements secure user authentication, project membership controls, soft-deletes, multi-parameter issue filtering/sorting, rate limiting, and an automated audit trail for issue activity.

---

## 🏗️ Project Architecture & Directory Layout

The project follows a modular, scalable directory structure separating database models, API routing, data schemas, and integration tests:

```text
issue-tracker/
├── app/
│   ├── core/
│   │   └── dependencies.py   # JWT auth, project member guard, secret key config
│   ├── models/
│   │   ├── __init__.py       # Model exporter for ORM initialization
│   │   ├── issue.py          # Tortoise ORM models (Issue, IssueActivity)
│   │   ├── project.py        # Tortoise ORM model (Project)
│   │   └── user.py           # Tortoise ORM model (User)
│   ├── routers/
│   │   ├── auth.py           # Endpoints for Registration & Login (Rate-limited)
│   │   ├── issues.py         # Endpoints for Issue CRUD, filtering, & logs
│   │   ├── projects.py       # Endpoints for Project & Membership management
│   │   └── users.py          # Endpoints for Current User Profile
│   ├── schemas/
│   │   ├── common.py         # Generic Paginated Response Schema
│   │   ├── issue.py          # Pydantic Schemas for Issue input/output validation
│   │   └── user.py           # Pydantic Schemas for User responses
│   ├── database.py           # Database connection & Tortoise configuration
│   └── main.py               # FastAPI entry point, lifespan, & global exception handler
├── tests/
│   ├── conftest.py           # Database fixtures, app client, & helper functions
│   └── test_issues.py        # Integration test suite (pytest + HTTPX client)
├── requirements.txt          # Python package dependencies
└── README.md                 # Project documentation
```

---

## ⚡ Tech Stack & Core Libraries

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Asynchronous endpoints, automatic Swagger UI docs)
- **Database ORM**: [Tortoise ORM](https://tortoise.github.io/) (Async, inspired by Django ORM)
- **Validation**: [Pydantic v2](https://docs.pydantic.dev/) (Data serialization & strict type-checking)
- **Security**: [Jose (JWT)](https://python-jose.readthedocs.io/) & [Bcrypt](https://github.com/pyca/bcrypt/) (Secure password hashing and token generation)
- **Rate Limiting**: [SlowAPI](https://slowapi.readthedocs.io/) (Token-bucket rate limiter for auth endpoints)
- **Testing**: [pytest](https://docs.pytest.org/) & [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio) (Asynchronous integration tests)

---

## 🚀 Local Development Setup

Follow these steps to set up and run the project locally on your machine:

### 1. Create and Activate a Virtual Environment
```bash
# Create a virtual environment
python3 -m venv .venv

# Activate the environment
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables (`.env`)
Create a `.env` file in the root directory:
```env
DATABASE_URL=postgres://postgres:postgres@localhost:5432/issue_tracker
SECRET_KEY=a_very_secure_random_hex_string_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```
*Note: PostgreSQL is the default database. Ensure you have a running PostgreSQL instance and that the database `issue_tracker` has been created before starting the application.*

### 4. Run the Server
```bash
uvicorn app.main:app --reload
```
Once started, the API is running locally:
- **Server URL**: `http://127.0.0.1:8000`
- **Interactive Documentation (Swagger)**: `http://127.0.0.1:8000/docs`

---

## 🧪 Running the Test Suite

The project includes integration tests that mock the database using an isolated, fast **in-memory SQLite** environment. Running tests will not modify your local database.

```bash
# Run pytest with verbose details
PYTHONPATH=. pytest -v
```

All integration tests are structured inside `tests/test_issues.py` using `httpx.AsyncClient`.

---

## ⚙️ Key Architectural & Design Decisions

### 1. Secure Authentication Flow
Authentication is managed via JSON Web Tokens (JWT) using the `OAuth2PasswordBearer` pattern. 
- **Registration**: User passwords are encrypted with a secure salt using `bcrypt` and saved in the database.
- **Login**: Token generation validates the credentials and returns a signed JWT.
- **Access Guard**: Custom FastAPI dependencies check the authorization header, decode the token, fetch the database user object, and verify membership permission levels before executing endpoint logic.

### 2. Soft Delete pattern
When a `DELETE /projects/{id}/issues/{issue_id}` request is made, the issue is not physically removed from the database. Instead, an `is_archived` boolean column is updated to `True`. 
All list, update, and detail endpoints automatically filter out archived issues. This preserves relational integrity and prevents accidental data loss.

### 3. Automatic Append-Only Activity Log (Audit Trail)
Whenever an issue is modified using `PATCH`, the application automatically calculates which fields changed (`title`, `description`, `status`, `priority`, `assignee_id`, `due_date`). 
It logs the **old value**, **new value**, the **actor (user)** who performed the action, and a **timestamp** inside the `issue_activities` table. By design, there are no endpoints to modify or delete logs, ensuring a complete and unalterable audit trail.

---

## 📈 Scalability & Production Roadmap

For large-scale, high-concurrency production environments, these optimizations are recommended:

### 1. Database-Level Custom Sorting
Currently, sorting issues by `status` or `priority` Enums is performed in-memory (using Python's `sort()`) after pulling all project issues into RAM. For projects with thousands of issues, this is highly inefficient.
- **Production Fix**: Map Enum values to integer indexes inside the database (or use a PostgreSQL custom Enum type), allowing the database query engine to execute sorting via `.order_by()` before returning paginated records.

### 2. Aerich Migrations
With PostgreSQL, Tortoise ORM can still generate the schema automatically on startup during development. However, for production deployments, transition database schema management to **Aerich** (a migration tool for Tortoise ORM):
```bash
# Initialize migrations
aerich init -t app.database.TORTOISE_ORM
aerich init-db

# Make and apply updates
aerich migrate --name added_labels
aerich upgrade
```

### 3. Environment Secret Key Rotation
Move hardcoded configuration items to secure cloud secret managers (like AWS Secrets Manager, GCP Secret Manager, or Vault) and pull them into the environment variables during deployment.
