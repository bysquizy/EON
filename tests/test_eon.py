import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from eon.config import LocalSettings, OUTPUT_LIMITS, valid_model
from eon.provider import LocalModelError, LocalOllama
from eon.session import VolatileSession
from eon.service import EonService
from eon.tools import ToolError, calculate
from eon.launcher import ApplicationRegistry, LaunchError, safe_launch_path, shortcut_search_directories
from eon.server import start_server


class MockResponse:
    def __init__(self, body=None, status=200):
        self.status = status
        self.body = body or {"message": {"content": "Merhaba!"}}

    def read(self, size):
        return json.dumps(self.body).encode('utf-8')


class MockConnection:
    last = None
    response = MockResponse()
    def __init__(self, host, port, timeout):
        self.host, self.port = host, port
        MockConnection.last = self
    def request(self, method, path, body=None, headers=None):
        self.requested = (method, path, body)
    def getresponse(self):
        return MockConnection.response
    def close(self):
        pass


class FakeProvider:
    response = "EON yanıtı"
    models = ["qwen3:4b-instruct", "llama3.2:3b"]
    latest_messages = []
    calls = 0
    def __init__(self, settings):
        self.settings = settings
    def installed_models(self):
        return list(self.models)
    def chat(self, messages):
        FakeProvider.calls += 1
        FakeProvider.latest_messages = list(messages)
        return self.response


class ProviderTests(unittest.TestCase):
    def setUp(self):
        MockConnection.response = MockResponse()

    def test_local_connection_only(self):
        p = LocalOllama(LocalSettings(), connection_factory=MockConnection)
        self.assertEqual(p.chat([{"role": "user", "content": "merhaba"}]), "Merhaba!")
        self.assertEqual((MockConnection.last.host, MockConnection.last.port), ("127.0.0.1", 11434))
        self.assertEqual(MockConnection.last.requested[:2], ("POST", "/api/chat"))
        self.assertEqual(json.loads(MockConnection.last.requested[2])["think"], False)

    def test_reject_cloud_tag(self):
        self.assertFalse(valid_model("qwen3:cloud"))
        self.assertFalse(valid_model("model:LOUDcloud"))
        with self.assertRaises(ValueError): LocalSettings(model="qwen3:cloud")

    def test_reject_remote_url(self):
        with self.assertRaises(ValueError): LocalSettings(model="https://example.com/model")

    def test_accept_other_installed_model(self):
        self.assertTrue(valid_model("my-model:latest"))

    def test_filter_remote_and_cloud_metadata(self):
        MockConnection.response = MockResponse({"models": [
            {"name": "qwen3:4b-instruct"},
            {"name": "bad:cloud"},
            {"name": "remote:latest", "remote_host": "https://example.org"},
            {"name": "other:latest", "remote_model": "abc"},
            {"name": "llama3.2:3b"},
        ]})
        p = LocalOllama(LocalSettings(), connection_factory=MockConnection)
        self.assertEqual(p.installed_models(), ["llama3.2:3b", "qwen3:4b-instruct"])

    def test_route_blocked(self):
        p = LocalOllama(LocalSettings(), connection_factory=MockConnection)
        with self.assertRaises(LocalModelError): p._call("POST", "/api/pull", {})

    def test_redirect_blocked(self):
        MockConnection.response = MockResponse(status=302)
        p = LocalOllama(LocalSettings(), connection_factory=MockConnection)
        with self.assertRaises(LocalModelError): p.chat([])

    def test_oversized_request(self):
        p = LocalOllama(LocalSettings(), connection_factory=MockConnection)
        with self.assertRaises(LocalModelError): p.chat([{"role": "user", "content": "x" * 80000}])

    def test_invalid_settings(self):
        with self.assertRaises(ValueError): LocalSettings(context_tokens=100)
        with self.assertRaises(ValueError): LocalSettings(output_tokens=3000)


