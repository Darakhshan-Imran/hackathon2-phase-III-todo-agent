# 🏗️ Architecture Diagram

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  (Next.js 16 App / Web Browser)                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       │ HTTP/REST
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    API ROUTERS                           │   │
│  │                                                          │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐        │   │
│  │  │   Auth     │  │   Agent    │  │    SQL     │        │   │
│  │  │  Router    │  │  Router    │  │  Router    │        │   │
│  │  │            │  │            │  │            │        │   │
│  │  │ /register  │  │  /chat     │  │ /execute   │        │   │
│  │  │  /login    │  │  +logs 🆕  │  │ /schema    │        │   │
│  │  └────────────┘  └────────────┘  └────────────┘        │   │
│  └────────────┬────────────┬────────────┬─────────────────┘   │
│               │            │            │                      │
│               ▼            ▼            ▼                      │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              MIDDLEWARE & DEPENDENCIES                   │  │
│  │                                                          │  │
│  │  • JWT Authentication                                   │  │
│  │  • Database Session Management                          │  │
│  │  • CORS                                                 │  │
│  │  • Groq Client Injection                                │  │
│  │  • Error Categorization 🆕                              │  │
│  └──────────────────────────┬──────────────────────────────┘  │
│                              │                                 │
└──────────────────────────────┼─────────────────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│    AI AGENT LAYER        │    │   DATABASE LAYER         │
│                          │    │                          │
│  ┌────────────────────┐ │    │  ┌────────────────────┐ │
│  │  Agent Factory     │ │    │  │  SQLModel/SQLAlchemy│ │
│  │                    │ │    │  │                    │ │
│  │  • Mandatory Tool  │ │    │  │  • async engine    │ │
│  │    Usage Rules 🆕  │ │    │  │  • session maker   │ │
│  │  • Model config    │ │    │  │  • models          │ │
│  │  • Parallel calls🆕│ │    │  └──────────┬─────────┘ │
│  └─────────┬──────────┘ │    │             │           │
│            │            │    │             │           │
│            ▼            │    │             │           │
│  ┌────────────────────┐ │    │  ┌──────────▼─────────┐ │
│  │   Agent Tools      │ │    │  │   Neon PostgreSQL  │ │
│  │                    │◄┼────┼──┤                    │ │
│  │  • create_task     │ │    │  │  • users           │ │
│  │  • list_tasks      │ │    │  │  • todos           │ │
│  │  • update_task     │ │    │  │  • conversations🆕 │ │
│  │  • delete_task     │ │    │  └────────────────────┘ │
│  │  • get_details     │ │    │                          │
│  │  • search_keyword🆕│ │    └──────────────────────────┘
│  │    (fuzzy match)   │ │
│  │  • execute_sql ⚡  │ │
│  │  • generate_sql⚡  │ │
│  └────────────────────┘ │
│                          │
│  ┌────────────────────┐ │
│  │   Agent Context    │ │
│  │                    │ │
│  │  • user_id         │ │
│  │  • db_session      │ │
│  │  • flush() not     │ │
│  │    commit() 🆕     │ │
│  └────────────────────┘ │
└──────────────────────────┘
         │
         ▼
┌──────────────────────────┐
│   GROQ API (LLM)         │
│                          │
│  • openai/gpt-oss-20b    │
│  • Parallel function     │
│    calling enabled 🆕    │
│  • Max 30 turns          │
│  • Tracing enabled 🆕    │
└──────────────────────────┘

