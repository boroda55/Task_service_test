import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.queue import TaskQueue


@pytest.mark.asyncio
@patch("app.services.queue.connect_robust")
async def test_queue_connect_and_publish(mock_connect):
    mock_conn = AsyncMock()
    mock_conn.is_closed = False
    mock_channel = AsyncMock()
    mock_exchange = AsyncMock()
    mock_queue = AsyncMock()

    mock_conn.channel.return_value = mock_channel
    mock_channel.declare_exchange.return_value = mock_exchange
    mock_channel.declare_queue.return_value = mock_queue
    mock_connect.return_value = mock_conn

    queue = TaskQueue()
    await queue.connect()

    mock_channel.declare_exchange.assert_called_once()

    await queue.publish(123)
    mock_exchange.publish.assert_called_once()

    await queue.close()
    mock_conn.close.assert_called_once()