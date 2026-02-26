import asyncio
from asyncio import Task
from collections.abc import Coroutine
from types import TracebackType
from typing import Any

from loguru import logger

# async taskgroup won't work here because
# we also need to cancel all tasks if they are successful


class RaceGroup:
    def __init__(self) -> None:
        self.tasks: list[Task[Any]] = []  # pyright: ignore[reportExplicitAny]

    def create_task(
        self, coro: Coroutine[Any, Any, Any]  # pyright: ignore[reportExplicitAny]
    ) -> None:
        task = asyncio.create_task(coro)
        self.tasks.append(task)

    async def __aenter__(self) -> "RaceGroup":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_val:
            for task in self.tasks:
                if not task.done():
                    accepted = task.cancel()
                    status = "accepted" if accepted else "already done"
                    logger.debug(f"Cancel request for task {task.get_name()}: {status}")
            return

        if not self.tasks:
            return

        done, pending = await asyncio.wait(
            self.tasks, return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            accepted = task.cancel()
            status = "accepted" if accepted else "already done"
            logger.debug(f"Cancel request for task {task.get_name()}: {status}")
            try:
                await task
            except asyncio.CancelledError:
                pass

        for task in done:
            exc = task.exception()
            if exc:
                raise exc
