from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.task import Priority, Status
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskListResponse, TaskRead, TaskStatusResponse
from app.services.queue import queue
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

@router.post("", response_model=TaskRead, status_code=201)
async def create_task(payload: TaskCreate, bg: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    task = await service.create_task(payload)
    bg.add_task(queue.publish, task.id)
    return task

@router.get("", response_model=TaskListResponse)
async def list_tasks(status: Status | None = None, priority: Priority | None = None, page: int = Query(1, ge=1), per_page: int = Query(50, ge=1, le=200), db: AsyncSession = Depends(get_db)):
    service = TaskService(db)
    items, total = await service.list_tasks(status, priority, page, per_page)
    return TaskListResponse(items=items, total=total, page=page, per_page=per_page)

@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    return await TaskService(db).get_task(task_id)

@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: int, db: AsyncSession = Depends(get_db)):
    status = await TaskService(db).get_task_status(task_id)
    return TaskStatusResponse(status=status)

@router.delete("/{task_id}", response_model=TaskStatusResponse)
async def cancel_task(task_id: int, db: AsyncSession = Depends(get_db)):
    task = await TaskService(db).cancel_task(task_id)
    return TaskStatusResponse(status=task.status)
