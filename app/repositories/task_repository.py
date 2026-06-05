from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.task import Priority, Status, Task
from app.schemas.task import TaskCreate

class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: TaskCreate) -> Task:
        task = Task(**data.model_dump())
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> Task | None:
        return await self.session.get(Task, task_id)

    async def list_tasks(self, status: Status | None, priority: Priority | None, offset: int, limit: int) -> tuple[list[Task], int]:
        query = select(Task)
        if status: query = query.where(Task.status == status)
        if priority: query = query.where(Task.priority == priority)
        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_q)).scalar_one()
        query = query.order_by(Task.created_at.desc()).offset(offset).limit(limit)
        rows = (await self.session.execute(query)).scalars().all()
        return list(rows), total

    async def update(self, task: Task) -> Task:
        await self.session.flush()
        await self.session.refresh(task)
        return task
