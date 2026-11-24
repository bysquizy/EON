import base64
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from eon.actions import ActionCenter, ActionError, redact_text
from eon.gemini import Gemini
from eon.knowledge import KnowledgeBase, KnowledgeError, extract_document_sections
from eon.productivity import ProductivityCenter, system_memory_info, validate_vision_image
from eon.provider import LocalModelError
from eon.server import start_server
from eon.service import EonService, Generation
from eon.studio_gen import (
    StudioError,
    build_docx_bytes,
    build_pdf_bytes,
    build_xlsx_bytes,
    preview_studio_document,
    save_or_encode_studio_document,
)
from eon.vault import Vault
from test_eon import FakeProvider


def _make_valid_png(width=32, height=32) -> str:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr + b"\x00\x00\x00\x00"
    return base64.b64encode(raw).decode("ascii")


class Response(io.BytesIO):
    status = 200


class Release050Tests(unittest.TestCase):
    def setUp(self):
        self.s = EonService(provider_factory=FakeProvider, launcher=Mock())
        self.s.launcher.list_apps.return_value = [{"id": "notepad", "name": "Notepad", "ready": True, "path": r"C:\Windows\notepad.exe"}]

    def test_projects_2_0_and_knowledge_base_isolation(self):
        # Create two projects
        self.s.library_action("project", {"name": "AlphaProj", "instructions": "alpha-sys"})
        self.s.library_action("project", {"name": "BetaProj", "instructions": "beta-sys"})
        pids = {v["name"]: k for k, v in self.s.workspace.projects.items()}
        alpha_id, beta_id = pids["AlphaProj"], pids["BetaProj"]

        # Import DOCX into AlphaProj and XLSX into BetaProj
        docx_bytes = build_docx_bytes("Alpha Kılavuzu", "# Bölüm 1\nKuantum protokolü gizli kodu KRP-991.")
        xlsx_bytes = build_xlsx_bytes("Beta Tablo", "| Bütçe | Değer |\n| --- | --- |\n| BTP-772 | 4500 |")

        self.s.knowledge_action({
            "action": "import",
            "name": "alpha_guide.docx",
            "data": base64.b64encode(docx_bytes).decode("ascii"),
            "project": alpha_id,
        })
        self.s.knowledge_action({
            "action": "import",
            "name": "beta_budget.xlsx",
            "data": base64.b64encode(xlsx_bytes).decode("ascii"),
            "project": beta_id,
        })

        # Assign chat 1 to AlphaProj
        chat1 = self.s.chats.active_id
        self.s.library_action("configure", {"id": chat1, "project": alpha_id, "mode": "general"})
        res1 = self.s.generate(text="Kuantum protokolü KRP-991 nedir?")
        sys_prompt_1 = FakeProvider.latest_messages[0]["content"]
        self.assertIn("KRP-991", sys_prompt_1)
        self.assertIn("alpha_guide.docx", sys_prompt_1)
        self.assertNotIn("BTP-772", sys_prompt_1)
        self.assertEqual(res1["sources"][0]["title"], "alpha_guide.docx")

        # Assign chat 2 to BetaProj -> must never see AlphaProj docs
        chat2 = self.s.new_chat()["active_chat_id"]
        self.s.library_action("configure", {"id": chat2, "project": beta_id, "mode": "general"})
        self.s.generate(text="BTP-772 bütçe değeri nedir ve KRP-991 var mı?")
        sys_prompt_2 = FakeProvider.latest_messages[0]["content"]
        self.assertIn("BTP-772", sys_prompt_2)
        self.assertNotIn("KRP-991", sys_prompt_2)

    def test_pdf_csv_md_extraction_and_unsupported_rejection(self):
        pdf_bytes = build_pdf_bytes("Deneme PDF", "Bu bir PDF test satıridir. Sayfa verisi OMEGA-42.")
        sections = extract_document_sections("rapor.pdf", pdf_bytes)
        self.assertEqual(sections[0]["page"], 1)
        self.assertIn("OMEGA-42", sections[0]["text"])

        csv_sections = extract_document_sections("veri.csv", b"Ad,Puan\nAli,95\nAyse,98")
        self.assertIn("Ali | 95", csv_sections[0]["text"])

        with self.assertRaises(KnowledgeError):
            extract_document_sections("zararli.exe", b"MZ...")
        with self.assertRaises(KnowledgeError):
            extract_document_sections("bozuk.pdf", b"not-a-pdf")
        with self.assertRaises(KnowledgeError):
            extract_document_sections("xxe.docx", b"invalid-zip")

    def test_gemini_kb_sharing_respects_project_opt_in(self):
        model = "models/gemini-2.5-flash"
        self.s.cloud_models = [model]
        self.s.library_action("project", {"name": "CloudProj", "instructions": "cloud-proj-inst"})
        pid = next(iter(self.s.workspace.projects))
        self.s.knowledge.import_document(name="secret_local.md", raw=b"# Gizli\nBULUT_BELGE_VERISI_123", project=pid)

        self.s.cloud_chat(model, None, True, True, True)
        cid = self.s.chats.active_id
        self.s.library_action("configure", {"id": cid, "project": pid, "mode": "general"})

        # By default share_docs is False -> KB doc must NOT be sent to Gemini
        with patch("eon.service.secret", return_value="synthetic-key"), patch("eon.service.Gemini") as mock_gem:
            mock_gem.return_value.stream.side_effect = lambda msgs, emit, job: emit("yanıt")
            self.s.generate(text="BULUT_BELGE_VERISI_123 hakkında bilgi ver", destination=model)
            sent_prompt = mock_gem.return_value.stream.call_args.args[0][0]["content"]
            self.assertNotIn("BULUT_BELGE_VERISI_123", sent_prompt)

            # Now explicitly enable share_docs on project
            self.s.extra_action({"kind": "project", "id": pid, "share_docs": True})
            self.s.generate(text="BULUT_BELGE_VERISI_123 hakkında bilgi ver", destination=model)
            sent_prompt_2 = mock_gem.return_value.stream.call_args.args[0][0]["content"]
            self.assertIn("BULUT_BELGE_VERISI_123", sent_prompt_2)

    def test_actions_sandbox_preview_confirm_rollback_and_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            root.mkdir()
            outside = Path(tmp) / "outside.txt"
            outside.write_text("hidden", encoding="utf-8")

            self.s.action_center({"action": "add_folder", "path": str(root)})

            # Path traversal outside allowed folder must fail
            with self.assertRaises(ActionError):
                self.s.action_center({"action": "run", "skill": "read_file", "params": {"path": str(outside)}})
            with self.assertRaises(ActionError):
                self.s.action_center({"action": "run", "skill": "read_file", "params": {"path": "../outside.txt"}})
            # Dangerous executable/script extension must fail
            with self.assertRaises(ActionError):
                self.s.action_center({"action": "run", "skill": "write_text_file", "params": {"path": "hack.bat", "content": "calc.exe"}})
            with self.assertRaises(ActionError):
                self.s.action_center({"action": "run", "skill": "write_text_file", "params": {"path": "script.ps1", "content": "dir"}})

            # Write text file -> returns preview, does NOT write before confirmation
            preview_res = self.s.action_center({
                "action": "run",
                "skill": "write_text_file",
                "params": {"path": "notlar.md", "content": "# İlk Sürüm\nMerhaba"},
            })
            self.assertFalse(preview_res["executed"])
            self.assertTrue(preview_res["requires_confirmation"])
            target_file = root / "notlar.md"
            self.assertFalse(target_file.exists())

            # Confirm approval -> file is written
            token = preview_res["preview"]["token"]
            self.s.action_center({"action": "confirm", "token": token, "approve": True})
            self.assertTrue(target_file.exists())
            self.assertEqual(target_file.read_text(encoding="utf-8"), "# İlk Sürüm\nMerhaba")

            # Overwrite existing file -> confirm -> rollback restores original version
            p2 = self.s.action_center({
                "action": "run",
                "skill": "write_text_file",
                "params": {"path": "notlar.md", "content": "# İkinci Sürüm"},
            })
            self.s.action_center({"action": "confirm", "token": p2["preview"]["token"], "approve": True})
            self.assertEqual(target_file.read_text(encoding="utf-8"), "# İkinci Sürüm")

            self.s.action_center({"action": "rollback"})
            self.assertEqual(target_file.read_text(encoding="utf-8"), "# İlk Sürüm\nMerhaba")

            # Rename file -> confirm -> rollback
            p3 = self.s.action_center({
                "action": "run",
                "skill": "rename_file",
                "params": {"path": "notlar.md", "new_name": "arsiv.md"},
            })
            self.s.action_center({"action": "confirm", "token": p3["preview"]["token"], "approve": True})
            self.assertFalse(target_file.exists())
            self.assertTrue((root / "arsiv.md").exists())

            self.s.action_center({"action": "rollback"})
            self.assertTrue(target_file.exists())

            # Search and read file
            found = self.s.action_center({"action": "run", "skill": "search_files", "params": {"query": "*.md"}})
            self.assertEqual(len(found["matches"]), 1)
            read_res = self.s.action_center({"action": "run", "skill": "read_file", "params": {"path": "notlar.md"}})
            self.assertIn("İlk Sürüm", read_res["content"])

            # Verify audit log redacts secrets
            fake_sk = "sk-" + "proj1234567890abcdef"
            redacted = redact_text(f"Hata anahtarı: AIzaSyD-1234567890abcdefghijk ve {fake_sk}")
            self.assertNotIn("AIzaSyD", redacted)
            self.assertNotIn("proj123456", redacted)

    def test_studio_document_generation_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.s.action_center({"action": "add_folder", "path": str(root)})

            for fmt in ("docx", "pdf", "xlsx", "csv", "md", "txt"):
                prev = self.s.studio_action({
                    "action": "preview",
                    "title": "Test Raporu",
                    "content": "| Kategori | Değer |\n| --- | --- |\n| Alpha | 120 |\n| Beta | 240 |",
                    "format": fmt,
                    "folder": str(root),
                })
                self.assertEqual(prev["preview"]["format"], fmt)
                with self.assertRaises(StudioError):
                    save_or_encode_studio_document("Test", "İçerik", fmt, confirm=False)

                gen = self.s.studio_action({
                    "action": "generate",
                    "title": "Test Raporu",
                    "content": "| Kategori | Değer |\n| --- | --- |\n| Alpha | 120 |\n| Beta | 240 |",
                    "format": fmt,
                    "folder": str(root),
                    "confirm": True,
                })
                saved = Path(gen["saved_path"])
                self.assertTrue(saved.is_file())
                # Verify generated DOCX/XLSX/PDF/CSV/MD/TXT can be parsed back by KnowledgeBase
                parsed = extract_document_sections(saved.name, saved.read_bytes())
                self.assertTrue(any("Alpha" in s["text"] for s in parsed))

    def test_gemini_research_grounding_usage_and_thought_signatures(self):
        conn = Mock()
        client = Gemini("synthetic-key", "models/gemini-2.5-flash", output=1024,
                        factory=lambda *a, **kw: conn, profile="deep", search=True)
        sse_event = {
            "candidates": [{
                "content": {
                    "parts": [
                        {"text": "internal reasoning", "thought": True, "thoughtSignature": "sig-xyz-987"},
                        {"text": "Araştırma sonucu bulundu."},
                    ]
                },
                "groundingMetadata": {
                    "webSearchQueries": ["eon Nedir"],
                    "groundingChunks": [
                        {"web": {"uri": "https://ai.google.dev/gemini-api/docs", "title": "Gemini API Docs"}}
                    ],
                },
                "finishReason": "STOP",
            }],
            "usageMetadata": {
                "promptTokenCount": 42,
                "candidatesTokenCount": 18,
                "thoughtsTokenCount": 10,
                "totalTokenCount": 70,
            },
        }
        conn.getresponse.return_value = Response(b"data: " + json.dumps(sse_event).encode("utf-8") + b"\n\n")
        chunks = []
        client.stream([{"role": "system", "content": "sys"}, {"role": "user", "content": "araştır"}], chunks.append, Generation())
        self.assertEqual(chunks, ["Araştırma sonucu bulundu."])
        self.assertEqual(client.usage["input_tokens"], 42)
        self.assertEqual(client.usage["output_tokens"], 18)
        self.assertTrue(client.usage["measured"])
        self.assertEqual(client.sources[0]["uri"], "https://ai.google.dev/gemini-api/docs")
        self.assertEqual(client.raw_parts[0]["thoughtSignature"], "sig-xyz-987")
        _, _, req_body, _ = conn.request.call_args.args
        sent_json = json.loads(req_body)
        self.assertIn({"googleSearch": {}}, sent_json["tools"])

        # Ollama must refuse live web research mode rather than pretending to search the web
        with self.assertRaisesRegex(ValueError, "yalnızca onaylı Gemini"):
            self.s.generate(text="webde ara", research=True)

    def test_memory_2_0_metadata_and_conflict_detection(self):
        res1 = self.s.memory_edit("", "Programlama dili: Python", category="tercih", source="kullanıcı")
        self.assertNotIn("memory_conflict", res1)
        mid = next(iter(self.s.memory))
        self.assertEqual(self.s.memory_meta[mid]["category"], "tercih")

        # Conflicting note with same key must return memory_conflict without silently overwriting
        res2 = self.s.memory_edit("", "Programlama dili: Rust", category="tercih", source="kullanıcı")
        self.assertIn("memory_conflict", res2)
        self.assertEqual(len(self.s.memory), 1)
        self.assertEqual(self.s.memory[mid], "Programlama dili: Python")

        # User resolves conflict by replacing existing record
        self.s.memory_edit("", "Programlama dili: Rust", category="tercih", replace_id=mid, force=True)
        self.assertEqual(list(self.s.memory.values()), ["Programlama dili: Rust"])

    def test_vision_image_validation_and_non_vision_model_guard(self):
        b64_png = _make_valid_png(48, 48)
        info = validate_vision_image("image/png", b64_png)
        self.assertEqual((info["width"], info["height"]), (48, 48))

        with self.assertRaises(ValueError):
            validate_vision_image("image/svg+xml", base64.b64encode(b"<svg/>").decode())
        with self.assertRaises(ValueError):
            validate_vision_image("image/png", base64.b64encode(b"not-a-png-header-at-all-123456").decode())

        # Non-vision local model rejects images with helpful explanation
        class NonVisionProvider(FakeProvider):
            def capabilities(self, model_name=None):
                return {"vision": False}
        self.s.provider_factory = NonVisionProvider
        with self.assertRaisesRegex(ValueError, "görsel analizini"):
            self.s.generate(text="Bu resmi açıkla", images=[{"mime": "image/png", "data": b64_png}])

        # Vision-capable local model receives images
        class VisionProvider(FakeProvider):
            def capabilities(self, model_name=None):
                return {"vision": True}
        self.s.provider_factory = VisionProvider
        self.s.generate(text="Bu grafikte ne var?", images=[{"mime": "image/png", "data": b64_png}])
        self.assertEqual(FakeProvider.latest_messages[-1]["images"], [b64_png])

    def test_focus_tasks_and_ics_roundtrip(self):
        self.s.productivity_action({"action": "add_task", "title": "Tez literatür taraması", "due": "2026-12-01"})
        self.s.productivity_action({"action": "log_focus", "minutes": 25, "label": "Okuma"})
        snap = self.s.snapshot()["productivity"]
        self.assertEqual(snap["total_tasks"], 1)
        self.assertEqual(snap["today_focus_minutes"], 25)

        ics_text = self.s.productivity_action({"action": "export_ics"})["ics"]
        self.assertIn("BEGIN:VCALENDAR", ics_text)
        self.assertIn("Tez literatür taraması", ics_text)

        prod2 = ProductivityCenter()
        imported = prod2.import_ics(ics_text)
        self.assertEqual(imported, 1)

    def test_command_center_health_and_privacy_redacted_metrics(self):
        self.s.send("Gizli kullanıcı sorusu SECRET_PROMPT_999")
        status = self.s.runtime_action("status")
        self.assertEqual(status["version"], "0.6.2")
        self.assertIn("system_memory", status)
        # Request log must NEVER contain prompt or assistant text
        log_dump = json.dumps(status["request_log"])
        self.assertNotIn("SECRET_PROMPT_999", log_dump)
        self.assertNotIn("EON yanıtı", log_dump)

    def test_built_in_natural_neural_voice_engine_and_prosody_cleaner(self):
        from eon.productivity import clean_speech_text
        cleaned = clean_speech_text("# Başlık\nMerhaba **dünya**! ```python\nprint(1)\n``` [Link](https://example.com)")
        self.assertNotIn("**", cleaned)
        self.assertNotIn("https://", cleaned)
        self.assertIn("Merhaba dünya!", cleaned)

        cfg = self.s.voice_action({"action": "configure", "voice": "tr-TR-EmelNeural"})
        self.assertEqual(cfg["voice_state"]["selected"], "tr-TR-EmelNeural")
        with self.assertRaises(ValueError):
            self.s.voice_action({"action": "configure", "voice": "invalid-voice"})

        spoken = self.s.voice_action({"action": "speak", "text": "Merhaba EON doğal ses!", "voice": "tr-TR-EmelNeural"})
        self.assertEqual(spoken["engine"], "browser_natural")
        self.assertEqual(spoken["voice"], "tr-TR-EmelNeural")
        self.assertIn("Merhaba EON doğal ses!", spoken["cleaned_text"])

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI")
    def test_v041_vault_migration_creates_pre_v050_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "library.dpapi"
            v = Vault(path)
            v.open()
            v041_payload = {
                "schema": 3,
                "cloud_chats": {},
                "weather": {"asked": False, "enabled": False},
                "metrics": {},
                "icons": {},
                "workspace": self.s.workspace.dump(),
                "chats": self.s.chats.dump(),
                "memory": {"m1": "eski v041 notu"},
                "instructions": "eski yönerge",
                "settings": vars(self.s.settings),
                "style": "normal",
                "extras": self.s.extras,
            }
            v.save(v041_payload)
            v.close()
            raw_before = path.read_bytes()

            svc = EonService(provider_factory=FakeProvider, launcher=Mock(), vault_path=path)
            try:
                self.assertEqual(svc.memory["m1"], "eski v041 notu")
                svc.productivity_action({"action": "add_task", "title": "Yeni v050 görevi"})
                backup_file = path.with_suffix(".pre-v050.dpapi")
                self.assertTrue(backup_file.exists())
                self.assertEqual(backup_file.read_bytes(), raw_before)
                # Import knowledge doc and verify separate knowledge.dpapi is written
                svc.knowledge_action({
                    "action": "import",
                    "name": "ayri_kasa.md",
                    "data": base64.b64encode(b"# Ayri Kasa\nKASA_AYRISTIRMA_TESTI_77").decode("ascii"),
                    "project": "",
                })
                kb_file = path.with_name("knowledge.dpapi")
                self.assertTrue(kb_file.exists())
                self.assertNotIn(b"KASA_AYRISTIRMA_TESTI_77", kb_file.read_bytes())
            finally:
                if svc.vault:
                    svc.vault.close()

            reopened = EonService(provider_factory=FakeProvider, launcher=Mock(), vault_path=path)
            try:
                hits = reopened.knowledge_action({"action": "search", "query": "KASA_AYRISTIRMA_TESTI_77", "project": ""})["results"]
                self.assertEqual(len(hits), 1)
                chunk = reopened.knowledge_action({"action": "get_chunk", "doc_id": hits[0]["doc_id"], "chunk_index": 0})["chunk"]
                self.assertIn("KASA_AYRISTIRMA_TESTI_77", chunk["text"])
            finally:
                if reopened.vault:
                    reopened.vault.close()

    def test_turkish_pdf_encoding_batch_folder_import_and_inline_action_card(self):
        # 1. Verify Turkish characters (ğ, Ğ, ş, Ş, ı, İ, ö, Ö, ç, Ç, ü, Ü) survive PDF build + extraction
        tr_text = "Türkçe karakter testi: ğĞşŞıİöÖçÇüÜ ve Tablo:\n| Kalem | Değer |\n| --- | --- |\n| Ölçüm | 145 |"
        pdf_raw = build_pdf_bytes("Türkçe Başlık ŞĞİ", tr_text)
        extracted = extract_document_sections("turkce.pdf", pdf_raw)
        self.assertIn("ğĞşŞıİöÖçÇüÜ", extracted[0]["text"])
        self.assertIn(b"/Differences", pdf_raw)

        # 2. Verify batch folder import & inline chat action proposal card
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "belge1.md").write_text("# Belge 1\nTOPLU_AKTARIM_VERISI_1", encoding="utf-8")
            (root / "belge2.txt").write_text("TOPLU_AKTARIM_VERISI_2", encoding="utf-8")
            self.s.action_center({"action": "add_folder", "path": str(root)})

            batch = self.s.knowledge_action({"action": "import_folder", "folder": str(root), "project": ""})
            self.assertEqual(batch["imported"], 2)

            # Inline action card proposal when user asks to save output to a file
            res = self.s.generate(text="Bu özeti rapor_ozeti.md dosyasına kaydet")
            cid = res["state"]["active_chat_id"]
            cards = res["state"]["chat_action_cards"]
            self.assertTrue(len(cards) >= 1)
            card = next(iter(cards.values()))
            self.assertEqual(card["skill"], "write_text_file")
            self.assertFalse((root / "rapor_ozeti.md").exists())
            # Confirm card token -> file is written
            self.s.action_center({"action": "confirm", "token": card["token"], "approve": True})
            self.assertTrue((root / "rapor_ozeti.md").exists())


if __name__ == "__main__":
    unittest.main()