⚡ = SQL Query Features
🆕 = Recent Enhancements
```

## Request Flow Diagrams

### 1. Natural Language Query Flow (with Real-Time Logs)

```
User: "Find tasks about cooking"
  │
  ├─→ POST /agent/chat
  │   Headers: Authorization: Bearer <token>
  │   Body: {"message": "Find tasks about cooking"}
  │
  ├─→ Auth Middleware
  │   ├─→ Verify JWT token
  │   └─→ Extract user_id
  │
  ├─→ Agent Router
  │   ├─→ Create AgentContext(user_id, db_session)
  │   ├─→ Initialize Agent with tools
  │   └─→ Enable tracing for logs 🆕
  │
  ├─→ Groq API (LLM) - Parallel Execution 🆕
  │   ├─→ Analyze user message
  │   ├─→ MANDATORY: Call tool first (enforced)
  │   └─→ Choose: search_tasks_by_keyword tool
  │
  ├─→ search_tasks_by_keyword("cooking") 🆕
  │   ├─→ Fetch all user tasks from DB
  │   ├─→ Try exact substring match first
  │   ├─→ If no match, apply fuzzy matching
  │   │   ├─→ Calculate similarity scores
  │   │   ├─→ Threshold: 60%
  │   │   └─→ Rank by similarity
  │   ├─→ Return matches with metadata
  │   └─→ Log: [tool_call] 🔧 search_tasks_by_keyword({"keyword":"cooking"})
  │
  ├─→ Database (Neon PostgreSQL)
  │   ├─→ Execute: SELECT * FROM todos WHERE user_id = 123
  │   └─→ Returns: All user tasks
  │
  ├─→ Fuzzy Matching Algorithm 🆕
  │   ├─→ Uses difflib.SequenceMatcher
  │   ├─→ Handles "cooking" → "cook", "cooked"
  │   └─→ Log: [tool_result] ✓ Found 2 tasks matching 'cooking'
  │
  ├─→ Agent processes result
  │   ├─→ Log: [reasoning] I found matching tasks
  │   └─→ Generate response with task details
  │
  └─→ Response to User
      {
        "response": "Found 2 tasks: #1 Cook dinner, #3 Cooking class",
        "agent_logs": [
          {"action": "tool_call", "details": "🔧 search_tasks_by_keyword(...)"},
          {"action": "tool_result", "details": "✓ Found 2 tasks..."},
          {"action": "reasoning", "details": "I found matching tasks"}
        ]
      }
```

### 2. Direct SQL Execution Flow

```
User: SQL Query
  │
  ├─→ POST /sql/execute
  │   Headers: Authorization: Bearer <token>
  │   Body: {"query": "SELECT COUNT(*)..."}
  │
  ├─→ Auth Middleware
  │   └─→ Verify token & get user
  │
  ├─→ SQL Router
  │   ├─→ Validate query
  │   │   ├─→ SELECT only? ✓
  │   │   ├─→ No dangerous keywords? ✓
  │   │   └─→ user_id filter present? ✓
  │   │
  │   ├─→ Replace {user_id}
  │   └─→ Execute query
  │
  ├─→ Database
  │   └─→ Return results
  │
  └─→ Response to User
      {
        "success": true,
        "result": "...",
        "rows_affected": 1
      }
```

### 3. Task Management Flow (Enhanced)

```
User: "Create a task to review code"
  │
  ├─→ POST /agent/chat
  │   Body: {"message": "Create a task...", "session_id": "xyz"}
  │
  ├─→ Load conversation history 🆕
  │   └─→ Query ConversationMessage by session_id
  │
  ├─→ Agent analyzes with context
  │   ├─→ MANDATORY: Must call tool 🆕
  │   └─→ Decides: Use create_task tool
  │
  ├─→ create_task tool
  │   ├─→ Create Todo object
  │   ├─→ session.add(todo)
  │   ├─→ session.flush() ← NOT commit() 🆕
  │   └─→ Return task details immediately
  │
  ├─→ Database Transaction
  │   ├─→ INSERT into todos
  │   ├─→ Flush but don't commit yet
  │   └─→ Task visible in session
  │
  ├─→ Save to conversation history 🆕
  │   ├─→ Save user message
  │   ├─→ Save agent response
  │   └─→ Commit all together
  │
  └─→ Response with logs 🆕
      {
        "response": "Task #1 created: 'review code'",
        "session_id": "xyz",
        "agent_logs": [
          {"action": "tool_call", "details": "🔧 create_task(...)"},
          {"action": "tool_result", "details": "✓ Task #1 created"}
        ]
      }
```

## Data Flow

```
┌────────────┐
│   Client   │
└─────┬──────┘
      │
      │ 1. HTTP Request (+ JWT)
      ▼
┌────────────────────┐
│  FastAPI Router    │
└─────┬──────────────┘
      │
      │ 2. Validate & Extract user_id
      ▼
┌────────────────────┐
│  Agent/SQL Handler │◄─────────┐
└─────┬──────────────┘          │
      │                         │
      │ 3a. Natural Language    │ 3b. Direct SQL
      │                         │
      ▼                         ▼
┌─────────────┐        ┌────────────────┐
│  Groq API   │        │ SQL Validator  │
│  (LLM)      │        └────────┬───────┘
└─────┬───────┘                 │
      │                         │
      │ 4. Tool Selection       │ 4. Validated Query
      ▼                         │
┌────────────────────────────┐  │
│     Agent Tools            │  │
│  • execute_sql_query       │◄─┘
│  • generate_sql_query      │
│  • create_task             │
│  • list_tasks              │
│  • update_task             │
│  • delete_task             │
└─────┬──────────────────────┘
      │
      │ 5. SQL Query
      ▼
┌────────────────────┐
│   Database         │
│   (PostgreSQL)     │
└─────┬──────────────┘
      │
      │ 6. Results
      ▼
