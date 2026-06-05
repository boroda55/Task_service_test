import pytest
from httpx import Response
from app.db.models.task import Priority, Status

class TestTasksAPI:
    async def test_create_task_success(self, async_client, mock_queue):
        payload = {"title": "API Task", "priority": "HIGH"}
        response = await async_client.post("/api/v1/tasks", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "API Task"
        assert data["status"] == "NEW"
        mock_queue.publish.assert_called_once_with(data["id"])

    async def test_get_task_not_found(self, async_client):
        response = await async_client.get("/api/v1/tasks/99999")
        assert response.status_code == 404

    async def test_list_tasks_pagination(self, async_client, test_session, task_factory):
        for i in range(10):
            test_session.add(task_factory(title=f"Page {i}"))
        await test_session.commit()
        response = await async_client.get("/api/v1/tasks?page=2&per_page=3")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["items"]) == 3

    async def test_cancel_task_success(self, async_client, test_session, task_factory):
        task = task_factory(status=Status.NEW)
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        response = await async_client.delete(f"/api/v1/tasks/{task.id}")
        assert response.status_code == 200
        assert response.json()["status"] == "CANCELLED"

    async def test_health_endpoint(self, async_client):
        response = await async_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
