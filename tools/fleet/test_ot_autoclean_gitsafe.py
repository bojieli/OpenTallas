"""GITSAFE_1114 (ADMIT-TUNE-1): autoclean never writes ARCHIVED.json / STUBBED.json inside a git work tree or a never-touch tree.
Incident: AUTOCLEAN-7 overwrote a tracked file in intel2's ~/OpenTallas checkout (11-14 05:39 PST) and blocked a merge train.
    python3 -I tools/fleet/test_ot_autoclean_gitsafe.py"""
import io
import json
import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_ot_autoclean_auto as T   # noqa: E402

ac = T.ac


def mark(unit):
    a = SimpleNamespace(unit=unit, roots=[os.path.dirname(unit)])
    out = io.StringIO()
    with patch.object(sys, "stdin", io.StringIO(json.dumps({"archive": "/x", "sha": {}, "verify": "ok"}))), patch.object(ac, "say", lambda *m: out.write(" ".join(map(str, m)))):
        rc = ac.mark_archived_main(a)
    return rc, out.getvalue()


class GitSafe(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def test_unit_inside_a_git_work_tree_is_refused_and_untouched(self):
        repo = os.path.join(self.root, "checkout")
        unit = os.path.join(repo, "physical", "plan", "views_e2s", "unit")
        os.makedirs(unit)
        os.makedirs(os.path.join(repo, ".git"))
        tracked = os.path.join(unit, "ARCHIVED.json")
        open(tracked, "w").write("tracked content\n")
        rc, msg = mark(unit)
        self.assertEqual(rc, 2)
        self.assertIn("inside git work tree", msg)
        self.assertEqual(open(tracked).read(), "tracked content\n")

    def test_never_touch_tree_is_refused(self):
        unit = os.path.join(ac.HOME, "OpenTallas", "physical", "nonexistent_unit")
        self.assertIn("never-touch", ac.write_refused(unit))

    def test_plain_scratch_unit_may_be_marked(self):
        unit = os.path.join(self.root, "lane", "u1")
        os.makedirs(unit)
        rc, msg = mark(unit)
        self.assertEqual(rc, 0, msg)
        self.assertTrue(os.path.exists(os.path.join(unit, "ARCHIVED.json")))

    def test_git_tree_of_finds_the_enclosing_repo(self):
        repo = os.path.join(self.root, "r")
        os.makedirs(os.path.join(repo, ".git"))
        os.makedirs(os.path.join(repo, "a", "b"))
        self.assertEqual(os.path.realpath(ac.git_tree_of(os.path.join(repo, "a", "b"))), os.path.realpath(repo))
        self.assertIsNone(ac.git_tree_of(os.path.join(self.root, "nogit")))


if __name__ == "__main__":
    unittest.main()
