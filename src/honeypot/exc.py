# --- Backend Exceptions ---


class BackendPropertyError(RuntimeError):
    """Raised when an invalid property access or assignment is made on a backend container."""

    pass


# --- Container Exceptions ---


class ContainerNotInitializedError(Exception):
    """Raised when the inner container is accessed before it has been initialized."""

    pass
