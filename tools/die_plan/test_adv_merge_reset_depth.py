"""ADV-MERGE-RESET-DEPTH: real positive KV kv3_hub_Eo astk_EN on plan bf83bf83b70c (OPUS-FIX-KV-HUB-R6 11-22,
kit_rtl rc 2 'g_phys_fault_u_fault__rst_n merge group is not one net')."""
import copy
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_merge_reset_depth as A

PINS = ["g_phys_fault_u_fault__rst_n", "u_strip_u_strip_g_zn_0_u_zn__rst_n", "u_strip_u_strip_g_zn_1_u_zn__rst_n",
        "u_strip_u_strip_g_zn_2_u_zn__rst_n", "u_strip_u_strip_g_zn_3_u_zn__rst_n", "u_strip_u_strip_u_ctl__rst_n"]


def _row(pin, d=8):
    return {"inst": "astk_EN", "port": pin, "side": "sink", "D": d, "path_um": 2250.0}


def _plan(rows, sites=None):
    return {"partition_types": {"kv3_hub_Eo": {
        "hard_cores": [{"inst": "astk_EN", "module": "kv3_astk",
                        "native_port_adapter": {"merge": {"g_phys_fault_u_fault__rst_n": PINS,
                                                          "ck": [p.replace("rst_n", "ck") for p in PINS]}}}],
        "relay_depth": rows + [{"inst": "seq_g_fan_0_u_fan", "port": "rst_n", "side": "sink", "D": 3}],
        "relay_sites": sites or {}}}}


def test_positive_partial_group():
    out = A.findings(_plan([_row(PINS[0])]), "p.json")
    hit = [l for l in out if "kv3_hub_Eo astk_EN.g_phys_fault_u_fault__rst_n" in l]
    assert len(hit) == 1 and "rows on 1 only" in hit[0] and "D=8" in hit[0]
    assert out[-1].startswith("WARN ADV-MERGE-RESET-DEPTH summary: 1 finding(s) on 2 merge group(s)")


def test_full_equal_group_clean():
    sites = {f"u_y_xd_astk_EN_g_phys_fault_u_fault__rst_n_0_{s}.q": [1.0, 2.0] for s in range(8)}
    out = A.findings(_plan([_row(p) for p in PINS], sites), "p.json")
    assert out == ["WARN ADV-MERGE-RESET-DEPTH summary: 0 finding(s) on 2 merge group(s) of native_port_adapter "
                   "hard cores (clean)"]


def test_no_rows_clean_and_old_bound_form():
    assert "0 finding(s)" in A.findings(_plan([]), "p.json")[-1]
    rows = [dict(_row(PINS[0]), inst="u_astk_EN")]
    assert "rows on 1 only" in A.findings(_plan(rows), "p.json")[0]


def test_unequal_and_sites():
    rows = [_row(p) for p in PINS[:-1]] + [_row(PINS[-1], 6)]
    out = A.findings(_plan(rows), "p.json")
    assert any("D differs" in l for l in out)
    sites = {f"u_y_xd_astk_EN_{PINS[0]}_0_{s}.q": [0, 0] for s in range(8)}
    sites.update({f"u_y_xd_astk_EN_{PINS[1]}_0_{s}.q": [0, 0] for s in range(5)})
    out = A.findings(_plan([_row(p) for p in PINS], sites), "p.json")
    assert any("relay_sites stage chains disagree" in l for l in out)


def test_never_raises():
    assert "not checked" in A.findings({"partition_types": {"t": {"hard_cores": [{"native_port_adapter": 5}]}}}, "p")[0]
