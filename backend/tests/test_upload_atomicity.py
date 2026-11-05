import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from auditpipe import server


class UploadAtomicityTest(unittest.TestCase):
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

    def upload_valid_dossier(self):
        response = self.client.post("/api/upload", files=[
            ("files", ("Root/evidence.txt", b"keep me", "text/plain")),
        ])
        self.assertEqual(response.status_code, 200)
        return response

    def test_rejected_upload_keeps_existing_dossier(self):
        first = self.upload_valid_dossier()
        dossier_id = first.json()["dossierId"]

        rejected = self.client.post("/api/upload", files=[
            ("files", ("Root/../bad.txt", b"reject me", "text/plain")),
        ])
        self.assertEqual(rejected.status_code, 400)

        self.assertTrue((self.data / "evidence.txt").exists())
        self.assertEqual(server._count_files(), 1)
        documents = self.client.get(f"/api/dossiers/{dossier_id}/documents").json()
        self.assertEqual(len(documents), 1)

    def test_partially_invalid_upload_writes_nothing(self):
        self.upload_valid_dossier()

        rejected = self.client.post("/api/upload", files=[
            ("files", ("Root/new-ok.txt", b"new", "text/plain")),
            ("files", ("Root/../bad.txt", b"reject me", "text/plain")),
        ])
        self.assertEqual(rejected.status_code, 400)

        self.assertTrue((self.data / "evidence.txt").exists())
        self.assertFalse((self.data / "new-ok.txt").exists())
        self.assertEqual(server._count_files(), 1)

    def test_rejected_upload_keeps_previous_findings(self):
        self.upload_valid_dossier()
        self.output.parent.mkdir(parents=True, exist_ok=True)
        self.output.write_text("{}", encoding="utf-8")

        rejected = self.client.post("/api/upload", files=[
            ("files", ("Root/../bad.txt", b"reject me", "text/plain")),
        ])
        self.assertEqual(rejected.status_code, 400)
        self.assertTrue(self.output.exists())

    def test_valid_upload_still_replaces_dossier(self):
        self.upload_valid_dossier()
        second = self.client.post("/api/upload", files=[
            ("files", ("Root/replacement.txt", b"new dossier", "text/plain")),
        ])
        self.assertEqual(second.status_code, 200)
        self.assertFalse((self.data / "evidence.txt").exists())
        self.assertTrue((self.data / "replacement.txt").exists())
        self.assertEqual(server._count_files(), 1)


if __name__ == "__main__":
    unittest.main()
