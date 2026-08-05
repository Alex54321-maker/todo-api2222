from pydantic import BaseModel, Field
from typing import List, Dict

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)

class TaskCreate(TaskBase):
    user_id: int = Field(..., description="ID создателя задачи")

class TaskUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=500)
    is_completed: bool | None = Field(None)

class TaskResponse(TaskBase):
    id: int
    is_completed: bool = False
    user_id: int

    model_config = {"from_attributes": True}

class LikesBatchRequest(BaseModel):
    entity_ids: List[int]

LikesBatchResponse = Dict[str, int]
