"""HBM-HUB-RTL-1 11-11 (DIE-HBM-100 ruling (B)): hbm_param_regen STRAP_PINS guard for the QUANT controller strap.

The QUANT LG (hb_quant_q__quant_qk_lg) is a register pass-through rr_i -> rr_o into hb_quant_q__quant_q_xp_ctl rr_v; the
controller's read round trip is its rl_cfg strap.  An rd1 bind (+X on the LG rr_i) passes only when the as-built netlist
ties rl_cfg = 126 + X on a master that accepts it (ctl_r5 for 127..254).
    python3 -m pytest tools/die_plan/test_hbm_strap_guard.py
"""
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("hbm_param_regen_t", ROOT / "physical/die_plan/hbm/bind/hbm_param_regen.py")
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

LG, CTL = "hb_quant_NW__quant_NW2_lg", "hb_quant_NW__quant_NW_xp_ctl"


def ctx(value, width, module, kind="strap"):
    cells = [SimpleNamespace(path=LG, module="ot_hgi_qdq_lg_bf16_r2"), SimpleNamespace(path=CTL, module=module)]
    sinks = {(1, "rl_cfg", i): (kind, str((value >> i) & 1)) for i in range(width)}
    return SimpleNamespace(F=SimpleNamespace(cells=cells), sinks=sinks)


def guard(c, xs=frozenset({1})):
    return H.strap_guard(c, LG, "rr_i", set(xs), lambda key, v: max(v))


class StrapGuard(unittest.TestCase):
    def test_rd1_on_r5_passes(self):
        self.assertEqual(guard(ctx(127, 8, "ot_hgi_qdq_transport_ctl_r5")), "")

    def test_strap_not_moved_fails(self):
        self.assertIn("126 + 1 = 127", guard(ctx(126, 8, "ot_hgi_qdq_transport_ctl_r5")))

    def test_r4_cannot_take_127(self):
        self.assertIn("as-built 127", guard(ctx(127, 7, "ot_hgi_qdq_transport_ctl_r4")))

    def test_tied_not_strap_fails(self):
        self.assertIn("as-built None", guard(ctx(127, 8, "ot_hgi_qdq_transport_ctl_r5", kind="int")))

    def test_other_leaf_not_guarded(self):
        self.assertIsNone(H.strap_guard(ctx(127, 8, "x"), "hb_coll_NW.__cut_vm", "rr_i", {1}, lambda k, v: max(v)))


if __name__ == "__main__":
    unittest.main()
