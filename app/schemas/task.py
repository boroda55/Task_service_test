from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.task import Priority, Status

class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    priority: Priority = Priority.MEDIUM

class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str | None
    priority: Priority
    status: Status
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    result: str | None
    error: str | None

class TaskStatusResponse(BaseModel):
    status: Status

class TaskListResponse(BaseModel):
    items: list[TaskRead]
    total: int
    page: int
    per_page: int
