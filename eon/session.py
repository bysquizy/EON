"""In-memory conversation; never writes conversation content to disk."""
from dataclasses import dataclass, field
from .config import SYSTEM_PROMPT, STYLE_GUIDANCE


@dataclass
class VolatileSession:
    max_turns: int = 12
    _history: list[dict[str, str]] = field(default_factory=list)

    def messages_for(self, user_text: str, style: str = "normal") -> list[dict[str, str]]:
        if not isinstance(user_text, str) or not 0 < len(user_text.strip()) <= 2500:
            raise ValueError("Mesaj 1–2500 karakter arasında olmalı.")
        if style not in STYLE_GUIDANCE:
            raise ValueError("Yanıt modu geçersiz.")
        return [{"role": "system", "content": SYSTEM_PROMPT + " " + STYLE_GUIDANCE[style]},
                *self._history[-2 * self.max_turns:],
                {"role": "user", "content": user_text.strip()}]

    def remember_turn(self, user_text: str, assistant_text: str) -> None:
        self._history.extend([
            {"role": "user", "content": user_text.strip()},
            {"role": "assistant", "content": assistant_text.strip()},
        ])

    def history(self) -> list[dict[str, str]]:
        return [dict(message) for message in self._history]

    def last_user_message(self) -> str | None:
        if len(self._history) < 2:
            return None
        return self._history[-2]["content"]

    def regeneration_messages(self, style: str = "normal") -> list[dict[str, str]]:
        user = self.last_user_message()
        if user is None:
            raise ValueError("Yenilenecek yanıt yok.")
        if style not in STYLE_GUIDANCE:
            raise ValueError("Yanıt modu geçersiz.")
        return [{"role": "system", "content": SYSTEM_PROMPT + " " + STYLE_GUIDANCE[style]},
                *self._history[:-1][-(2 * self.max_turns + 1):]]

    def replace_last_assistant(self, text: str) -> None:
        if len(self._history) < 2 or self._history[-1]["role"] != "assistant":
            raise ValueError("Yenilenecek yanıt yok.")
        self._history[-1] = {"role": "assistant", "content": text.strip()}

    def clear(self) -> None:
        self._history.clear()


class ConversationCollection:
    """Multiple titled chats in memory only; no unencrypted disk history."""

    def __init__(self, max_chats: int = 40):
        import secrets
        self.max_chats = max_chats
        self._items = {}
        self.active_id = ""
        self.new()

    def new(self) -> str:
        import secrets
        if len(self._items) >= self.max_chats:
            raise ValueError("Sohbet sınırına ulaşıldı. Kullanılmayan bir sohbeti sil.")
        ident = secrets.token_urlsafe(9)
        self._items[ident] = {"title": "Yeni sohbet", "session": VolatileSession()}
        self.active_id = ident
        return ident

    def current(self) -> VolatileSession:
        return self._items[self.active_id]["session"]

    def rename_from_first_message(self, ident: str, text: str) -> None:
        item = self._items[ident]
        if item["title"] == "Yeni sohbet":
            item["title"] = text.strip().replace("\n", " ")[:55] or "Yeni sohbet"

    def list(self) -> list[dict]:
        return [
            {"id": ident, "title": item["title"],
             "message_count": len(item["session"].history()) // 2}
            for ident, item in reversed(list(self._items.items()))
        ]

    def open(self, ident: str) -> None:
        if not isinstance(ident, str) or ident not in self._items:
            raise ValueError("Sohbet bulunamadı.")
        self.active_id = ident

    def delete(self, ident: str) -> None:
        if not isinstance(ident, str) or ident not in self._items:
            raise ValueError("Sohbet bulunamadı.")
        del self._items[ident]
        if not self._items:
            self.new()
        elif self.active_id == ident:
            self.active_id = next(reversed(self._items))

    def clear_current(self) -> None:
        self.current().clear()
