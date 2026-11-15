"""KV-ECTLK-RL 11-15: a kit whose config.mk already carries the comment '# OT_PRD post-route drive repair' (KV-50 / KV-51
notes) made prd_mk.sh skip its whole append block: no eco_grt_pre.tcl (no clk_freeze_pre.tsv), the kit's own
POST_GLOBAL_ROUTE_TCL stayed last, the ECO was a NO-OP.  And a kit that already routes through eco_drt_pre.tcl got
OT_ECO_DRT_PRE_CHAIN = eco_drt_pre.tcl (the hook chained to itself: detail_route.tcl 'too many nested evaluations').
The append block of prd_mk.sh is run verbatim on such a config.mk."""
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def block():
    mk = (HERE / "prd_mk.sh").read_text().splitlines()
    a = next(i for i, ln in enumerate(mk) if ln.startswith("if ! grep -q '^override export PRE_GLOBAL_ROUTE_TCL = /work/eco_grt_pre.tcl"))
    g = next(i for i in range(a + 1, len(mk)) if mk[i].startswith("override export GND_NETS_VOLTAGES"))
    b = next(i for i in range(g + 1, len(mk)) if mk[i] == "fi")
    return "\n".join(mk[a:b + 1]) + "\n"


def run(cfg):
    with tempfile.TemporaryDirectory() as td:
        out = Path(td)
        (out / "config.mk").write_text(cfg)
        p = subprocess.run(["bash", "-euo", "pipefail", "-c", block()], capture_output=True, text=True,
                           env=dict(V="m10", OUT=str(out), ML_TT="/work/macros/x_tt.lib", ML_FF="/work/macros/x_ff.lib", PATH="/usr/bin:/bin"))
        assert p.returncode == 0, p.stderr
        return (out / "config.mk").read_text().splitlines()


KIT = """override export PRE_GLOBAL_ROUTE_TCL = /work/grt_pre_core.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/grt_post_core.tcl
# OT_PRD post-route drive repair (tools/die_plan/post_route_drv, variant m15) [DIE-KV-51 re-added after the KV-50 marker]
override export PRE_DETAIL_ROUTE_TCL = /work/eco_drt_pre.tcl
override export POST_GLOBAL_ROUTE_TCL = /work/grt_post_core.tcl
"""


class Marker(unittest.TestCase):
    def test_comment_marker_does_not_skip_block(self):
        L = run(KIT)
        post = [x for x in L if x.startswith("override export POST_GLOBAL_ROUTE_TCL")]
        self.assertEqual(post[-1], "override export POST_GLOBAL_ROUTE_TCL = /work/eco_post.tcl")
        self.assertEqual([x for x in L if x.startswith("override export PRE_GLOBAL_ROUTE_TCL")][-1],
                         "override export PRE_GLOBAL_ROUTE_TCL = /work/eco_grt_pre.tcl")
        self.assertIn("override export OT_ECO_GRT_PRE_CHAIN = /work/grt_pre_core.tcl", L)

    def test_no_self_chain_of_eco_drt_pre(self):
        L = run(KIT)
        self.assertFalse([x for x in L if "OT_ECO_DRT_PRE_CHAIN = /work/eco_drt_pre.tcl" in x])

    def test_other_kit_drt_hook_still_chained(self):
        L = run("override export PRE_DETAIL_ROUTE_TCL = /work/kit_drt.tcl\n")
        self.assertIn("override export OT_ECO_DRT_PRE_CHAIN = /work/kit_drt.tcl", L)

    def test_second_run_is_idempotent(self):
        once = run(KIT)
        twice = run("\n".join(once) + "\n")
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
