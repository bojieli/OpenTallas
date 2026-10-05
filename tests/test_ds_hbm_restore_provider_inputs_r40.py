import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/ds_hbm_restore_provider_inputs_r40.py"

class ReplayInputs(unittest.TestCase):
    def test_missing_restore_and_immutable_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            target = base / "input.bin"
            payload = b"source-bound-input"
            inventory = {"files": [{"path": str(target), "tar_member": "inputs/input.bin", "bytes": len(payload), "expected_sha256": hashlib.sha256(payload).hexdigest()}]}
            (base / "input_inventory.json").write_text(json.dumps(inventory))
            with tarfile.open(base / "provider-inputs.tar", "w") as tar:
                member = tarfile.TarInfo("inputs/input.bin")
                member.size = len(payload)
                tar.addfile(member, io.BytesIO(payload))
            pins = {name: {"sha256": hashlib.sha256((base/name).read_bytes()).hexdigest()} for name in ("input_inventory.json", "provider-inputs.tar")}
            (base / "archive_sha256.json").write_text(json.dumps(pins))
            def run(*extra):
                return subprocess.run([sys.executable, str(TOOL), "--package", str(base), *extra], capture_output=True, text=True)
            self.assertNotEqual(run().returncode, 0)
            self.assertFalse(target.exists())
            self.assertEqual(run("--restore").returncode, 0)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(run().returncode, 0)
            target.write_bytes(b"unique conflicting evidence")
            self.assertNotEqual(run("--restore").returncode, 0)
            self.assertEqual(target.read_bytes(), b"unique conflicting evidence")
            (base / "provider-inputs.tar").write_bytes(b"corrupt")
            self.assertNotEqual(run("--restore").returncode, 0)
            self.assertEqual(target.read_bytes(), b"unique conflicting evidence")

if __name__ == "__main__":
    unittest.main()
