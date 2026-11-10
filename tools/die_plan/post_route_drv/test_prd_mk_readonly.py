"""HEAD-92 11-10 (class fix): a second PRD pass staged from a first pass dir whose tool copies came from the read-only
shared tools tree (mode 0444) failed in prd_mk.sh ('cp: cannot create regular file .../prd_count.tcl: Permission
denied'), so the ECO died as 'prd_mk.sh failed (pass dir not staged)'.  The staging block of prd_mk.sh (rsync of the
source pass, chmod, tool copies) is run here on such a tree; also: a copy never writes through a symlink."""
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = ("prd_hook.tcl prd_count.tcl eco_grt_pre.tcl eco_drt_pre.tcl prd_route_keep.tcl prd_targeted.tcl "
         "prd_local_branches.tcl prd_tiesplit.tcl prd_autofo.tcl prd_spef_insts.py").split()
SO_TOOLS = "clk_freeze.tcl clk_dump_db.tcl clk_geom_diff.py clk_freeze_check.sh kit_modes_eco.tcl pg_connect.tcl".split()


def block():
    """the staging lines of prd_mk.sh, verbatim and in their order: chmod after the source rsync, the tool copies"""
    mk = (HERE / "prd_mk.sh").read_text().splitlines()
    pick = [i for i, ln in enumerate(mk) if ln == 'chmod -R u+w "$OUT"' or ln.startswith((
        "for f in prd_hook.tcl prd_count.tcl", 'if [ -n "${OT_PRD_HOOK:-}" ]; then',
        "for f in clk_freeze.tcl clk_dump_db.tcl", 'chmod u+w "$OUT"/*.tcl'))]
    assert len(pick) == 5, pick
    # the chmod must follow the rsync of the source pass: it is what makes the copied-in files writable
    rs = [i for i, ln in enumerate(mk) if ln.endswith("$KIT/ $OUT/")]
    assert rs and rs[0] < pick[0] and pick == sorted(pick), (rs, pick)
    return 'mkdir -p "$OUT"\nrsync -a "$KIT/" "$OUT/"\n' + "\n".join(mk[i] for i in pick) + "\n"


class ReadOnlySecondPass(unittest.TestCase):
    def tree(self, t):
        t = Path(t)
        here, so = t / "shared/post_route_drv", t / "shared/so/tools/die_plan"
        for d, names, tag in ((here, TOOLS, "v2"), (so, SO_TOOLS, "v2")):
            d.mkdir(parents=True)
            for n in names:
                (d / n).write_text(f"{n} {tag}\n")
                os.chmod(d / n, 0o444)            # the read-only shared tools tree
        kit = t / "pass1"                         # first pass dir: its tool copies kept mode 0444
        kit.mkdir()
        for n in TOOLS + SO_TOOLS:
            (kit / n).write_text(f"{n} v1\n")
            os.chmod(kit / n, 0o444)
        (kit / "config.mk").write_text("x\n")
        os.chmod(kit / "config.mk", 0o444)
        return t, here, so.parent.parent, kit

    def run_block(self, t, here, so, kit, out, script=None):
        env = dict(os.environ, KIT=str(kit), OUT=str(out), HERE=str(here), SO=str(so))
        env.pop("OT_PRD_HOOK", None)
        return subprocess.run(["bash", "-euo", "pipefail", "-c", script or block()], env=env,
                              capture_output=True, text=True)

    def test_second_pass_overwrites_read_only_copies(self):
        with tempfile.TemporaryDirectory() as td:
            t, here, so, kit = self.tree(td)
            out = t / "pass2"
            p = self.run_block(t, here, so, kit, out)
            self.assertEqual(p.returncode, 0, p.stderr)
            for n in TOOLS + SO_TOOLS:
                self.assertEqual((out / n).read_text(), f"{n} v2\n")
                self.assertTrue(os.stat(out / n).st_mode & stat.S_IWUSR, n)
            self.assertTrue(os.stat(out / "config.mk").st_mode & stat.S_IWUSR)   # later >> appends work
            # a third pass from this one stages as well
            p = self.run_block(t, here, so, out, t / "pass3")
            self.assertEqual(p.returncode, 0, p.stderr)

    def test_old_plain_cp_form_fails_on_this_tree(self):
        # the pre-fix form, to show the test tree reproduces the HEAD-92 failure
        with tempfile.TemporaryDirectory() as td:
            t, here, so, kit = self.tree(td)
            old = 'rsync -a "$KIT/" "$OUT/"\nfor f in prd_count.tcl; do cp $HERE/$f $OUT/; done\n'
            p = self.run_block(t, here, so, kit, t / "pass2", old)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("Permission denied", p.stderr)

    def test_copy_never_writes_through_a_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            t, here, so, kit = self.tree(td)
            shared = t / "shared_src_prd_count.tcl"
            shared.write_text("shared\n")             # writable shared file a kit links to
            os.chmod(kit / "prd_count.tcl", 0o644)
            (kit / "prd_count.tcl").unlink()
            (kit / "prd_count.tcl").symlink_to(shared)
            out = t / "pass2"
            p = self.run_block(t, here, so, kit, out)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(shared.read_text(), "shared\n")
            self.assertFalse((out / "prd_count.tcl").is_symlink())
            self.assertEqual((out / "prd_count.tcl").read_text(), "prd_count.tcl v2\n")


if __name__ == "__main__":
    unittest.main()
