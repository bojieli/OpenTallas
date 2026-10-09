"""Malformed externally written state must not stop unrelated fleet work."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import closure_loop as cl


class StateIsolationTests(unittest.TestCase):
    def test_malformed_records_are_preserved_and_healthy_jobs_remain_visible(self):
        with tempfile.TemporaryDirectory() as td, patch.object(cl, "STATE", Path(td)), \
                patch.object(cl, "_STATE_READ_WARNINGS", set()), patch.object(cl, "log") as log:
            directory = Path(td) / "jobs"
            directory.mkdir()
            bad = {
                "missing": json.dumps({"name": "missing", "spec": {}}),
                "partial": '{"name":',
                "array": '[]',
                "mismatch": json.dumps({"name": "another", "status": "RUNNING", "spec": {}}),
            }
            for name, raw in bad.items():
                (directory / (name + ".json")).write_text(raw)
            healthy = {"name": "healthy", "status": "RUNNING", "spec": {}}
            (directory / "healthy.json").write_text(json.dumps(healthy))
            self.assertEqual(cl.all_jobs(), [healthy])
            self.assertEqual(cl.all_jobs(), [healthy])
            self.assertEqual(log.call_count, len(bad))
            for name, raw in bad.items():
                self.assertEqual((directory / (name + ".json")).read_text(), raw)
            recovered = {"name": "missing", "status": "QUEUED", "spec": {}}
            (directory / "missing.json").write_text(json.dumps(recovered))
            self.assertEqual(cl.all_jobs(), [healthy, recovered])


if __name__ == "__main__":
    unittest.main()
