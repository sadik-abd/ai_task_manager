# AI-Powered Task Management System

A natural language task management system that uses AI to help you organize projects and tasks. The system understands plain English commands and maintains your tasks in a SQLite database.

## Features

- 🗣️ **Natural Language Commands**: Interact with the system using plain English
- 🤖 **AI-Powered**: AI helps organize tasks and provides recommendations
- 📁 **Project Management**: Create and organize projects
- ✅ **Task Management**: Add, delete, and complete tasks
- 💬 **Task Discussion**: Discuss tasks with AI to get insights
- 🎯 **Smart Recommendations**: AI suggests what to work on next
- 🗄️ **Persistent Storage**: All data stored in SQLite database

## Prerequisites

- Python 3.7 or higher
- Required Python packages:
  ```
  google-generativeai
  sqlite3
  ```

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd task_manager
   ```

2. Install required packages:
   ```bash
   pip install google-generativeai
   ```

3. Set up your Google AI API key:
   - Get an API key from Google AI Studio
   - Add GOOGLE_API_KEY in `.env` or just as environment variable

## Usage

Run commands using natural language:

```bash
python main.py "your command here"
```

### Example Commands

1. **Create a Project**
   ```bash
   python main.py "Create a project called Website Development"
   ```

2. **Add Tasks**
   ```bash
   python main.py "Add a task UI design to the Website Development project"
   python main.py "Add a high priority task database setup to Website Development"
   ```

3. **Get Task Recommendations**
   ```bash
   python main.py "What should I work on next?"
   ```

4. **Delete Tasks**
   ```bash
   python main.py "Delete the UI design task"
   ```

5. **Complete Tasks**
   ```bash
   python main.py "Mark the database setup task as complete"
   ```

6. **Discuss Tasks**
   ```bash
   python main.py "Let's discuss the progress of Website Development project"
   ```

## System Architecture

The system consists of three main components:

1. **AI Command Processor**
   - Converts natural language to structured commands
   - Provides context-aware responses
   - Generates task recommendations

2. **Database Manager**
   - SQLite database for persistent storage
   - Manages projects and tasks
   - Maintains relationships and metadata

3. **Command Executor**
   - Executes AI-interpreted commands
   - Handles all CRUD operations
   - Manages task states and updates

## Database Schema

### Projects Table
```sql
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active'
)
```

### Tasks Table
```sql
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'pending',
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    due_date TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id)
)
```

## Error Handling

The system includes robust error handling for:
- Invalid commands
- Missing projects/tasks
- Database errors
- API failures

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License - feel free to use this project for your own purposes. 