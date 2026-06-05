import pytest
from app.db.models.task import Priority, Status, Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate

class TestTaskRepository:
    async def test_create_task(self, test_session):
        repo = TaskRepository(test_session)
        data = TaskCreate(title="New Task", priority=Priority.HIGH)
        task = await repo.create(data)
        assert task.id is not None
        assert task.title == "New Task"
        assert task.priority == Priority.HIGH

    async def test_get_by_id_not_found(self, test_session):
        repo = TaskRepository(test_session)
        result = await repo.get_by_id(99999)
        assert result is None

    async def test_list_tasks_with_filters_and_pagination(self, test_session):
        repo = TaskRepository(test_session)
        for i in range(5):
            test_session.add(Task(
                title=f"Task {i}",
                priority=Priority.HIGH if i % 2 == 0 else Priority.LOW,
                status=Status.NEW if i < 3 else Status.COMPLETED
            ))
        await test_session.commit()

        items, total = await repo.list_tasks(status=Status.NEW, priority=None, offset=0, limit=10)
        assert total == 3
        assert len(items) == 3
        assert all(t.status == Status.NEW for t in items)
