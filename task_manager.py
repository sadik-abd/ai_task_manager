#!/usr/bin/env python3
"""
AI-Powered Task Management System

The system accepts natural language commands and uses AI to convert them to structured JSON responses.
All data is stored in SQLite database.

Usage:
  python main.py "Create a project called Website Development"
  python main.py "Add a task UI design to the Website Development project"
  python main.py "What should I work on next?"
  python main.py "Delete the UI design task"
"""

import sqlite3
import argparse
import sys
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv
# === Gemini AI Integration ===
try:
    load_dotenv()
except Exception as e:
    pass
import google.generativeai as genai
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

class GeminiModel:
    def __init__(self, model_name: str = 'gemini-2.5-flash-preview-05-20', system_prompt: str = None) -> None:
        self.model = genai.GenerativeModel(model_name)
    
    def generate_text(self, inp: str):
        generation_config = genai.GenerationConfig(
            max_output_tokens=8192,
            temperature=0.7
        )
        safety_settings = {
            "HARASSMENT": "block_none",
            "HATE": "block_none",
            "SEXUAL": "block_none",
            "DANGEROUS": "block_none",
        }
        response = self.model.generate_content(
            inp,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        cost = (response.usage_metadata.total_token_count / 1_000_000) * 5
        return response.text.strip(), cost


class TaskDatabase:
    """Handles all database operations for projects and tasks"""
    
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Tasks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
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
        ''')
        
        conn.commit()
        conn.close()
    
    def create_project(self, name: str, description: str = "") -> int:
        """Create a new project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO projects (name, description) VALUES (?, ?)",
                (name, description)
            )
            project_id = cursor.lastrowid
            conn.commit()
            return project_id
        except sqlite3.IntegrityError:
            raise ValueError(f"Project '{name}' already exists")
        finally:
            conn.close()
    
    def add_task(self, project_name: str, title: str, description: str = "", priority: str = "medium", due_date: str = None) -> int:
        """Add a task to a project"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get project ID
        cursor.execute("SELECT id FROM projects WHERE name = ?", (project_name,))
        project = cursor.fetchone()
        
        if not project:
            raise ValueError(f"Project '{project_name}' not found")
        
        project_id = project[0]
        
        cursor.execute(
            "INSERT INTO tasks (project_id, title, description, priority, due_date) VALUES (?, ?, ?, ?, ?)",
            (project_id, title, description, priority, due_date)
        )
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    
    def delete_task(self, task_identifier: str) -> bool:
        """Delete a task by ID or title"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Try to delete by ID first
        try:
            task_id = int(task_identifier)
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        except ValueError:
            # If not a number, try to delete by title
            cursor.execute("DELETE FROM tasks WHERE title LIKE ?", (f"%{task_identifier}%",))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
    
    def get_all_data(self) -> Dict:
        """Get all projects and tasks for AI context"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all projects
        cursor.execute("SELECT * FROM projects WHERE status = 'active'")
        projects = []
        for row in cursor.fetchall():
            project = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'created_date': row[3],
                'status': row[4]
            }
            
            # Get tasks for this project
            cursor.execute("SELECT * FROM tasks WHERE project_id = ? AND status != 'completed'", (project['id'],))
            tasks = []
            for task_row in cursor.fetchall():
                tasks.append({
                    'id': task_row[0],
                    'title': task_row[2],
                    'description': task_row[3],
                    'priority': task_row[4],
                    'status': task_row[5],
                    'created_date': task_row[6],
                    'due_date': task_row[7]
                })
            
            project['tasks'] = tasks
            projects.append(project)
        
        conn.close()
        return {'projects': projects}
    
    def update_task_status(self, task_identifier: str, new_status: str) -> bool:
        """Update task status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            task_id = int(task_identifier)
            cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
        except ValueError:
            cursor.execute("UPDATE tasks SET status = ? WHERE title LIKE ?", (new_status, f"%{task_identifier}%"))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return updated


class AITaskManager:
    """Main AI-powered task management system"""
    
    def __init__(self):
        self.db = TaskDatabase()
        self.ai = GeminiModel()
    
    def process_command(self, user_input: str) -> str:
        """Process natural language command through AI and execute the result"""
        
        # Get current database state for AI context
        current_data = self.db.get_all_data()
        
        # Create AI prompt
        system_prompt = f"""
You are a task management assistant. The user will give you natural language commands about managing projects and tasks.

Current database state:
{json.dumps(current_data, indent=2)}

Based on the user's input, respond with ONLY a JSON object in this exact format:
{{
    "function": "function_name",
    "function_arg": {{"key": "value"}},
    "output": "User-friendly response message"
}}

Available functions:
- "create_project": Create a new project
  function_arg: {{"name": "project_name", "description": "optional_description"}}
  
- "add_task": Add a task to a project
  function_arg: {{"project_name": "name", "title": "task_title", "description": "optional", "priority": "low/medium/high", "due_date": "optional"}}
  
- "delete_task": Delete a task
  function_arg: {{"task_identifier": "task_id_or_title"}}
  
- "complete_task": Mark a task as completed
  function_arg: {{"task_identifier": "task_id_or_title"}}
  
- "recommend_task": Suggest what task to work on next
  function_arg: {{}}
  
- "discuss": General discussion about tasks
  function_arg: {{"topic": "what_to_discuss"}}

Examples:
User: "Create a project called Website Development"
Response: {{"function": "create_project", "function_arg": {{"name": "Website Development", "description": ""}}, "output": "I've created the 'Website Development' project for you!"}}

User: "Add a task UI design to the Website Development project"
Response: {{"function": "add_task", "function_arg": {{"project_name": "Website Development", "title": "UI design", "description": "", "priority": "medium"}}, "output": "I've added the 'UI design' task to your Website Development project!"}}

User: "What should I work on next?"
Response: {{"function": "recommend_task", "function_arg": {{}}, "output": "Based on your tasks, I recommend working on the UI design task in the Website Development project as it's high priority and blocking other work."}}

User input: {user_input}
"""
        
        try:
            ai_response, cost = self.ai.generate_text(system_prompt)
            
            # Parse AI response as JSON
            try:
                command_json = json.loads(ai_response)
            except json.JSONDecodeError:
                # If AI didn't return valid JSON, try to extract it
                start = ai_response.find('{')
                end = ai_response.rfind('}') + 1
                if start != -1 and end != 0:
                    command_json = json.loads(ai_response[start:end])
                else:
                    return "Sorry, I couldn't understand that command. Please try again."
            
            # Execute the function
            result = self.execute_function(command_json)
            return result
            
        except Exception as e:
            return f"Error processing command: {str(e)}"
    
    def execute_function(self, command_json: Dict) -> str:
        """Execute the function specified in the AI's JSON response"""
        
        function_name = command_json.get("function")
        function_arg = command_json.get("function_arg", {})
        output_message = command_json.get("output", "Operation completed.")
        
        try:
            if function_name == "create_project":
                name = function_arg.get("name")
                description = function_arg.get("description", "")
                self.db.create_project(name, description)
                return output_message
            
            elif function_name == "add_task":
                project_name = function_arg.get("project_name")
                title = function_arg.get("title")
                description = function_arg.get("description", "")
                priority = function_arg.get("priority", "medium")
                due_date = function_arg.get("due_date")
                self.db.add_task(project_name, title, description, priority, due_date)
                return output_message
            
            elif function_name == "delete_task":
                task_identifier = function_arg.get("task_identifier")
                success = self.db.delete_task(task_identifier)
                if success:
                    return output_message
                else:
                    return f"Could not find task '{task_identifier}' to delete."
            
            elif function_name == "complete_task":
                task_identifier = function_arg.get("task_identifier")
                success = self.db.update_task_status(task_identifier, "completed")
                if success:
                    return output_message
                else:
                    return f"Could not find task '{task_identifier}' to complete."
            
            elif function_name == "recommend_task":
                # AI handles the recommendation logic in the output message
                return output_message
            
            elif function_name == "discuss":
                # AI handles the discussion in the output message
                return output_message
            
            else:
                return f"Unknown function: {function_name}"
                
        except Exception as e:
            return f"Error executing {function_name}: {str(e)}"


def Main():
    """Main CLI interface"""
    if len(sys.argv) < 2:
        print("Usage: python main.py \"<your natural language command>\"")
        print("\nExamples:")
        print("  python main.py \"Create a project called Website Development\"")
        print("  python main.py \"Add a task UI design to the Website Development project\"")
        print("  python main.py \"What should I work on next?\"")
        print("  python main.py \"Delete the UI design task\"")
        return
    
    user_input = " ".join(sys.argv[1:])
    
    # Initialize the task manager
    task_manager = AITaskManager()
    
    # Process the command
    result = task_manager.process_command(user_input)
    print(result)


if __name__ == "__main__":
    Main()

