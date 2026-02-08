# Agentic TODO Application

A TODO application with AI-powered natural language interface using FastAPI, SQLModel, Neon PostgreSQL, and Groq LLM.

## Features

- User authentication with JWT tokens
- Natural language task management via AI agent
- RESTful API with automatic OpenAPI documentation
- Async database operations with SQLModel + asyncpg

## Tech Stack

- **Backend**: FastAPI
- **Database**: Neon PostgreSQL (async)
- **ORM**: SQLModel
- **Authentication**: JWT + bcrypt
- **AI Agent**: OpenAI Agents SDK + Groq API

## Setup

### 1. Install Dependencies

```bash
uv sync
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required variables:
- `DATABASE_URL`: Your Neon PostgreSQL connection string
- `api_key`: Your Groq API key
- `SECRET_KEY`: A secure random string for JWT signing

### 3. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login and get access token |

### Agent

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agent/chat` | Chat with AI agent (requires auth) |

## Usage Examples

### 1. Register a User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=password123"
```

### 3. Chat with Agent

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"message": "Create a task to buy groceries"}'
```

## Agent Commands

The AI agent understands natural language. Examples:

- "Add a task to buy groceries"
- "Create a high priority task: Review PR"
- "Show my tasks"
- "What are my pending tasks?"
- "Mark task 1 as done"
- "Complete task 3"
- "Delete task 2"
- "What's in task 5?"

## Project Structure

```
groq-agent/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings
│   ├── database.py          # Async DB setup
│   ├── models.py            # SQLModel models
│   ├── schemas.py           # Pydantic schemas
│   ├── auth.py              # JWT + bcrypt
│   ├── dependencies.py      # FastAPI deps
│   ├── agent/
│   │   ├── context.py       # Agent context
│   │   ├── tools.py         # DB-aware tools
│   │   └── factory.py       # Agent creation
│   └── routers/
│       ├── auth_router.py   # Auth endpoints
│       └── agent_router.py  # Chat endpoint
├── .env.example
├── pyproject.toml
└── README.md
```
