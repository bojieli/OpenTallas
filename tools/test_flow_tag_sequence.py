"""Counting accepts releases after z while retaining commit binding."""
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location("release_tree_plan", Path(__file__).with_name("release_tree_plan.py"))
plan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan)

class FlowSequenceTest(unittest.TestCase):
    def test_resign_count(self):
        for seq in ("a", "z", "aa", "ah", "abc"):
            for suffix in ("", "-qc", "-s81", "-head", "-kv", "-hbm"):
                tag = "flow-20261106-" + seq + suffix
                r = dict(resign=True, flow_tag=tag, src_commit="a" * 12, versioned=True)
                self.assertTrue(plan.check_resign_tag(r, lambda t: "a" * 40)["versioned"])
                r = dict(resign=True, flow_tag=tag, src_commit="b" * 12, versioned=True)
                self.assertFalse(plan.check_resign_tag(r, lambda t: "a" * 40)["versioned"])
        for tag in ("flow-20261106-", "flow-20261106-AH", "flow-20261106-a1", "flow-20261106-ah-other", "flow-2026116-ah", "xflow-20261106-ah"):
            r = dict(resign=True, flow_tag=tag, src_commit="a" * 12, versioned=True)
            self.assertFalse(plan.check_resign_tag(r, lambda t: "a" * 40)["versioned"])

if __name__ == "__main__":
    unittest.main()