class SessionTests(unittest.TestCase):
    def test_memory_recent_only(self):
        s = VolatileSession(max_turns=2)
        for i in range(4): s.remember_turn(f"u{i}", f"a{i}")
        self.assertEqual(len(s.history()), 8)  # Full session remains available in RAM.
        self.assertEqual(s.messages_for('next')[-1]['content'], 'next')
        self.assertNotIn('u0', [x['content'] for x in s.messages_for('next')])
        s.clear()
        self.assertEqual(s.history(), [])

    def test_regenerate_replaces_without_duplicate(self):
        s = VolatileSession()
        s.remember_turn('Hi', 'First')
        self.assertEqual(s.regeneration_messages()[-1], {"role": "user", "content": "Hi"})
        s.replace_last_assistant('Second')
        self.assertEqual(s.history(), [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Second"}])

    def test_regenerate_empty_denied(self):
        with self.assertRaises(ValueError): VolatileSession().regeneration_messages()

    def test_prompt_limit(self):
        with self.assertRaises(ValueError): VolatileSession().messages_for('x' * 2600)

    def test_style_prompt(self):
        self.assertIn('Çok kısa', VolatileSession().messages_for('Merhaba', 'kisa')[0]['content'])

    def test_calculator(self):
        self.assertEqual(calculate('2*(3+5)'), '16')
        self.assertEqual(calculate('1/4'), '0.25')

    def test_calculator_reject_code(self):
        with self.assertRaises(ToolError): calculate("__import__('os').system('cmd')")
        with self.assertRaises(ToolError): calculate('2**999999')
        with self.assertRaises(ToolError): calculate('1/0')


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.launcher = ApplicationRegistry(config_path=Path(self.temp.name)/"apps.json", platform="linux")
        FakeProvider.response = 'EON yanıtı'
        FakeProvider.models = ['qwen3:4b-instruct', 'llama3.2:3b']
        FakeProvider.calls = 0
        self.s = EonService(provider_factory=FakeProvider, launcher=self.launcher)

    def test_chat_keeps_history(self):
        r = self.s.send('Merhaba')
        self.assertEqual(r['message'], 'EON yanıtı')
        self.assertEqual(len(self.s.snapshot()['history']), 2)


    def test_chat_collection_create_open_delete(self):
        self.s.send('İlk konuşmam')
        first_id = self.s.snapshot()['active_chat_id']
        self.assertEqual(self.s.snapshot()['conversations'][0]['title'], 'İlk konuşmam')
        other = self.s.new_chat()['active_chat_id']
        self.assertNotEqual(other, first_id)
        self.assertEqual(self.s.snapshot()['history'], [])
        self.s.send('İkinci konuşmam')
        self.assertEqual(len(self.s.snapshot()['conversations']), 2)
        self.s.open_chat(first_id)
        self.assertEqual(self.s.snapshot()['history'][0]['content'], 'İlk konuşmam')
        self.s.delete_chat(first_id)
        self.assertEqual(self.s.snapshot()['active_chat_id'], other)
        self.assertEqual(self.s.snapshot()['history'][0]['content'], 'İkinci konuşmam')

    def test_invalid_chat_id_denied(self):
        with self.assertRaises(ValueError): self.s.open_chat('../../other')
        with self.assertRaises(ValueError): self.s.delete_chat('missing-id')

    def test_chat_collection_in_memory_only(self):
        self.s.send('İçerik bilgisayara yazılmamalı')
        # App launcher settings are the only persisted configuration at this stage.
        self.assertFalse((Path(self.temp.name)/'chats.json').exists())
        self.assertFalse((Path(self.temp.name)/'chats.db').exists())

    def test_settings_are_responsive_during_slow_model(self):
        started = threading.Event()
        release = threading.Event()
        class SlowProvider(FakeProvider):
            def chat(self, messages):
                started.set()
                release.wait(timeout=5)
                return 'Yanıt'
        self.s.provider_factory = SlowProvider
        thread = threading.Thread(target=lambda: self.s.send('Uzun model isteği'))
        thread.start()
        try:
            self.assertTrue(started.wait(2))
            import time
            t0 = time.monotonic()
            self.s.select_length('kisa')
            self.assertLess(time.monotonic()-t0, 1.0)
        finally:
            release.set()
            thread.join(timeout=3)
        self.assertFalse(thread.is_alive())

    def test_regenerate_does_not_add_pair(self):
        self.s.send('merhaba')
        FakeProvider.response = 'Yeni yanıt'
        self.s.regenerate()
        self.assertEqual(len(self.s.snapshot()['history']), 2)
        self.assertEqual(self.s.snapshot()['history'][-1]['content'], 'Yeni yanıt')
        self.assertEqual(self.s.snapshot()['stats']['regenerated'], 1)

    def test_summary_does_not_pollute_chat(self):
        self.s.send('Bana yardımcı ol')
        before = self.s.snapshot()['history']
        result = self.s.summary()
        self.assertEqual(result['summary'], 'EON yanıtı')
        self.assertEqual(before, self.s.snapshot()['history'])
        self.assertEqual(self.s.snapshot()['stats']['summaries'], 1)

    def test_empty_summary_denied(self):
        with self.assertRaises(ValueError): self.s.summary()

    def test_model_switch_installed_only(self):
        self.s.select_model('llama3.2:3b')
        self.assertEqual(self.s.snapshot()['model'], 'llama3.2:3b')
        with self.assertRaises(ValueError): self.s.select_model('unknown:latest')

    def test_model_switch_refuses_cloud(self):
        FakeProvider.models = ['qwen3:4b-instruct', 'other:cloud']
        with self.assertRaises(ValueError): self.s.select_model('other:cloud')

    def test_model_fallback(self):
        FakeProvider.models = ['llama3.2:3b']
        self.assertEqual(self.s.models()['selected'], 'llama3.2:3b')

    def test_length_switch(self):
        self.s.select_length('detayli')
        self.assertEqual(self.s.settings.output_tokens, OUTPUT_LIMITS['detayli'])
        with self.assertRaises(ValueError): self.s.select_length('infinite')

    def test_history_command(self):
        self.s.send('merhaba')
        self.assertIn('Sen: merhaba', self.s.command('/gecmis')['message'])

    def test_stats(self):
        self.s.send('test')
        self.assertEqual(self.s.snapshot()['stats']['messages'], 1)
        self.assertIn('Mesaj: 1', self.s.command('/istatistik')['message'])

    def test_clear_keeps_statistics(self):
        self.s.send('test')
        self.s.clear()
        self.assertEqual(self.s.snapshot()['history'], [])
        self.assertEqual(self.s.snapshot()['stats']['messages'], 1)

    def test_slash_commands(self):
        self.assertIn('gecmis', self.s.send('/yardim')['message'])
        self.assertEqual(self.s.send('/hesap 2*8')['message'], '16')
        self.assertEqual(self.s.send('/model llama3.2:3b')['state']['model'], 'llama3.2:3b')
        self.assertEqual(self.s.send('/uzunluk kisa')['state']['style'], 'kisa')

    def test_chat_does_not_launch_apps(self):
        self.s.send('Chrome aç')
        self.assertEqual(self.launcher.list_apps()[0]['id'], 'chrome')

    def test_user_message_length(self):
        with self.assertRaises(ValueError): self.s.send('x' * 2501)


class LauncherTests(unittest.TestCase):

    def test_desktop_shortcut_directories(self):
        env = {'USERPROFILE': r'Z:\ExampleProfile',
               'PUBLIC': r'Z:\ExamplePublic',
               'OneDrive': r'C:\OneDrive',
               'APPDATA': r'Z:\ExampleProfile\AppData\Roaming'}
        places = [str(x) for x in shortcut_search_directories(env)]
        self.assertTrue(any('Desktop' in place for place in places))
        self.assertTrue(any('OneDrive' in place for place in places))
        self.assertTrue(any('Start Menu' in place for place in places))
        self.assertEqual(len(places), len(set(places)))

    def test_desktop_shortcuts_are_detected(self):
        with tempfile.TemporaryDirectory() as d:
            desktop = Path(d) / 'Desktop'
            desktop.mkdir()
            (desktop / 'Notion.lnk').write_bytes(b'test-shortcut-placeholder')
            (desktop / 'Antigravity.lnk').write_bytes(b'test-shortcut-placeholder')
            (desktop / 'SOLIDWORKS.lnk').write_bytes(b'test-shortcut-placeholder')
            with patch('eon.launcher.shortcut_search_directories', return_value=[desktop]), \
                 patch('eon.launcher.safe_launch_path', side_effect=lambda path: path):
                registry = ApplicationRegistry(config_path=Path(d)/'apps.json', platform='win32')
            found = {entry['id']: entry for entry in registry.list_apps()}
            self.assertTrue(found['notion']['ready'])
            self.assertTrue(found['antigravity']['ready'])
            self.assertTrue(found['solidworks']['ready'])
            self.assertEqual(found['notion']['source'], 'found')

    def test_refuses_url_and_shell(self):
        for path in ('https://example.org/abc.exe', 'cmd /c calc.exe', r'\\server\share\x.exe',
                     r'C:\fake\run.bat', r'C:\fake\script.ps1'):
            with self.subTest(path=path):
                with self.assertRaises(LaunchError): safe_launch_path(path)

    def test_unconfigured_launch_denied(self):
        with tempfile.TemporaryDirectory() as d:
            # Isolate this test from real Start Menu / App Paths discovery.
            # Without this mock, a CI runner with Chrome installed could open it.
            with patch.object(ApplicationRegistry, 'refresh', return_value=None):
                apps = ApplicationRegistry(config_path=Path(d)/'apps.json', platform='win32')
            apps._discovered.clear()
            with self.assertRaises(LaunchError): apps.launch('chrome')

    def test_non_windows_denied(self):
        with tempfile.TemporaryDirectory() as d:
            apps = ApplicationRegistry(config_path=Path(d)/'apps.json', platform='linux')
            with self.assertRaises(LaunchError): apps.save('test', 'Test', 'x.exe')
            with self.assertRaises(LaunchError): apps.launch('chrome')

    def test_config_outside_repo_and_launch_with_no_shell(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'program.exe'
            path.write_bytes(b'')
            called = []
            apps = ApplicationRegistry(config_path=Path(d)/'apps.json', platform='win32',
                                       start_process=lambda *a, **k: called.append((a,k)))
            with patch('eon.launcher.safe_launch_path', return_value=str(path)):
                apps.save('myapp', 'My App', r'C:\Program Files\My App\program.exe')
                apps.launch('myapp')
            self.assertEqual(len(called), 1)
            self.assertEqual(called[0][0], ([str(path)],))
            self.assertEqual(called[0][1]['shell'], False)
            self.assertTrue((Path(d)/'apps.json').exists())

    def test_untrusted_id_refused(self):
        with tempfile.TemporaryDirectory() as d:
            apps = ApplicationRegistry(config_path=Path(d)/'apps.json', platform='win32')
            with self.assertRaises(LaunchError): apps.save('../../evil', 'Invalid', r'C:\app.exe')


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        reg = ApplicationRegistry(config_path=Path(cls.temp.name)/'apps.json', platform='linux')
        cls.service = EonService(provider_factory=FakeProvider, launcher=reg)
        cls.server = start_server(service=cls.service)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp.cleanup()

    def fetch(self, route, body=None, origin=None, token=None):
        headers = {"X-EON-Access":self.server.access}
        if body is not None:
            headers['Content-Type'] = 'application/json'
            if origin is not None: headers['Origin'] = origin
            if token is not None: headers['X-EON-Token'] = token
        req = Request(self.server.origin+route, data=json.dumps(body).encode() if body is not None else None,
                      headers=headers, method='POST' if body is not None else 'GET')
        return urlopen(req, timeout=5)

    def test_bootstrap(self):
        with self.fetch('/api/bootstrap') as response:
            data = json.loads(response.read())
            self.assertEqual(len(data['token']) > 20, True)
            self.assertEqual(data['state']['version'], '0.4.1')
            self.assertIn("connect-src 'self'", response.headers['Content-Security-Policy'])

    def test_html_rendered(self):
        with self.fetch('/') as response:
            text = response.read().decode('utf-8')
            self.assertIn('EON', text)
            self.assertIn('view-apps', text)
            self.assertNotIn('fonts.googleapis.com', text)

    def test_cross_origin_denied(self):
        token = json.loads(self.fetch('/api/bootstrap').read())['token']
        with self.assertRaises(HTTPError) as ex:
            self.fetch('/api/apps/launch', {'id':'chrome'}, origin='https://evil.example', token=token)
        self.assertEqual(ex.exception.code, 403)

    def test_library_endpoints_require_same_origin_and_token(self):
        for route in ("/api/search", "/api/library/project", "/api/library/star", "/api/library/look", "/api/backup/export", "/api/backup/restore"):
            with self.subTest(route=route):
                with self.assertRaises(HTTPError) as denied:
                    self.fetch(route, {}, origin=self.server.origin)
                self.assertEqual(denied.exception.code, 403)
                with self.assertRaises(HTTPError) as foreign:
                    self.fetch(route, {}, origin="https://example.invalid", token=self.server.token)
                self.assertEqual(foreign.exception.code, 403)

    def test_missing_token_denied(self):
        with self.assertRaises(HTTPError) as ex:
            self.fetch('/api/clear', {}, origin=self.server.origin)
        self.assertEqual(ex.exception.code, 403)

    def test_post_with_token(self):
        token = json.loads(self.fetch('/api/bootstrap').read())['token']
        with self.fetch('/api/message', {'text': 'Merhaba'}, origin=self.server.origin, token=token) as res:
            result = json.loads(res.read())
            self.assertEqual(result['message'], 'EON yanıtı')


    def test_chat_actions_and_health(self):
        token = json.loads(self.fetch('/api/bootstrap').read())['token']
        with self.fetch('/api/health') as response:
            self.assertEqual(json.loads(response.read())['status'], 'ok')
        def post(route, data):
            return json.loads(self.fetch(route, data, origin=self.server.origin, token=token).read())
        first = post('/api/chats/new', {})
        first_id = first['active_chat_id']
        post('/api/message', {'text': 'Birinci sohbet'})
        second = post('/api/chats/new', {})
        self.assertNotEqual(first_id, second['active_chat_id'])
        reopened = post('/api/chats/open', {'id': first_id})
        self.assertEqual(reopened['history'][0]['content'], 'Birinci sohbet')
        deleted = post('/api/chats/delete', {'id': first_id})
        self.assertNotEqual(deleted['active_chat_id'], first_id)
        with self.assertRaises(HTTPError) as ex:
            post('/api/chats/open', {'id': 'bad-id'})
        self.assertEqual(ex.exception.code, 400)

    def test_no_arbitrary_command_route(self):
        token = json.loads(self.fetch('/api/bootstrap').read())['token']
        with self.assertRaises(HTTPError) as ex:
            self.fetch('/api/shell', {'cmd': 'calc'}, origin=self.server.origin, token=token)
        self.assertEqual(ex.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
