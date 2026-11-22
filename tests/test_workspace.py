import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from eon.service import EonService
from eon.vault import Vault
from test_eon import FakeProvider


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.s = EonService(provider_factory=FakeProvider, launcher=object())
        self.ident = self.s.chats.active_id

    def record(self, kind, name, instructions):
        key = "projects" if kind == "project" else "modes"
        old = set(self.s.snapshot()[key])
        result = self.s.library_action(kind, {"name": name, "instructions": instructions})
        return (set(result[key]) - old).pop()

    def test_projects_isolate_both_context_and_history(self):
        first = self.record("project", "A", "scope-alpha")
        second = self.record("project", "B", "scope-beta")
        mode = self.record("mode", "Test", "mode-guide")
        self.s.library_action("configure", {"id":self.ident, "project":first, "mode":mode})
        self.s.send("private-alpha")
        self.assertIn("scope-alpha", FakeProvider.latest_messages[0]["content"])
        self.assertIn("mode-guide", FakeProvider.latest_messages[0]["content"])
        other = self.s.new_chat()["active_chat_id"]
        self.s.library_action("configure", {"id":other, "project":second, "mode":"study"})
        self.s.send("private-beta")
        self.assertIn("scope-beta", FakeProvider.latest_messages[0]["content"])
        self.assertNotIn("alpha", str(FakeProvider.latest_messages))
        self.assertNotIn("mode-guide", str(FakeProvider.latest_messages))
        self.s.library_action("project", {"id":first, "name":"Renamed", "instructions":"updated"})
        self.s.library_action("project", {"id":first, "delete":True})
        self.s.library_action("mode", {"id":mode, "delete":True})
        snap = self.s.open_chat(self.ident)
        item = next(c for c in snap["conversations"] if c["id"] == self.ident)
        self.assertEqual((item["project"], item["mode"]), ("", "general"))
        self.assertEqual(snap["history"][0]["content"], "private-alpha")

    def test_project_move_blocked_during_generation(self):
        project = self.record("project", "A", "scope-alpha")
        def attempt_move():
            with self.assertRaises(ValueError):
                self.s.library_action("configure", {"id":self.ident, "project":project, "mode":"code"})
        self.s.generate(text="sample", ready=attempt_move)
        self.assertEqual(self.s.snapshot()["conversations"][0]["project"], "")

    def test_invalid_configuration_atomic(self):
        for payload in [{"id":self.ident, "project":"", "mode":"missing"},
                        {"id":self.ident, "project":[], "mode":"general"}]:
            with self.assertRaises(ValueError):
                self.s.library_action("configure", payload)
        with self.assertRaises(ValueError):
            self.s.library_action("mode", {"id":"code", "delete":True})
        with self.assertRaises(ValueError):
            self.s.library_action("look", {"theme":"bad"})

    def test_search_and_stars_follow_actual_messages(self):
        self.s.send("first")
        self.s.send("İçerikte ANAHTAR")
        revision = self.s.snapshot()["revision"]
        self.s.library_action("pin", {"id":self.ident,"on":True})
        self.s.library_action("star", {"id":self.ident,"index":2,"revision":revision,"on":True})
        self.assertEqual([h["index"] for h in self.s.search("",True)["results"]], [None,2])
        self.assertEqual(self.s.search("içerikte anahtar")["results"][0]["index"], 2)
        self.s.generate(text="changed", edit_index=0)
        self.assertEqual(self.s.snapshot()["stars"], [])
        self.assertFalse(self.s.search("anahtar")["results"])
        with self.assertRaises(ValueError):
            self.s.library_action("star", {"id":self.ident,"index":0,"revision":revision,"on":True})

    def test_no_model_requests_for_library_operations(self):
        with patch.object(FakeProvider, "chat", side_effect=AssertionError):
            self.record("project", "A", "a")
            self.s.library_action("pin", {"id":self.ident,"on":True})
            self.s.search("test")
            self.s.library_action("look", {"theme":"light","accent":"mint","reduced":True,"compact":True})

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI")
    def test_v010_vault_upgrade_and_reopen(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "library.dpapi"
            vault = Vault(path)
            vault.open()
            history = [{"role":"user","content":"legacy marker"},{"role":"assistant","content":"ok"}]
            vault.save({"chats":{"active":"old","items":[["old","Original",history]]},
                        "memory":{"m":"old note"}, "instructions":"old preferences",
                        "settings":vars(self.s.settings), "style":"normal"})
            vault.close()
            before = path.read_bytes()
            def start():
                return EonService(provider_factory=FakeProvider, launcher=object(), vault_path=path)
            service = start()
            try:
                self.assertEqual(before, path.read_bytes())
                initial = service.snapshot()
                self.assertEqual(initial["history"], history)
                self.assertEqual(initial["conversations"][0]["mode"], "general")
                service.library_action("pin", {"id":"old","on":True})
                service.library_action("star", {"id":"old","index":0,"on":True,"revision":0})
                service.library_action("project", {"name":"project marker","instructions":"local"})
                self.assertNotIn(b"project marker",path.read_bytes())
            finally:
                service.vault.close()
            again = start()
            try:
                data = again.snapshot()
                self.assertEqual(data["history"], history)
                self.assertEqual(data["instructions"], "old preferences")
                self.assertEqual(data["memory"], {"m":"old note"})
                self.assertTrue(data["conversations"][0]["pinned"])
                self.assertEqual(data["stars"], [0])
                self.assertEqual(len(data["projects"]), 1)
            finally:
                again.vault.close()

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI")
    def test_unknown_schema_never_overwrites_existing_vault(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "library.dpapi"
            vault = Vault(path)
            vault.open()
            vault.save({"schema":99})
            vault.close()
            before = path.read_bytes()
            service = EonService(launcher=object(), vault_path=path)
            self.assertIsNone(service.vault)
            service.new_chat()
            self.assertEqual(path.read_bytes(), before)
