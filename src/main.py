from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, field_validator
from boto3.dynamodb.conditions import Attr
from typing import List, Dict, Any
from datetime import datetime
import logging
import uuid
import boto3

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('todo_table')

# 静的ファイルの提供
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


class TodoCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str
    done: bool = False
    deadline: str
    tags: List[str] = []

    @field_validator('title', mode='before')
    @classmethod
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError('タイトルは空にできません')
        return v.strip()

    @field_validator('deadline', mode='before')
    @classmethod
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


@app.get("/todos/done", response_model=List[Todo])
def read_done():
    response = table.scan(
        FilterExpression=Attr('done').eq(True)
    )
    return response.get('Items', [])


@app.get("/todos/not_done", response_model=List[Todo])
def read_not_done():
    response = table.scan(
        FilterExpression=Attr('done').eq(False)
    )
    return response.get('Items', [])


@app.get("/todos/{todo_id}", response_model=Todo)
def read_todo(todo_id: str):
    response = table.get_item(Key={'id': todo_id})
    if 'Item' not in response:
        raise HTTPException(status_code=404, detail="Todo not found")
    return response['Item']


@app.post("/todos", response_model=Todo)
async def create_todo(todo_create: TodoCreate):
    todo_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    todo = Todo(
        **todo_create.model_dump(),
        id=todo_id,
        created_at=created_at
    )

    logger.info("作成するTodo: %s", todo.model_dump())

    try:
        table.put_item(Item=todo.model_dump())
    except Exception as e:
        logger.error("DynamoDB書き込みエラー: %s", str(e))
        raise HTTPException(status_code=500, detail="DynamoDBへの書き込みに失敗しました")

    return todo


@app.put("/todos/{todo_id}", response_model=Todo)
def update_todo(todo_id: str, todo_update: TodoCreate):
    response = table.get_item(Key={'id': todo_id})
    if 'Item' not in response:
        raise HTTPException(status_code=404, detail="Todo not found")

    updated_todo = Todo(
        **todo_update.model_dump(),
        id=todo_id,
        created_at=response['Item']['created_at']
    )

    try:
        table.put_item(Item=updated_todo.model_dump())
    except Exception as e:
        logger.error("DynamoDB更新エラー: %s", str(e))
        raise HTTPException(status_code=500, detail="DynamoDBの更新に失敗しました")

    return updated_todo


@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: str):
    try:
        table.delete_item(Key={'id': todo_id})
        return {"message": "Todo deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=404, detail="Todo not found")
