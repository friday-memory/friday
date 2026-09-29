"""Direct remote libSQL access: no embedded replica or filesystem fallback."""

from storage.local import LocalStorage


class TursoStorage(LocalStorage):
    """Use the official libsql driver for remote authoritative transactions."""

    def __init__(
        self, url: str, token: str = "", initialize: bool = False, allow_local_fixture: bool = False
    ):
        if not url.startswith(("libsql://", "https://")) and not allow_local_fixture:
            raise ValueError("Turso requires a remote URL")
        if not token and not allow_local_fixture:
            raise ValueError("Turso token is required")
        self.url, self.token = url, token
        if initialize:
            self.migrate()

    def connect(self):
        """Open remote-only connection, or an explicitly authorized test fixture."""
        import libsql

        return (
            libsql.connect(database=self.url, auth_token=self.token)
            if self.token
            else libsql.connect(self.url)
        )
