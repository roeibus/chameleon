import asyncio
from asyncio import Task
from collections.abc import Coroutine, Iterable
from types import TracebackType
from typing import Any

# async taskgroup won't work here because
# we also need to cancel all tasks if they are successful


async def _cancel_tasks(
    tasks: Iterable[Task[Any]],  # pyright: ignore[reportExplicitAny]
) -> None:
    tasks = list(tasks)
    for task in tasks:
        _ = task.cancel()
    for task in tasks:
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass


class RaceGroup:
    def __init__(self) -> None:
        self.tasks: list[Task[Any]] = []  # pyright: ignore[reportExplicitAny]

    def create_task(
        self,
        coro: Coroutine[Any, Any, Any],  # pyright: ignore[reportExplicitAny]
    ) -> None:
        self.tasks.append(asyncio.create_task(coro))

    async def __aenter__(self) -> "RaceGroup":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_val or not self.tasks:
            await _cancel_tasks(self.tasks)
            return

        done, pending = await asyncio.wait(
            self.tasks, return_when=asyncio.FIRST_COMPLETED
        )

        await _cancel_tasks(pending)

        for task in done:
            if not task.cancelled():
                exc = task.exception()
                if exc:
                    raise exc
