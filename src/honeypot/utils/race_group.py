import asyncio
from asyncio import Task
from types import TracebackType
from typing import Type, Coroutine, Any


# async taskgroup won't work here because
# we also need to cancel all tasks if they are successful

class RaceGroup:
    def __init__(self) -> None:
        self.tasks: list[Task[Any]] = []

    def create_task(self, coro: Coroutine[Any, Any, Any]) -> Task[Any]:
        task = asyncio.create_task(coro)
        self.tasks.append(task)
        return task

    async def __aenter__(self) -> "RaceGroup":
        return self

    async def __aexit__(
            self,
            exc_type: Type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None
    ) -> None:
        if exc_val:
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            return

        if not self.tasks:
            return

        done, pending = await asyncio.wait(
            self.tasks,
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        for task in done:
            exc = task.exception()
            if exc: raise exc
