# 🎯 Quick Start Guide - SQL Query Agent

## What's New?

Your TODO agent can now **execute SQL queries from natural language**! Ask questions about your data and get instant insights.

## 🚀 Setup & Run

1. **Set up your environment file:**
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual credentials:
# - DATABASE_URL: Get from https://neon.tech (PostgreSQL connection string)
# - api_key: Get from https://console.groq.com/keys (Groq API key)
# - SECRET_KEY: Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. **Start the server:**
```bash
uvicorn app.main:app --reload
```

3. **Run the test script (optional):**
```bash
python test_sql_agent.py
```

## 💬 Example Conversations

### Task Management (Original Features)
```
You: "Create a task to review the code"
Agent: Task #1 created: 'review the code'

You: "Show my tasks"
Agent: ○ #1 review the code (pending)

You: "Mark task 1 as done"
Agent: Task #1 'review the code' updated: status → completed
```

### Data Analysis (New Features!)
```
You: "How many completed tasks do I have?"
Agent: You have 5 completed tasks.

You: "Show me tasks created this week"
Agent: [Executes SQL and shows results]
Query returned 3 row(s):
id | title | created_at
1 | Review code | 2026-02-03 10:30:00
2 | Buy groceries | 2026-02-04 14:20:00
3 | Update docs | 2026-02-05 09:15:00

You: "What's my task completion rate?"
Agent: [Generates and runs analytics query]
You have completed 5 out of 10 tasks (50% completion rate)
```

## 🔍 What Can You Ask?

### Basic Queries
- "How many tasks do I have?"
- "Show my pending tasks"
- "Count my completed tasks"
- "What tasks did I create today?"

### Analytics
- "What's my completion rate?"
- "Show me tasks from this week"
- "Count tasks by status"
- "When did I create the most tasks?"

### SQL Generation
- "Generate a query to show my recent tasks"
- "Help me write SQL to count pending tasks"
- "Create a query for today's tasks"

## 🛡️ Security Features

All queries are automatically:
- ✅ Restricted to SELECT only
- ✅ Filtered by your user_id
- ✅ Validated for dangerous keywords
- ✅ Protected from SQL injection

## 📊 Direct SQL API (Advanced)

### Execute Custom Query
```bash
curl -X POST http://localhost:8000/sql/execute \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SELECT COUNT(*) FROM todos WHERE user_id = {user_id}"
  }'
```

### Get Database Schema
```bash
curl http://localhost:8000/sql/schema \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📚 API Documentation

Once running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🧪 Testing

### Quick Test Sequence

1. Register a user:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "password123"
  }'
```

2. Login and get token:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "password123"
  }'
```

3. Chat with agent:
```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How many tasks do I have?"
  }'
```

## 🎯 Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Register new user |
| `/auth/login` | POST | Login and get token |
| `/agent/chat` | POST | Chat with AI agent |
| `/sql/execute` | POST | Execute SQL query |
| `/sql/schema` | GET | Get database schema |

## 📖 Full Documentation

See [SQL_AGENT_DOCUMENTATION.md](SQL_AGENT_DOCUMENTATION.md) for complete details on:
- All available features
- Security implementation
- Query examples
- API specifications
- Best practices

## 🐛 Troubleshooting

### Database Connection Issues
If you see connection errors, check:
1. `.env` file has correct `DATABASE_URL`
2. `asyncpg` is installed: `pip install asyncpg`
3. Database is accessible from your network

### Agent Not Responding
Check:
1. Groq API key is valid in `.env`
2. Server logs for errors: check terminal output
3. Token is valid (not expired)

### SQL Query Errors
Remember:
1. Only SELECT queries work
2. Must include `user_id` filtering
3. Use `{user_id}` placeholder for your user ID

## 💡 Tips

1. **Start simple**: Try basic queries before complex analytics
2. **Use placeholders**: Always use `{user_id}` in queries
3. **Check schema**: Use `/sql/schema` to see available tables
4. **Test safely**: The agent blocks dangerous operations
5. **Natural language**: Just ask naturally, the agent understands!

## 🎉 Have Fun!

Your agent is now a powerful data analyst. Ask it questions, explore your data, and discover insights!

Need help? Check the docs or ask the agent: "What can you help me with?"
