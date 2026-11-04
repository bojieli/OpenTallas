"""DIE-HBM-61/RF1-BUILD 11-03 class fixes for the HBM-RF1 conservative-form builds.
(1) q2_hard_v8g__reduce d44v pin table (oneclk + clock-entry pins, sha 72041fe1...) selects the reviewed oneclk wrapper
    (without it gen fell back to the 33-replica clk_reduce wrapper -> PORT_MISMATCH ['clk', 'clk_reduce']).
(2) ot_qkvd_llr_replay_sram_leaf RW arms are independent labelled if-generates: yosys put the else-if arms under
    genblk1, so core_macros "<leaf>.g_rw141.u_sram" was not found (host_cp_rxs MPL-0020).
    Names + equivalence for W 20/137/141/306/400: results/die_hbm_1103/rf1_build/llr_names_eq.sh."""
import json, re
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
POR = REPO / "physical/die_plan/hbm/plan_of_record/d44v/core_clock_regions.json"


def test_q2_reduce_d44v_pins_select_oneclk_wrapper():
    r = json.loads((HERE / "recipes_b2.json").read_text())["ot_hfd_coll_q2_hard_v8g__reduce"]
    sel = r["wrapper_by_pins_sha256"]["72041fe1902610536dde7a09cf1f5109f2afe59dea0e89dfc2468acfcef2a8b0"]
    assert sel.endswith("wrappers/oneclk/ot_hfd_coll_q2_hard_v8g__reduce.sv")
    w = re.sub(r"//.*", "", (REPO / sel).read_text())
    assert re.search(r"input\s+wire\s+clk\s*,", w) and "clk_reduce" not in w


def test_llr_rw_arms_not_else_if_chain():
    s = (REPO / "rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv").read_text()
    blk = s[s.index("`ifdef OT_HBM_RW_MACROS\n    // DIE-HBM-61/MEM"):]
    blk = blk[:blk.index("ot_sram_1r1w_64x512_m1_r2c2 u_sram")]
    assert "else if" not in blk and "end else" not in blk
    for g in ("g_rw32", "g_rw141", "g_rw306", "g_r2c2"):
        assert re.search(r"\n    if \(.*\) begin : " + g + r"\n", blk), g


def test_rf1_clock_regions_superset_of_d44v():
    b = json.loads((REPO / "results/die_hbm_1103/rf1_build/core_clock_regions_rf1.json").read_text())["modules"]
    for m in ("ot_hbm_xp_aq_tree13_fmt", "ot_hgi_sfu_programme_store_r10", "ot_hgi_sm_xload_cl2_ctlx", "hfd_hgi_vms_glue_nw_t"):
        assert b[m]["sinks_per_entry"] <= 5000 and len(b[m]["regional_entries"]) == b[m]["entries"]
        assert all(e["xy_um"] for e in b[m]["regional_entries"])
    if POR.is_file():
        a = json.loads(POR.read_text())["modules"]
        assert all(b[m] == v for m, v in a.items())
