"""Friday Python SDK — Custom Exceptions."""


class FridayError(Exception):
    """Base exception for all Friday SDK errors."""

    pass


class FridayConnectionError(FridayError):
    """Raised when the client fails to connect to the Friday server or times out."""

    pass


class FridayAuthenticationError(FridayError):
    """Raised when the API key is missing, invalid, or unauthorized (HTTP 401)."""

    pass


class FridayNotFoundError(FridayError):
    """Raised when a requested resource is not found (HTTP 404)."""

    pass


class FridayAPIError(FridayError):
    """Raised when the Friday API returns an unexpected error response."""

    def __init__(self, message: str, status_code: int = 500, response_text: str = ""):
        super().__init__(f"[{status_code}] {message}: {response_text}".strip())
        self.status_code = status_code
        self.response_text = response_text
