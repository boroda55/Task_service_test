import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager
from app.db.models.task import Status, Task
from app.worker import _process_task, handle_message


@pytest.mark.asyncio
@patch("app.worker.async_session")
async def test_process_task_success(mock_async_session, task_factory):
    mock_session = AsyncMock()
    mock_task = task_factory(status=Status.NEW, id=1)
    mock_session.get.return_value = mock_task
    mock_async_session.return_value.__aenter__.return_value = mock_session

    await _process_task(1)

    assert mock_task.status == Status.COMPLETED
    assert mock_session.commit.call_count >= 2


@pytest.mark.asyncio
@patch("app.worker.async_session")
async def test_process_task_not_found(mock_async_session):
    mock_session = AsyncMock()
    mock_session.get.return_value = None
    mock_async_session.return_value.__aenter__.return_value = mock_session

    await _process_task(999)

    mock_session.get.assert_called_once_with(Task, 999)
    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
@patch("app.worker.async_session")
async def test_process_task_idempotency_guard(mock_async_session, task_factory):
    mock_session = AsyncMock()
    mock_task = task_factory(status=Status.COMPLETED, id=2)
    mock_session.get.return_value = mock_task
    mock_async_session.return_value.__aenter__.return_value = mock_session

    await _process_task(2)

    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_invalid_body():
    # Создаем правильный async context manager для message.process()
    @asynccontextmanager
    async def mock_process(*args, **kwargs):
        yield None

    msg = MagicMock()
    msg.body = b"not_an_integer"
    msg.process = mock_process

    with patch("app.worker._process_task") as mock_process_task:
        await handle_message(msg)
        mock_process_task.assert_not_called()


@pytest.mark.asyncio
async def test_handle_message_valid_body():
    @asynccontextmanager
    async def mock_process(*args, **kwargs):
        yield None

    msg = MagicMock()
    msg.body = b"42"
    msg.process = mock_process

    with patch("app.worker._process_task") as mock_process_task:
        await handle_message(msg)
        mock_process_task.assert_called_once_with(42)