┌────────────────────┐
│  Response Formatter│
└─────┬──────────────┘
      │
      │ 7. JSON Response
      ▼
┌────────────┐
│   Client   │
└────────────┘
```

## Security Layers

```
┌─────────────────────────────────────────────┐
│           CLIENT REQUEST                     │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  Layer 1: JWT Auth   │
        │  • Token validation  │
        │  • User extraction   │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │  Layer 2: SQL Type   │
        │  • SELECT only       │
        │  • Reject others     │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Layer 3: Dangerous   │
        │ Keywords             │
        │ • DROP, DELETE, etc  │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Layer 4: user_id     │
        │ Filtering            │
        │ • Must be present    │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Layer 5: Placeholder │
        │ Replacement          │
        │ • {user_id} → real   │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │ Layer 6: Try-Catch   │
        │ • SQL error handling │
        │ • Safe error msgs    │
        └──────────┬───────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │   SAFE EXECUTION     │
        └──────────────────────┘
```

## Technology Stack

```
┌──────────────────────────────────────────┐
│         FRONTEND LAYER 🆕                 │
│  • Next.js 16.1.6 (App Router)           │
│  • React 19 (RSC)                        │
│  • TypeScript 5                          │
│  • Tailwind CSS 4                        │
│  • Framer Motion 12                      │
│  • Radix UI (Components)                 │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│         PRESENTATION LAYER                │
│  • FastAPI (API Framework)               │
│  • Pydantic (Validation)                 │
│  • JWT (Authentication)                  │
│  • CORS Middleware                       │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│         APPLICATION LAYER                 │
│  • OpenAI Agents SDK v0.7.0              │
│  • Groq API (LLM Provider)               │
│  • Custom Agent Tools (8 tools)          │
│  • Fuzzy Matching (difflib) 🆕           │
│  • Parallel Tool Calls 🆕                │
│  • Real-time Logging 🆕                  │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│         DATA ACCESS LAYER                 │
│  • SQLModel (ORM)                        │
│  • SQLAlchemy 2.0 (Async)                │
│  • asyncpg (PostgreSQL Driver)           │
│  • Session Management (flush) 🆕         │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│         DATABASE LAYER                    │
│  • Neon PostgreSQL (Cloud Database)      │
│  • Tables: users, todos, conversations🆕 │
│  • Async engine with connection pooling  │
└──────────────────────────────────────────┘
```

## Component Interactions

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Router    │─────→│   Agent     │─────→│    Groq     │
│             │      │  Factory    │      │    API      │
└─────────────┘      └─────────────┘      └─────────────┘
       │                    │                     │
       │                    │                     │
       ▼                    ▼                     ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Auth      │      │   Tools     │      │ Natural     │
│ Middleware  │      │  Registry   │      │ Language    │
└─────────────┘      └─────────────┘      └─────────────┘
       │                    │                     
       │                    │                     
       ▼                    ▼                     
┌─────────────┐      ┌─────────────┐      
│  Database   │◄─────│   Context   │      
│  Session    │      │  (user_id)  │      
└─────────────┘      └─────────────┘      
```

---

## Legend

- `→` : Data flow / Function call
- `◄` : Response / Return value
- `⚡` : SQL query features
- `🆕` : Recent enhancements (2026)
- `✓` : Validation passed
- `┌─┐` : Component boundary
- `│ │` : Contains / Part of

## Recent Enhancements (2026)

### Agent Intelligence
- **Mandatory Tool Usage Protocol**: Agent MUST call tools before responding
- **Parallel Tool Calls**: Multiple independent tools execute simultaneously
- **Real-time Execution Logs**: Capture actual tool calls, results, and reasoning
- **Fuzzy Search**: Intelligent keyword matching using SequenceMatcher (60% threshold)
- **Enhanced Instructions**: Violation examples and enforcement rules

### Database & Performance
- **Transaction Optimization**: Use `flush()` instead of `commit()` to prevent race conditions
- **Conversation History**: Session-based stateful chat with ConversationMessage table
- **Error Categorization**: Structured error handling with detailed messages

### Frontend Integration
- **Next.js 16 App**: Modern React 19 with Server Components
- **Real Agent Logs Display**: Shows actual tool execution, not simulated
- **Retry/Edit/Copy**: Enhanced message interaction capabilities
- **Framer Motion**: Smooth animations and transitions
- **Markdown Parsing**: Rich text formatting in responses

### Security & Validation
- **Enhanced Error Handling**: Categorized errors (database, timeout, API, etc.)
- **Tool Schema Validation**: Fixed optional parameter handling for Groq API
- **Session Management**: Secure session-based conversation tracking
