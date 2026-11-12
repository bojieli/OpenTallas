"""KW-FIX-46 11-12 (CORES-HBM-1 READ_AT_COMMIT): fetch() reads a pinned file from REPO/.kw_at_commit/<commit>/<f> when the
tree is a plain copy (no git)"""
import tempfile, unittest
from pathlib import Path
import gen_core_kit_hbm as G


class FetchAtCommitStore(unittest.TestCase):
    def test_store_used_without_git(self):
        td = Path(tempfile.mkdtemp())
        old = G.REPO
        G.REPO = td
        self.addCleanup(setattr, G, "REPO", old)
        (td / ".kw_at_commit" / "abc123" / "rtl").mkdir(parents=True)
        (td / ".kw_at_commit" / "abc123" / "rtl" / "x.sv").write_text("module x; endmodule\n")
        dst = td / "out" / "x.sv"
        dst.parent.mkdir()
        G.fetch("rtl/x.sv", "abc123", dst, at_commit=True)
        self.assertEqual(dst.read_text(), "module x; endmodule\n")
        with self.assertRaises(SystemExit):
            G.fetch("rtl/y.sv", "abc123", td / "out" / "y.sv", at_commit=True)


if __name__ == "__main__":
    unittest.main()
