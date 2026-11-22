import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eon.service import EonService
from eon.weather import forecast
from test_eon import FakeProvider


class Stream(FakeProvider):
    def stream(self, messages, emit, job):
        FakeProvider.latest_messages = messages
        emit("bir")
        emit(" iki")


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.s = EonService(provider_factory=Stream, launcher=object())

    def test_stop_discards_partial_answer(self):
        with self.assertRaisesRegex(ValueError, "durduruldu"):
            self.s.generate(text="Merhaba", key="example", emit=lambda _: self.s.cancel("example"))
        self.assertFalse(self.s.session.history())
        self.assertEqual(self.s.send("again")["message"], Stream.response)

    def test_stream_stays_with_original_chat(self):
        ident = self.s.chats.active_id
        self.s.generate(text="first", emit=lambda _: None, ready=self.s.new_chat)
        self.assertFalse(self.s.session.history())
        self.assertEqual(self.s.open_chat(ident)["history"][1]["content"], "bir iki")

    def test_deleted_chat_cannot_receive_completion(self):
        ident = self.s.chats.active_id
        with self.assertRaises(ValueError):
            self.s.generate(text="first", emit=lambda _: None, ready=lambda: self.s.delete_chat(ident))
        self.assertFalse(self.s.session.history())

    def test_edit_replaces_branch_after_success(self):
        self.s.send("one")
        self.s.send("two")
        self.s.generate(text="edited", edit_index=0, emit=lambda _: None)
        self.assertEqual([m["content"] for m in self.s.session.history()], ["edited", "bir iki"])
        with self.assertRaises(ValueError):
            self.s.generate(text="bad", edit_index=1)

    def test_context_budget_preserves_recent_pairs(self):
        for i in range(12):
            self.s.session.remember_turn(str(i), "x" * 1100)
        self.s.send("next")
        messages = FakeProvider.latest_messages
        self.assertLess(sum(len(m["content"]) for m in messages), 8000)
        self.assertEqual(messages[-3]["content"], "11")

    def test_explicit_memory_only(self):
        self.s.send("hello")
        self.assertFalse(self.s.memory)
        self.s.memory_edit("", "test note")
        ident = next(iter(self.s.memory))
        self.s.memory_edit(ident, "updated note")
        self.s.send("hello")
        self.assertIn("updated note", FakeProvider.latest_messages[0]["content"])
        self.s.memory_edit(ident, None)
        self.assertFalse(self.s.memory)

    def test_invalid_preferences_atomic(self):
        with self.assertRaises(ValueError):
            self.s.preferences("test", 600, 700)
        self.assertEqual(self.s.instructions, "")

    def test_no_weather_network_without_permission_or_coordinates(self):
        with patch("eon.weather.HTTPSConnection") as connection:
            for values in [(False, 0, 0), ("yes", 0, 0), (True, float("nan"), 0), (True, None, 42)]:
                with self.assertRaises(ValueError):
                    forecast(*values)
            connection.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI")
    def test_encrypted_restart_lock_and_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "vault"
            def start():
                return EonService(provider_factory=Stream, launcher=object(), vault_path=path)
            first = start()
            self.assertIsNotNone(first.vault)
            first.send("synthetic-private-marker")
            first.memory_edit("", "private note")
            self.assertNotIn(b"synthetic-private-marker", path.read_bytes())
            self.assertIsNone(start().vault)
            first.vault.close()
            second = start()
            self.assertEqual(second.session.history()[0]["content"], "synthetic-private-marker")
            self.assertIn("private note", second.memory.values())
            second.vault.close()
            path.write_bytes(b"damaged")
            third = start()
            self.assertIsNone(third.vault)
            third.send("new content")
            self.assertEqual(path.read_bytes(), b"damaged")
