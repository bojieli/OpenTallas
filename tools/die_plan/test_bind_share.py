import os, tempfile, unittest
from unittest.mock import patch
import bind_share as B


class T(unittest.TestCase):
    def test_identical_copies_share_one_inode_and_distinct_stay(self):
        d = tempfile.mkdtemp(); store = d + "/s"
        a, b, c = d + "/a.json", d + "/b.json", d + "/c.json"
        for p, x in ((a, b"x" * 100), (b, b"x" * 100), (c, b"x" * 99 + b"y")):
            open(p, "wb").write(x)
        self.assertEqual(B.share_identical(a, store, 10), "stored")
        self.assertEqual(B.share_identical(b, store, 10), "linked")
        self.assertEqual(B.share_identical(c, store, 10), "stored")
        self.assertEqual(os.stat(a).st_ino, os.stat(b).st_ino)
        self.assertNotEqual(os.stat(a).st_ino, os.stat(c).st_ino)
        self.assertEqual(open(b, "rb").read(), b"x" * 100)

    def test_small_or_unstorable_kept(self):
        d = tempfile.mkdtemp(); p = d + "/a.json"; open(p, "wb").write(b"x")
        self.assertEqual(B.share_identical(p, d + "/s"), "kept")
        # The remote gate's TMPDIR can sit under a real scratch root.
        # Exercise the unavailable-store case without writing its shared store.
        with patch.object(B, "store_dir", return_value=None):
            self.assertEqual(B.share_identical(p, None, 0), "kept")

    def test_orphan_store_entry_pruned(self):
        d = tempfile.mkdtemp(); store = d + "/s"; os.makedirs(store)
        o = store + "/1-dead"; open(o, "wb").write(b"z"); os.utime(o, (1, 1))
        p = d + "/a.json"; open(p, "wb").write(b"x" * 20)
        B.share_identical(p, store, 10)
        self.assertFalse(os.path.exists(o))

    def test_never_links_onto_a_published_read_only_inode(self):
        """FLOW-OPS-1300 (OPUS-FIX-KV-HGI-R5): a private bind_sinks.json was linked onto the store inode a sealed tree made r--r--r--"""
        d = tempfile.mkdtemp(); store = d + "/s"
        a, b = d + "/sealed.json", d + "/private.json"
        open(a, "wb").write(b"x" * 100); open(b, "wb").write(b"x" * 100)
        self.assertEqual(B.share_identical(a, store, 10), "stored")
        os.chmod(a, 0o444)                                   # publish chmod a-w acts on the shared inode
        self.assertEqual(B.share_identical(b, store, 10), "kept")
        self.assertNotEqual(os.stat(a).st_ino, os.stat(b).st_ino)
        self.assertEqual(os.stat(b).st_nlink, 1)

    def test_bind_outputs_are_renamed_into_place_never_written_through_a_link(self):
        import sys, importlib
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        bind = importlib.import_module("bind")
        from pathlib import Path
        d = tempfile.mkdtemp(); shared = d + "/shared.json"; mine = d + "/bind_sinks.json"
        open(shared, "w").write("old"); os.link(shared, mine); os.chmod(shared, 0o444)
        bind._fresh_write_text(Path(mine), "new")
        self.assertEqual(open(mine).read(), "new")
        self.assertEqual(open(shared).read(), "old")         # the other link is untouched
        self.assertEqual(os.stat(mine).st_nlink, 1)
        src = open(bind.__file__).read()
        self.assertNotRegex(src, r'\(out / f?"[^"\n]*"\)\.write_text\(')    # every bind output goes through _fresh_write_text


if __name__ == "__main__":
    unittest.main()
