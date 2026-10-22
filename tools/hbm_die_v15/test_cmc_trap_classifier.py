"""check_contract_modules trap classifier: u_trap / u_cfg_err under g_bad_* / g_*_err* = static assert (HBMc/CHAIN2 10-22)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_contract_modules import trap_label

C12 = """generate if (OPR != 0) begin : g_bad_c12
    ot_hdc_v41x_vec_lane_c12_OPR_0_1_DDIV_19_21_SIDEX_0_3 u_trap ();
end endgenerate"""
SFU = """if (MLAT != 6) begin : g_chain_cfg_err2
    OT_SFU_CHAIN_HARD_VIEW_IS_MLAT6_ALAT6_DDIV21_DENR1_DRING4_K1 u_cfg_err ();
end"""


def test_c12_trap():
    assert trap_label(C12, C12.index('ot_hdc'), 'u_trap') == 'g_bad_c12'


def test_sfu_cfg_err():
    assert trap_label(SFU, SFU.index('OT_SFU'), 'u_cfg_err') == 'g_chain_cfg_err2'


def test_real_missing_not_masked():
    t = "begin : g_bad_x\n missing_mod u_core ();"          # wrong instance name
    assert trap_label(t, t.index('missing_mod'), 'u_core') is None
    t = "begin : g_lane\n missing_mod u_trap ();"            # wrong label
    assert trap_label(t, t.index('missing_mod'), 'u_trap') is None
