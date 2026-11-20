import json
import unittest
from unittest.mock import patch

from eon.config import LocalSettings
from eon.provider import LocalOllama
from eon.session import VolatileSession
from eon.tools import ToolError, calculate

class MockResponse:
    status = 200
    def read(self, length):
        return json.dumps({"message":{"role":"assistant","content":"Merhaba!"}}).encode()

class MockConnection:
    created_with = None
    calls = []
    def __init__(self, host, port, timeout):
        MockConnection.created_with = (host, port, timeout)
    def request(self, method, path, body=None, headers=None):
        MockConnection.calls.append((method, path, body))
    def getresponse(self):
        return MockResponse()
    def close(self):
        pass

class EonTests(unittest.TestCase):
    def test_cloud_model_refused(self):
        with self.assertRaises(ValueError):
            LocalSettings(model="qwen3:cloud")

    def test_remote_model_refused(self):
        with self.assertRaises(ValueError):
            LocalSettings(model="https://example.com/model")

    def test_fixed_loopback(self):
        llm = LocalOllama(LocalSettings(), connection_factory=MockConnection)
        reply = llm.chat([{"role":"user","content":"Merhaba"}])
        self.assertEqual(reply, "Merhaba!")
        self.assertEqual(MockConnection.created_with[:2], ("127.0.0.1", 11434))
        self.assertEqual(MockConnection.calls[-1][1], "/api/chat")
        self.assertEqual(json.loads(MockConnection.calls[-1][2])["model"], "qwen3:4b-instruct")

    def test_session_only_recent_turns(self):
        s = VolatileSession(max_turns=2)
        for i in range(4):
            s.remember_turn(f"u{i}", f"a{i}")
        m = s.messages_for("yeni")
        self.assertEqual(len(m), 6)
        self.assertNotIn("u0", [x["content"] for x in m])
        s.clear()
        self.assertEqual(len(s.messages_for("yeni")), 2)

    def test_calculator(self):
        self.assertEqual(calculate("2*(3+5)"), "16")
        self.assertEqual(calculate("1/4"), "0.25")

    def test_calculator_rejects_code(self):
        with self.assertRaises(ToolError):
            calculate("__import__('os').system('whoami')")

    def test_calculator_rejects_large_power(self):
        with self.assertRaises(ToolError):
            calculate("2**9999999")

    def test_long_prompt_rejected(self):
        with self.assertRaises(ValueError):
            VolatileSession().messages_for("x" * 3000)

if __name__ == "__main__":
    unittest.main()
