
import asyncio
import signal
from contextlib import AsyncExitStack

from loguru import logger

from honeypot.core.bridge import ProtocolServer
from honeypot.utils.race_group import RaceGroup

_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 30.0


class HoneypotRunner:
    def __init__(self, servers: list[ProtocolServer]) -> None:
        self._servers: list[ProtocolServer] = servers
        self._stop: asyncio.Event = asyncio.Event()

    def stop(self) -> None:
        """Signal the runner to shut down (used by tests and signal handlers)."""
        self._stop.set()

    async def _run_server(self, server: asyncio.Server) -> None:
        """Race serve_forever against the stop event."""
        async with RaceGroup() as rg:
            rg.append_task(server.serve_forever())
            rg.append_task(self._stop.wait())

    async def _backoff(
        self,
        srv: ProtocolServer,
        server: asyncio.Server | None,
        exc: Exception,
        delay: float,
    ) -> float:
        """Log crash, release the server port, and wait out the backoff delay.
        Returns the next delay to use. The caller should check ``_stop`` after
        this returns, since a stop signal during the wait is not re-raised.
        """
        logger.error(
            f"[!] {srv.protocol} server error: {exc}; retrying in {delay:.0f}s"
        )
        if server is not None:
            server.close()  # release port before retrying
            await server.wait_closed()
        try:
            await asyncio.wait_for(self._stop.wait(), timeout=delay)
        except TimeoutError:
            return min(delay * 2, _MAX_BACKOFF)
        return delay  # stop was signaled; caller will exit on next loop check

    async def _supervise(self, srv: ProtocolServer, stack: AsyncExitStack) -> None:
        """Supervise a single protocol server with exponential-backoff restart.

        If ``srv.start()`` returns ``None`` the protocol manages its own
        lifecycle (e.g. SSH) and this coroutine exits without looping.
        """
        delay = _INITIAL_BACKOFF
        while not self._stop.is_set():
            try:
                server = await srv.start(stack)
            except Exception as e:
                if self._stop.is_set():
                    return
                delay = await self._backoff(srv, None, e, delay)
                continue
            if server is None:
                return  # Protocol manages its own lifecycle (e.g. SSH)
            try:
                await self._run_server(server)
                delay = _INITIAL_BACKOFF  # reset backoff after clean exit
            except Exception as e:
                if self._stop.is_set():
                    return
                delay = await self._backoff(srv, server, e, delay)


    async def run(self, stack: AsyncExitStack) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self._stop.set)

        async with asyncio.TaskGroup() as tg:
            for srv in self._servers:
                tg.create_task(self._supervise(srv, stack))
