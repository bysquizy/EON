import base64
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import urlopen, Request

from eon.credentials import secret
from eon.gemini import Gemini
from eon.provider import LocalModelError
from eon.server import start_server
from eon.service import EonService, Generation
from eon.vault import Vault
from test_eon import FakeProvider


class Response(io.BytesIO):
    status = 200


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.conn = Mock()
        self.client = Gemini("synthetic-credential", "models/gemini-fixture", factory=lambda *a,**kw:self.conn)
        self.messages = [{"role":"system","content":"test"}, {"role":"user","content":"hello"}]

    def test_stream_transport_and_header_only_secret(self):
        data = {"candidates":[{"content":{"parts":[{"text":"hidden","thought":True},{"text":"ok"}]}, "finishReason":"STOP"}]}
        self.conn.getresponse.return_value = Response(b"data: "+json.dumps(data).encode()+b"\n\n")
        out = []
        self.client.stream(self.messages,out.append,Generation())
        self.assertEqual(out,["ok"])
        _, path, body, headers = self.conn.request.call_args.args
        self.assertNotIn(self.client.key,path)
        self.assertNotIn(self.client.key.encode(),body)
        self.assertEqual(headers["x-goog-api-key"],self.client.key)
        self.assertEqual(json.loads(body)["contents"][0]["role"],"user")
        self.conn.close.assert_called_once()

    def test_incomplete_response_not_committed(self):
        self.conn.getresponse.return_value = Response(b"data: {}\n")
        with self.assertRaises(LocalModelError):
            self.client.stream(self.messages,lambda _:None,Generation())

    def test_statuses_never_echo_secret(self):
        for status in (302,400,401,403,429,503):
            reply = Response(self.client.key.encode())
            reply.status = status
            self.conn.getresponse.return_value = reply
            with self.assertRaises(LocalModelError) as err:
                self.client.models()
            self.assertNotIn(self.client.key,str(err.exception))

    def test_model_discovery_filters_supported_methods(self):
        data={"models":[{"name":"models/gemini-fixture","supportedGenerationMethods":["generateContent"]},
                        {"name":"models/gemini-other","supportedGenerationMethods":["embedContent"]}]}
        self.conn.getresponse.return_value=Response(json.dumps(data).encode())
        self.assertEqual(self.client.models(),["models/gemini-fixture"])


