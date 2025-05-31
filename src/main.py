from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any
from datetime import datetime
import os
import json
import uuid
from pydantic import validator


def load_todos() -> Dict[str, Any]:
    try:
        if os.path.exists("todos.json"):
            with open("todos.json", "r", encoding="utf-8") as f:
                todos_dict = json.load(f)
                return {todo["id"]: todo for todo in todos_dict} if isinstance(todos_dict, list) else todos_dict
        else:
            # ファイルが存在しない場合は空の辞書を返し、ファイルを作成
            save_todos({})
            return {}
    except Exception as e:
        print(f"Error loading todos: {e}")
        return {}


def save_todos(todos: Dict[str, Any]) -> None:
    try:
        with open("todos.json", "w", encoding="utf-8") as f:
            json.dump(list(todos.values()), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving todos: {e}")
        raise HTTPException(status_code=500, detail="Failed to save todos")


class TodoCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str
    done: bool = False
    deadline: str
    tags: List[str] = []

    @validator('title')
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('タイトルは空にできません')
        return v.strip()

    @validator('deadline')
    def deadline_must_be_valid(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('期限はYYYY-MM-DD形式で入力してください')


class Todo(TodoCreate):
    model_config = ConfigDict(extra='forbid')
    id: str
    created_at: str


app = FastAPI()

# 静的ファイルの提供
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


@app.get("/todos/done", response_model=List[Todo])
def read_done():
    todos = load_todos()
    return [todo for todo in todos.values() if todo["done"]]


@app.get("/todos/not_done", response_model=List[Todo])
def read_not_done():
    todos = load_todos()
    return [todo for todo in todos.values() if not todo["done"]]


@app.get("/todos/{todo_id}", response_model=Todo)
def read_todo(todo_id: str):
    todos = load_todos()
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    return todos[todo_id]


@app.post("/todos", response_model=Todo)
async def create_todo(todo_create: TodoCreate):
    try:
        print("受信したデータ:", todo_create.model_dump())  # デバッグログ
        todos = load_todos()
        todo_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        todo = Todo(
            **todo_create.model_dump(),
            id=todo_id,
            created_at=created_at
        )
        
        print("作成するTodo:", todo.model_dump())  # デバッグログ
        todos[todo_id] = todo.model_dump()
        save_todos(todos)
        return todo
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")  # デバッグログ
        raise HTTPException(
            status_code=422,
            detail=f"Todoの作成に失敗しました: {str(e)}"
        )


@app.put("/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: str, todo_update: TodoCreate):
    todos = load_todos()
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")

    updated_todo = Todo(
        **todo_update.model_dump(),
        id=todo_id,
        created_at=todos[todo_id]["created_at"]
    )
    todos[todo_id] = updated_todo.model_dump()
    save_todos(todos)
    return updated_todo


@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: str):
    todos = load_todos()
    if todo_id not in todos:
        raise HTTPException(status_code=404, detail="Todo not found")
    
    del todos[todo_id]
    save_todos(todos)
    return {"message": "Todo deleted successfully"}
