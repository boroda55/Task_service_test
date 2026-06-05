from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from app.db.models.task import Priority, Status, Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate

class TaskService:
    def __init__(self, session: AsyncSession):
        self.repo = TaskRepository(session)
        self.session = session

    async def create_task(self, data: TaskCreate) -> Task:
        task = await self.repo.create(data)
        await self.session.commit()
        return task

    async def get_task(self, task_id: int) -> Task:
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise HTTPException(HTTP_404_NOT_FOUND, "Задача не найдена")
        return task

    async def list_tasks(self, status: Status | None, priority: Priority | None, page: int, per_page: int):
        offset = (page - 1) * per_page
        items, total = await self.repo.list_tasks(status, priority, offset, per_page)
        return items, total

    async def cancel_task(self, task_id: int) -> Task:
        task = await self.get_task(task_id)
        if task.status in (Status.COMPLETED, Status.FAILED, Status.CANCELLED):
            raise HTTPException(HTTP_400_BAD_REQUEST, f"Нельзя отменить задачу в статусе {task.status.value}")
        task.status = Status.CANCELLED
        task.finished_at = datetime.now(timezone.utc)
        await self.session.commit()
        return task

    async def get_task_status(self, task_id: int) -> Status:
        task = await self.get_task(task_id)
        return task.status
