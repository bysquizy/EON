import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from eon.credentials import secret
from eon.gemini import Gemini
from eon.provider import LocalModelError
from eon.service import EonService
from test_eon import FakeProvider


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.service = EonService(provider_factory=FakeProvider, launcher=Mock())

    def test_key_formats_are_verified_after_write(self):
        import os
        if os.name != "nt":
            self.skipTest("Windows DPAPI")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "secret.dpapi"
            for value in ("synthetic-standard_A1", "synthetic.auth.key.1"):
                secret(path, value)
                self.assertEqual(secret(path), value)
                self.assertNotIn(value.encode(),path.read_bytes())
            with self.assertRaises(ValueError):
                secret(path, "invalid-key\r\nsynthetic")

    def test_transport_errors_are_distinct_and_redacted(self):
        import socket
        import ssl
        for failure, label in [(socket.gaierror("private"),"DNS"),
                               (ssl.SSLError("private"),"TLS"), (TimeoutError("private"),"zaman")]:
            connection=Mock()
            connection.connect.side_effect=failure
            with self.assertRaisesRegex(LocalModelError,label) as error:
                Gemini("synthetic",factory=lambda *a,**k:connection).models()
            self.assertNotIn("private",str(error.exception))

    def test_project_selected_memory_only(self):
        service=self.service
        service.memory_edit("", "note visible only by selection")
        note=next(iter(service.memory))
        service.library_action("project",{"name":"A","instructions":"Project A"})
        project=next(iter(service.workspace.projects))
        ident=service.chats.active_id
        service.library_action("configure",{"id":ident,"project":project,"mode":"general"})
        service.send("one")
        self.assertNotIn("note visible",FakeProvider.latest_messages[0]["content"])
        service.extra_action({"kind":"project","id":project,"mode":"code","model":"","notes":[note]})
        service.send("two")
        self.assertIn("note visible",FakeProvider.latest_messages[0]["content"])

    def test_delete_and_undo_restore_transcript(self):
        service=self.service
        service.send("first")
        service.send("second")
        original=service.session.history()
        ident=service.chats.active_id
        service.extra_action({"kind":"delete_message","id":ident,"index":1,"revision":2})
        self.assertEqual(service.session.history(),original[2:])
        service.extra_action({"kind":"undo","id":ident})
        self.assertEqual(service.session.history(),original)

    def test_restore_swaps_memory_only_after_successful_encrypted_write(self):
        service=self.service
        service.send("first")
        backup=json.loads(json.dumps(service.backup_data()))
        service.send("second")
        service.vault=Mock()
        service.vault.save.side_effect=OSError
        with self.assertRaises(ValueError):
            service.restore_data(backup)
        self.assertEqual(len(service.session.history()),4)
        bad={**backup,"memory":{"x":[]}}
        with self.assertRaises(ValueError):
            service.restore_data(bad)
        service.vault.save.side_effect=None
        service.restore_data(backup)
        self.assertEqual(len(service.session.history()),2)
        self.assertFalse(service.cloud_allowed)

    def test_weather_cache_is_cleared_when_consent_is_removed(self):
        s=self.service
        s.weather_settings({"enabled":True,"lat":41,"lon":29})
        with patch("eon.weather.forecast",return_value={"label":"sample data"}):
            s.weather_report(True)
        self.assertEqual(s.weather_pref["last"],"sample data")
        s.weather_settings({"enabled":False})
        self.assertNotIn("last",s.weather_pref)
