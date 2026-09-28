"""Explicit backend selection; a missing remote credential fails closed."""

import os

from storage.local import LocalStorage
from storage.turso import TursoStorage


def from_environment(initialize: bool = False):
    """Create the selected backend without implicit remote schema changes."""
    backend = os.getenv("FRIDAY_STORAGE_BACKEND", "local")
    if backend == "local":
        return LocalStorage(os.environ["FRIDAY_LOCAL_DB"], initialize=initialize)
    if backend == "turso":
        return TursoStorage(
            os.environ["TURSO_DATABASE_URL"], os.environ["TURSO_AUTH_TOKEN"], initialize
        )
    raise ValueError("Unknown storage backend")