class HybridTests(unittest.TestCase):
    def setUp(self):
        self.s = EonService(provider_factory=FakeProvider,launcher=Mock())
        self.s.launcher.list_apps.return_value=[{"id":"test"}]

    def test_cloud_isolation_and_no_silent_transfer(self):
        original=self.s.chats.active_id
        self.s.send("private local message")
        self.s.instructions="secret-preference"
        self.s.memory_edit("","secret-note")
        self.s.cloud_models=["models/gemini-fixture"]
        with self.assertRaises(ValueError):
            self.s.cloud_chat(self.s.cloud_models[0], original, True)
        with self.assertRaises(ValueError):
            self.s.cloud_chat(self.s.cloud_models[0], None, False)
        self.s.cloud_chat(self.s.cloud_models[0],None,True)
        self.s.library_action("project",{"name":"project","instructions":"secret-project"})
        ident=self.s.chats.active_id
        self.s.library_action("configure",{"id":ident,"project":next(iter(self.s.workspace.projects)),"mode":"code"})
        with patch("eon.service.secret",return_value="synthetic-key"), patch("eon.service.Gemini") as cloud:
            cloud.return_value.stream.side_effect=lambda msgs,emit,job:emit("ok")
            with self.assertRaises(ValueError):
                self.s.generate(text="send",destination="ollama")
            with patch.object(self.s,"_require_model",side_effect=AssertionError):
                self.s.generate(text="cloud user",destination=self.s.cloud_models[0])
            messages=cloud.return_value.stream.call_args.args[0]
            self.assertEqual(messages[-1]["content"],"cloud user")
            for marker in ("secret-", "private local message", "synthetic-key"):
                self.assertNotIn(marker,str(messages))
            self.assertNotIn("synthetic-key",str(self.s.snapshot()))
            self.s.cloud_allowed.clear()
            with self.assertRaises(ValueError):
                self.s.generate(text="no consent")

    def test_local_model_cache_and_refresh(self):
        with patch.object(FakeProvider,"installed_models",return_value=["model"]) as tags:
            self.s.models()
            self.s.models()
            self.s.models(refresh=True)
            self.assertEqual(tags.call_count,2)

    def test_unload_refused_during_generation(self):
        with self.s._generation_lock, self.assertRaises(ValueError):
            self.s.runtime_action("unload")
        with self.assertRaises(ValueError):
            self.s.runtime_action("keep","forever")

    def test_icon_raster_only_and_app_bound(self):
        for value in ["<svg/>",base64.b64encode(bytes(17)).decode(),"!"*12288]:
            with self.assertRaises(ValueError):
                self.s.save_icon("test",value)
        pixels=base64.b64encode(bytes(9216)).decode()
        self.assertEqual(self.s.save_icon("test",pixels)["apps"][0]["icon"],pixels)
        with self.assertRaises(ValueError):
            self.s.save_icon("unknown",pixels)
        self.assertFalse(self.s.save_icon("test",None)["apps"][0]["icon"])

    @unittest.skipUnless(os.name == "nt","Windows shortcut metadata")
    def test_local_shortcut_target_and_native_icon(self):
        import subprocess
        from eon.launcher import shortcut_executable
        from eon.icons import windows_pixels
        target = Path(os.environ["SystemRoot"])/"System32"/"notepad.exe"
        if not target.is_file():
            self.skipTest("Notepad fixture unavailable")
        with tempfile.TemporaryDirectory() as folder:
            link = Path(folder)/"example.lnk"
            exe = Path(os.environ["SystemRoot"])/"System32/WindowsPowerShell/v1.0/powershell.exe"
            script = ("[Console]::InputEncoding=[Text.UTF8Encoding]::new($false);"
                      "$p=[Console]::In.ReadToEnd()|ConvertFrom-Json;"
                      "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($p.link);"
                      "$s.TargetPath=$p.target;$s.Save()")
            subprocess.run([str(exe),"-NoProfile","-NonInteractive","-Command",script],
                           input=json.dumps({"link":str(link),"target":str(target)}), text=True,
                           capture_output=True,check=True,timeout=10)
            resolved = shortcut_executable(str(link))
            self.assertEqual(Path(resolved),target)
            self.assertEqual(len(base64.b64decode(windows_pixels(resolved))),9216)

    def test_cloud_sharing_is_scoped_and_opt_in(self):
        self.s.instructions="explicit-instructions"
        self.s.memory_edit("","explicit-note")
        self.s.cloud_models=["models/gemini-fixture"]
        self.s.cloud_chat(self.s.cloud_models[0],None,True,True,True)
        with patch("eon.service.secret",return_value="example"),patch("eon.service.Gemini") as cloud:
            cloud.return_value.stream.side_effect=lambda msgs,emit,job:emit("ok")
            self.s.generate(text="shared")
            prompt=cloud.return_value.stream.call_args.args[0][0]["content"]
            self.assertIn("explicit-note",prompt)
            self.assertIn("explicit-instructions",prompt)
            self.s.cloud_chat(self.s.cloud_models[0],None,True)
            self.s.generate(text="another")
            self.assertNotIn("explicit-",str(cloud.return_value.stream.call_args.args[0]))

    def test_weather_revocation_forgets_location(self):
        self.s.weather_settings({"enabled":True,"lat":40,"lon":30})
        self.s.weather_settings({"enabled":False})
        self.assertEqual(self.s.weather_pref,{"asked":True,"enabled":False})

    @unittest.skipUnless(os.name=="nt","Windows DPAPI")
    def test_v020_encrypted_rollback_and_separate_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"library.dpapi"
            v=Vault(path)
            v.open()
            self.s.send("old-message")
            v.save({"schema":2,"workspace":self.s.workspace.dump(),"chats":self.s.chats.dump(),
                    "settings":vars(self.s.settings),"memory":{"a":"old-note"},"style":"normal","instructions":"old"})
            v.close()
            before=path.read_bytes()
            service=EonService(launcher=Mock(),vault_path=path)
            try:
                self.assertEqual(service.session.history()[0]["content"],"old-message")
                self.assertEqual(before,path.read_bytes())
                secret(service.secret_path,"synthetic-key-example")
                service.new_chat()
                self.assertEqual(path.with_suffix(".pre-v030.dpapi").read_bytes(),before)
                self.assertEqual(secret(service.secret_path),"synthetic-key-example")
                self.assertNotIn("synthetic-key-example",str(service.snapshot()))
            finally:
                service.vault.close()
            v=Vault(path)
            data=v.open()
            v.close()
            self.assertEqual(data["memory"],{"a":"old-note"})
            self.assertNotIn("synthetic-key-example",str(data))

    def test_private_get_requires_launch_access(self):
        import threading
        server=start_server(service=self.s)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            for route in ("bootstrap","state","apps","models"):
                with self.assertRaises(HTTPError) as error:
                    urlopen(server.origin+"/api/"+route,timeout=2)
                self.assertEqual(error.exception.code,403)
            req=Request(server.origin+"/api/state",headers={"X-EON-Access":server.access,"Sec-Fetch-Site":"cross-site"})
            with self.assertRaises(HTTPError) as error:
                urlopen(req,timeout=2)
            self.assertEqual(error.exception.code,403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
