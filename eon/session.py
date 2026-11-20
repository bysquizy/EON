"""Kalıcı olmayan konuşma geçmişi. Disk üzerinde veri saklanmaz."""
from dataclasses import dataclass, field
from .config import SYSTEM_PROMPT

@dataclass
class VolatileSession:
    max_turns: int = 6
    _history: list[dict[str, str]] = field(default_factory=list)

    def messages_for(self, user_text: str) -> list[dict[str, str]]:
        if not 0 < len(user_text.strip()) <= 2500:
            raise ValueError("Mesaj 1–2500 karakter arasında olmalı.")
        history = self._history[-2 * self.max_turns:]
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
            {"role": "user", "content": user_text.strip()}
        ]

    def remember_turn(self, user_text: str, assistant_text: str) -> None:
        self._history += [
            {"role": "user", "content": user_text.strip()},
            {"role": "assistant", "content": assistant_text.strip()},
        ]
        self._history = self._history[-2 * self.max_turns:]

    def clear(self) -> None:
        self._history.clear()
