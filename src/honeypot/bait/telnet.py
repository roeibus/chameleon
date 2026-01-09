import asyncio
import docker
import logging
import itertools
from typing import List, Dict, Any, Optional, Iterator, TypedDict, Union
from docker.models.containers import Container


# --- TYPE DEFINITIONS ---
class NodeConfig(TypedDict):
    """Schema for the initial configuration of a node."""
    base_url: Optional[str]
    name: str


class ActiveNode(TypedDict):
    """Schema for a live, connected node in our pool."""
    client: docker.DockerClient
    name: str


# --- CONFIGURATION ---
LISTEN_HOST: str = '0.0.0.0'
LISTEN_PORT: int = 2323
IMAGE_NAME: str = "chameleon-victim"

# Configuration List
NODE_CONFIGS: List[NodeConfig] = [
    {'base_url': None, 'name': 'Local-Node'},
    # {'base_url': 'tcp://192.168.1.50:2375', 'name': 'London-Node'},
]

# Global state for active connections
active_clients: List[ActiveNode] = []

# --- INITIALIZATION ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')


def init_docker_swarm() -> None:
    """Initializes connections to all defined Docker nodes."""
    for config in NODE_CONFIGS:
        try:
            cli: docker.DockerClient

            if config['base_url'] is None:
                # Use from_env() for local
                cli = docker.from_env()
            else:
                # Use custom config for remote
                cli = docker.DockerClient(base_url=config['base_url'])

            # Test connection (ping)
            cli.ping()
            logging.info(f"[✓] Connected to {config['name']}")

            # Add to the pool of active nodes
            node_entry: ActiveNode = {'client': cli, 'name': config['name']}
            active_clients.append(node_entry)

            # Ensure the image exists on this node
            try:
                cli.images.get(IMAGE_NAME)
            except docker.errors.ImageNotFound:
                logging.info(f"    Building image on {config['name']}...")
                cli.images.build(path=".", tag=IMAGE_NAME)

        except Exception as e:
            logging.error(f"[X] Failed to connect to {config['name']}: {e}")

    if not active_clients:
        logging.critical("No Docker nodes available! Exiting.")
        exit(1)


# Create an infinite iterator to cycle through nodes (Round-Robin)
# We initialize this as None and populate it in main() to ensure active_clients is full
node_cycle: Iterator[ActiveNode] = iter([])


# --- HANDLER ---
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    addr: tuple = writer.get_extra_info('peername')

    # Select the next available node
    node: ActiveNode = next(node_cycle)
    client: docker.DockerClient = node['client']
    node_name: str = node['name']

    logging.info(f"[+] New Connection from {addr} -> Routing to {node_name}")

    try:
        # --- PHASE 1: FAKE LOGIN ---
        writer.write(b"Ubuntu 20.04 LTS\r\nlogin: ")
        await writer.drain()
        await reader.readline()  # Username
        writer.write(b"Password: ")
        await writer.drain()
        await reader.readline()  # Password
        await asyncio.sleep(1)
        writer.write(b"\r\nWelcome to Ubuntu.\r\n\r\n")
        await writer.drain()

        # --- PHASE 2: REMOTE SPAWNING ---
        container: Container = client.containers.run(
            IMAGE_NAME,
            detach=True,
            tty=True,
            stdin_open=True
        )

        try:
            # Attach to the specific node's container socket
            # The docker socket type is technically a socket object, but strict typing
            # for the underlying socket requires internal classes. 'Any' is safe here.
            docker_socket: Any = container.attach_socket(
                params={'stdin': 1, 'stdout': 1, 'stderr': 1, 'stream': 1}
            )

            loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

            async def forward_input() -> None:
                while True:
                    data: bytes = await reader.read(1024)
                    if not data: break
                    docker_socket._sock.send(data)

            async def forward_output() -> None:
                while True:
                    data: bytes = await loop.run_in_executor(None, docker_socket._sock.recv, 1024)
                    if not data: break
                    writer.write(data)
                    await writer.drain()

            await asyncio.gather(forward_input(), forward_output())

        except Exception as e:
            logging.error(f"Bridge error on {node_name}: {e}")
        finally:
            logging.info(f"[-] Cleanup on {node_name} for {addr}")
            container.kill()
            container.remove()

    except Exception as e:
        logging.error(f"Connection error: {e}")
    finally:
        writer.close()


async def main() -> None:
    global node_cycle
    init_docker_swarm()

    # Initialize the cycle iterator now that active_clients is populated
    node_cycle = itertools.cycle(active_clients)

    server = await asyncio.start_server(handle_client, LISTEN_HOST, LISTEN_PORT)
    logging.info(f"[*] Distributed Orchestrator listening on {LISTEN_HOST}:{LISTEN_PORT}")
    async with server:
        await server.serve_forever()


if __name__ == '__main__':
    asyncio.run(main())