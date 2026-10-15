"""MACRO-VIEW (el1011-ds-misc 2026-10-11): verdict.macros with a bare SRAM master crashed every hold ECO (ORD-0001
/src/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef does not exist).  Bare names, /src/ prefixes and
.lef paths resolve to the src-relative view dir; unresolvable / ambiguous entries fail loudly."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("CL_STATE", tempfile.mkdtemp(prefix="macroviews_"))
import closure_loop as cl  # noqa: E402
import macro_views as mv  # noqa: E402

HERE = Path(__file__).resolve().parent
SRAM = "ot_sram_1r1w_128x256_m1_r2c2"
CANON = f"physical/asap7_memory_macros/{SRAM}"
TREE = [f"{CANON}/{SRAM}.lef", f"{CANON}/{SRAM}_ff.lib", "physical/s81_engc_tiles/views/ot_engc_t_io/ot_engc_t_io.lef",
        "physical/old/ot_dup/ot_dup.lef", "physical/asap7_memory_macros/ot_dup/ot_dup.lef",
        "physical/a/ot_amb/ot_amb.lef", "physical/b/ot_amb/ot_amb.lef", "physical/x/notaview.lef"]


class Resolve(unittest.TestCase):
    def test_bare_master_resolves(self):
        out, rw = mv.resolve([SRAM], TREE)
        self.assertEqual(out, [CANON])
        self.assertEqual(rw, [(SRAM, CANON)])

    def test_canonical_unchanged(self):
        self.assertEqual(mv.resolve([CANON], TREE), ([CANON], []))

    def test_prefixes_and_lef_path_normalised(self):
        for e in (f"/src/{CANON}", f"{{SRC}}/{CANON}/", f"{CANON}/{SRAM}.lef", f"/src/{SRAM}"):
            self.assertEqual(mv.resolve([e], TREE)[0], [CANON], e)

    def test_path_entry_kept_when_not_in_tree(self):
        v = "physical/hbm_attn_tile_r/quad_b_tc/c891a57cf_cg_hm10/view"
        self.assertEqual(mv.resolve([f"/src/{v}/"], TREE), ([v], [(f"/src/{v}/", v)]))

    def test_ambiguous_prefers_memory_macros(self):
        self.assertEqual(mv.resolve(["ot_dup"], TREE)[0], ["physical/asap7_memory_macros/ot_dup"])

    def test_ambiguous_fails(self):
        with self.assertRaisesRegex(mv.MacroViewError, "ambiguous"):
            mv.resolve(["ot_amb"], TREE)

    def test_missing_fails(self):
        with self.assertRaisesRegex(mv.MacroViewError, "no ot_nope/ot_nope.lef"):
            mv.resolve(["ot_nope"], TREE)


class Cli(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp(prefix="mvcli_")
        for f in TREE:
            p = Path(self.td) / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("")

    def run_cli(self, *m):
        return subprocess.run([sys.executable, str(HERE / "macro_views.py"), "--root", self.td, *m],
                              capture_output=True, text=True)

    def test_cli_resolves_bare(self):
        r = self.run_cli(SRAM, "physical/s81_engc_tiles/views/ot_engc_t_io")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.split(), [CANON, "physical/s81_engc_tiles/views/ot_engc_t_io"])
        self.assertIn(f"MACRO-VIEW: {SRAM} -> {CANON}", r.stderr)

    def test_cli_fails_loudly(self):
        r = self.run_cli("ot_nope")
        self.assertEqual(r.returncode, 2)
        self.assertIn("MACRO-VIEW ERROR", r.stderr)

    def test_eco_scripts_resolve_before_mounting(self):
        for s in ("hold_eco.sh", "vtswap_eco.sh"):
            t = (HERE / s).read_text()
            i, k = t.index('macro_views.py" --root'), t.index('MS=""; for m in ${MACROS:-}')
            self.assertLess(i, k, s)
            self.assertIn("exit 2", t[i:k], s)

    def test_shipped(self):
        self.assertIn("macro_views.py", cl.HELPERS)


class Daemon(unittest.TestCase):
    def job(self, macros):
        return {"name": "x", "events": [], "spec": {"verdict": {"macros": macros}, "source": {"commit": "a" * 40}}}

    def test_verdict_macros_resolves_at_commit(self):
        j = self.job([SRAM])
        with patch.object(cl, "sh", return_value=SimpleNamespace(returncode=0, stdout="\n".join(TREE))) as sh:
            self.assertEqual(cl.verdict_macros(j), [CANON])
            self.assertEqual(cl.verdict_macros(j), [CANON])        # cached per commit
            self.assertEqual(sh.call_count, 1)
        self.assertTrue(any("MACRO-VIEW" in str(e) for e in j["events"]))

    def test_verdict_macros_falls_back_to_raw(self):
        j = self.job(["ot_nope"])
        with patch.object(cl, "sh", return_value=SimpleNamespace(returncode=0, stdout="\n".join(TREE))):
            self.assertEqual(cl.verdict_macros(j), ["ot_nope"])   # remote helper then fails loudly (exit 2)

    def test_empty(self):
        self.assertEqual(cl.verdict_macros(self.job([])), [])


if __name__ == "__main__":
    unittest.main()
