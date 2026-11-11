#!/usr/bin/env python3
"""ot-autoclean KIT-INPUT-STORE-1 hunks: store links do not block a kit delete; class k = referenced-set retention"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("ot_autoclean_ks", os.path.join(HERE, "ot-autoclean.py"))
ac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ac)
sys.path.insert(0, os.path.join(HERE, "..", "autopilot"))
import kit_store as KS  # noqa: E402


class StoreLinks(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="acks_")
        self.store = os.path.join(self.t, "kit-store")
        src = os.path.join(self.t, "lane", "a", "b", "x.sv")
        os.makedirs(os.path.dirname(src))
        with open(src, "w") as f:
            f.write("module x; endmodule\n")
        self.src = src
        self.kit = os.path.join(self.t, "claude", "wave", "items", "t", "attempt_1")
        old = KS.SCAN_PREFIX, KS.SCRATCH_FLOOR_GB, KS.ROOT_FLOOR_GB
        KS.SCAN_PREFIX, KS.SCRATCH_FLOOR_GB, KS.ROOT_FLOOR_GB = os.path.join(self.t, "lane"), 0, 0
        self.addCleanup(lambda: setattr(KS, "SCAN_PREFIX", old[0]) or setattr(KS, "SCRATCH_FLOOR_GB", old[1])
                        or setattr(KS, "ROOT_FLOOR_GB", old[2]))
        self.man = KS.snapshot({"inputs": [{"role": "x", "path": src, "required": True}], "meta": {"die": "d"}},
                               self.kit + "/kit_inputs", self.store, log=lambda *a: None)
        ac._KS_MANIFESTS.clear()

    def tearDown(self):
        shutil.rmtree(self.t)

    def test_store_link_is_not_foreign(self):
        f = self.kit + "/kit_inputs" + self.src
        self.assertGreater(os.stat(f).st_nlink, 1)
        self.assertTrue(ac.store_linked(f))
        self.assertIsNone(ac.tree_info(self.kit)[2])
        other = self.kit + "/foreign.sv"
        os.link(self.src, other)                     # a real foreign hard link still blocks
        self.assertEqual(ac.tree_info(self.kit)[2], other)
        self.assertFalse(ac.store_linked(other))

    def test_class_k_rule(self):
        sha = self.man["files"][self.src]
        blob = os.path.join(self.store, "blobs", sha[:2], sha)
        rows, s = ac.kit_store_gc(self.store, apply=True)
        self.assertEqual(rows, [])                   # linked by the kit
        shutil.rmtree(self.kit)
        rows, s = ac.kit_store_gc(self.store, apply=True)
        self.assertEqual(rows, [])                   # source copy: blob nlink 1 but a manifest of the window names it
        self.assertTrue(os.path.exists(blob))
        old = time.time() - 15 * 86400
        for n in os.listdir(os.path.join(self.store, "manifests")):
            os.utime(os.path.join(self.store, "manifests", n), (old, old))
        rows, s = ac.kit_store_gc(self.store, apply=False)
        self.assertEqual([r[0] for r in rows], ["WOULD"])
        self.assertTrue(os.path.exists(blob))
        rows, s = ac.kit_store_gc(self.store, apply=True)
        self.assertEqual([r[0] for r in rows], ["DELETED"])
        self.assertFalse(os.path.exists(blob))

    def test_unreadable_manifest_stops_class_k(self):
        shutil.rmtree(self.kit)
        old = time.time() - 15 * 86400
        for n in os.listdir(os.path.join(self.store, "manifests")):
            os.utime(os.path.join(self.store, "manifests", n), (old, old))
        with open(os.path.join(self.store, "manifests", "bad.json"), "w") as f:
            f.write("{")
        rows, s = ac.kit_store_gc(self.store, apply=True)
        self.assertEqual(rows[0][0], "SKIP")
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
