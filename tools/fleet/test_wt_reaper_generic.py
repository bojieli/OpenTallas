"""wt-reaper protected(): a BROAD ancestor named in free text (a kit_wave.json note 'every /srv path') says nothing about a worktree
(KW-FIX-44 11-11); a real PROTECTED-DBS parent still protects its children."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("wt_reaper_g", Path(__file__).with_name("wt-reaper.py"))
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


class GenericAncestor(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp(prefix="wrg")
        self.wt = os.path.join(self.t, "claude", "lane", "wt1")
        os.makedirs(self.wt)
        os.makedirs(os.path.join(self.t, "common"))

    def prot(self, listed):
        return R.protected(self.wt, os.path.join(self.t, "admin"), os.path.join(self.t, "common"), listed=listed)

    def test_broad_ancestor_does_not_protect(self):
        # the temp root stands in for /srv or a scratch root: listed as a broad ancestor of the worktree
        old = R.GENERIC_MOUNTS
        R.GENERIC_MOUNTS = set(old) | {self.t}
        try:
            why = self.prot([(self.t, "kit_wave.json note: every /srv path")])
        finally:
            R.GENERIC_MOUNTS = old
        self.assertNotIn("inside listed path", why or "")

    def test_same_listing_protects_when_not_broad(self):
        why = self.prot([(self.t, "lanes/PROTECTED-DBS.txt")])
        self.assertIn("inside listed path", why or "")

    def test_real_lane_parent_still_protects(self):
        why = self.prot([(os.path.join(self.t, "claude", "lane"), "lanes/PROTECTED-DBS.txt")])
        self.assertIn("inside listed path", why or "")

    def test_exact_listed_worktree_protects(self):
        why = self.prot([(self.wt, "lanes/PROTECTED-DBS.txt")])
        self.assertIn("listed source", why or "")


if __name__ == "__main__":
    unittest.main()
