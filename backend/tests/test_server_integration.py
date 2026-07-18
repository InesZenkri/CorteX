import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from auditpipe import server


class ServerIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.data = root / "data"
        self.output = root / "output" / "findings.json"
        self.database = root / "output" / "evidence.json"
        self.patches = [
            patch.object(server, "DATA_DIR", self.data),
            patch.object(server, "OUT_PATH", self.output),
            patch.object(server, "DB_PATH", self.database),
        ]
        for item in self.patches:
            item.start()
        server._state.update({"status": "ready", "progress": 0, "error": None, "file_count": 0})
        self.client = TestClient(server.app)

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_upload_document_download_and_background_investigation(self):
        response = self.client.post("/api/upload", files=[
            ("files", ("CortexScope/Root/sub/evidence.txt", b"source evidence", "text/plain")),
            ("files", ("CortexScope/Root/ledger.csv", b"id,amount\n1,10", "text/csv")),
        ])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["files"], 2)
        self.assertTrue((self.data / "Root/sub/evidence.txt").exists())

        dossier_id = response.json()["dossierId"]
        documents = self.client.get(f"/api/dossiers/{dossier_id}/documents").json()
        self.assertEqual(len(documents), 2)
        downloaded = self.client.get(f"/api/documents/{documents[0]['id']}/file")
        self.assertEqual(downloaded.status_code, 200)

        report = {
            "generated_at": "test-generated-at",
            "model": "gpt-5.6",
            "llm_used": True,
            "model_attestation": {
                "required": True,
                "verified": True,
                "requested_model": "gpt-5.6",
                "response_models": ["gpt-5.6-sol"],
                "calls": [{
                    "response_id": "resp_test", "requested_model": "gpt-5.6",
                    "response_model": "gpt-5.6-sol",
                }],
            },
            "summary": {"confirmed": 0, "leads": 0, "cleared": 0, "profit_overstatement_eur": 0, "profit_overstatement_vs_tolerance": "within"},
            "findings": [], "cleared_decoys": [],
        }

        def fake_pipeline(_config, use_llm=True, progress=None):
            if progress:
                progress(95, "Test synthesis")
            self.output.parent.mkdir(parents=True, exist_ok=True)
            self.output.write_text(json.dumps(report), encoding="utf-8")
            return report

        with patch.object(server, "run_pipeline", fake_pipeline):
            refused = self.client.post("/api/investigate", json={"use_llm": False})
            self.assertEqual(refused.status_code, 422)
            started = self.client.post("/api/investigate")
            self.assertEqual(started.status_code, 200)
            for _ in range(50):
                status = self.client.get("/api/investigation/summary").json()
                if status["dossier_status"] == "ready" and status["progress"] == 100:
                    break
                time.sleep(0.01)
            else:
                self.fail("background investigation did not complete")


if __name__ == "__main__":
    unittest.main()
