from pydantic import BaseModel, Field
from typing import List, Dict

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100, description="Название задачи")
    description: str | None = Field(None, max_length=500, description="Описание задачи")

class TaskCreate(TaskBase):
    # user_id удален отсюда, так как он извлекается сервером из JWT-токена
    pass

class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=100, description="Новое название")
    description: str | None = Field(None, max_length=500, description="Новое описание")
    is_completed: bool | None = Field(None, description="Статус выполнения задачи")

class TaskResponse(TaskBase):
    id: int
    is_completed: bool = False
    user_id: int  # В ответе клиенту ID создателя по-прежнему возвращается

    model_config = {"from_attributes": True}

class LikesBatchRequest(BaseModel):
    entity_ids: List[int]

LikesBatchResponse = Dict[str, int]
