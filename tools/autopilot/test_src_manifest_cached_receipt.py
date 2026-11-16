import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import src_manifest as SM


class CachedReceipt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        (self.repo / "tools").mkdir(parents=True)
        (self.repo / "tools/a.py").write_text("A=1\n")
        def git(*args):
            return subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                                  check=True, capture_output=True, text=True).stdout.strip()
        git("init", "-q")
        git("add", "tools/a.py")
        git("commit", "-qm", "fixture")
        self.sha = git("rev-parse", "HEAD")
        self.old_cache = SM.CACHE_DIR
        SM.CACHE_DIR = str(self.root / "cache")
        self.tree = self.root / "published"
        self.manifest = SM.build(str(self.repo), self.sha, None, ["tools"], str(self.tree), main_ref="")
        SM.publish(str(self.tree))
        self.hash = self.manifest["manifest_hash"]
        self.cache = Path(SM.CACHE_DIR) / (hashlib.md5(str(self.tree.resolve()).encode()).hexdigest() + ".json")

    def tearDown(self):
        SM.CACHE_DIR = self.old_cache
        self.tmp.cleanup()

    def test_reuses_completed_publish_without_hashing_payload(self):
        with patch.object(SM, "sha256_file", side_effect=AssertionError("payload must not be rehashed")):
            errs, info = SM.cached_receipt(str(self.tree), self.hash)
        self.assertEqual(errs, [])
        self.assertEqual((info["verdict"], info["main_sha"], info["manifest_hash"]), ("PASS", self.sha, self.hash))
        self.assertEqual(info["cache_path"], str(self.cache))
        self.assertGreater(info["cache_mtime_ns"], 0)
        self.assertEqual(len(info["cache_sha256"]), 64)

    def test_wrong_hash_and_missing_cache_refuse(self):
        self.assertTrue(SM.cached_receipt(str(self.tree), "f" * 64)[0])
        self.cache.unlink()
        self.assertTrue(SM.cached_receipt(str(self.tree), self.hash)[0])

    def test_never_published_tree_has_no_completed_receipt(self):
        fresh = self.root / "fresh"
        m = SM.build(str(self.repo), self.sha, None, ["tools"], str(fresh), main_ref="")
        errs, info = SM.cached_receipt(str(fresh), m["manifest_hash"])
        self.assertTrue(errs)
        self.assertTrue(any("CACHE MISS" in e for e in errs))

    def test_changed_inventory_refuses(self):
        self.tree.chmod(0o755)
        (self.tree / "extra").write_text("new")
        SM.make_ro(str(self.tree))
        errs, _ = SM.cached_receipt(str(self.tree), self.hash)
        self.assertTrue(any("stale" in e for e in errs))
        self.assertTrue(any("inventory" in e for e in errs))

    def test_writable_payload_refuses_even_when_signature_matches(self):
        payload = self.tree / "tools/a.py"
        payload.chmod(0o644)
        self.assertEqual(json.loads(self.cache.read_text())["sig"], SM.signature(str(self.tree)))
        errs, _ = SM.cached_receipt(str(self.tree), self.hash)
        self.assertTrue(any("writable tools/a.py" in e for e in errs))

    def test_shared_inode_refuses_even_when_signature_matches(self):
        os.link(self.tree / "tools/a.py", self.root / "outside_alias")
        self.assertEqual(json.loads(self.cache.read_text())["sig"], SM.signature(str(self.tree)))
        errs, _ = SM.cached_receipt(str(self.tree), self.hash)
        self.assertTrue(any("shared inode tools/a.py" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
