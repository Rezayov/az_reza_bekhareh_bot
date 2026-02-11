from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from .config import settings


class FoodCodeCipher:
    """Encrypts and decrypts food codes with Fernet."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key)

    def encrypt(self, value: str) -> bytes:
        return self._fernet.encrypt(value.encode("utf-8"))

    def decrypt(self, token: bytes) -> str:
        try:
            return self._fernet.decrypt(token).decode("utf-8")
        except InvalidToken as exc:  # pragma: no cover - defensive
            raise ValueError("رمز کد غذا نامعتبر است.") from exc


cipher = FoodCodeCipher(settings.fernet_key)

