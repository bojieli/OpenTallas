import os, tempfile, unittest
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
        self.assertEqual(B.share_identical(p, None, 0), "kept")      # not under a scratch root, no OT_BIND_SHARE

    def test_orphan_store_entry_pruned(self):
        d = tempfile.mkdtemp(); store = d + "/s"; os.makedirs(store)
        o = store + "/1-dead"; open(o, "wb").write(b"z"); os.utime(o, (1, 1))
        p = d + "/a.json"; open(p, "wb").write(b"x" * 20)
        B.share_identical(p, store, 10)
        self.assertFalse(os.path.exists(o))


if __name__ == "__main__":
    unittest.main()
