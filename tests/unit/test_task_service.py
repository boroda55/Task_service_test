import pytest
from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from app.db.models.task import Priority, Status
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService

class TestTaskService:
    async def test_create_task(self, test_session):
        service = TaskService(test_session)
        data = TaskCreate(title="New", priority=Priority.HIGH)
        task = await service.create_task(data)
        assert task.title == "New"
        assert task.priority == Priority.HIGH

    async def test_get_task_not_found(self, test_session):
        service = TaskService(test_session)
        with pytest.raises(HTTPException) as exc:
            await service.get_task(99999)
        assert exc.value.status_code == HTTP_404_NOT_FOUND

    async def test_cancel_task_already_completed(self, test_session, task_factory):
        service = TaskService(test_session)
        task = task_factory(status=Status.COMPLETED)
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        with pytest.raises(HTTPException) as exc:
            await service.cancel_task(task.id)
        assert exc.value.status_code == HTTP_400_BAD_REQUEST
