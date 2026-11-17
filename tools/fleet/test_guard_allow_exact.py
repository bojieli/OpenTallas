import os, tempfile, time, unittest
import ot_delete_guard as G

R = "/srv/opentallas-scratch2/claude/"


class AllowExact(unittest.TestCase):
    PROT = {R + "s81-b3-clk/rows/f2s5", R + "kw45/src_x_d1/keep/me/here"}

    def test_an_excepted_subdir_is_deletable_the_rows_dir_and_siblings_are_not(self):
        sub = R + "s81-b3-clk/rows/f2s5/d7/r3"
        self.assertIn("protected", G.refuse(sub, self.PROT, "", allow=set()))                               # no exception: refused by the rows dir
        self.assertIsNone(G.refuse(sub, self.PROT, "", allow={sub}))
        self.assertIn("protected", G.refuse(R + "s81-b3-clk/rows/f2s5/d7/r4", self.PROT, "", allow={sub}))   # a sibling stays protected
        self.assertIn("protected", G.refuse(R + "s81-b3-clk/rows/f2s5", self.PROT, "", allow={sub}))          # the rows dir itself too

    def test_an_exception_never_covers_a_protected_path_inside_it_or_a_live_process(self):
        inside = R + "s81-b3-clk/rows/f2s5/d7"
        p2 = self.PROT | {inside + "/r3/keep"}
        self.assertIn("protected", G.refuse(inside + "/r3", p2, "", allow={inside + "/r3"}))
        self.assertIn("live process", G.refuse(inside + "/r3", self.PROT, inside + "/r3/", allow={inside + "/r3"}))

    def test_allow_file_lines_expire_and_garbage_is_ignored(self):
        f = tempfile.mktemp(); now = time.time()
        open(f, "w").write("%sa/b/c/d/e\t%d\tCOORD\n%sold/b/c/d/e\t%d\tx\nnot a line\n" % (R, now + 3600, R, now - 5))
        self.assertEqual(G.load_allow_exact(f, now), {R + "a/b/c/d/e"})
        self.assertEqual(G.load_allow_exact("/nonexistent"), set())
