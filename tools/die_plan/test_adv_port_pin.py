"""ADV-PORT-PIN: real positive KV D28 kv3_pv_v3e (OPUS-FIX-KV-PV-R7 11-22, PORT_BIND extra ri_pv_u_g1_j_rst_n[0])."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_port_pin as A

WRAP = """module kv3_pv_v3e_part (
    input  wire clk,
    input  wire arst_n,
    input  wire start_i,   // START in (wavefront broadcast)
    input  wire [524:0] i_vport_W_N_vo,   // 524 data + epoch [524]: lane L2383
    output wire [1:0] o_vport_E_N_f,   // 1 data + epoch [1]: lane L2261
    input  wire [5:0] strap_ca_k_ft0_i,
    input  wire [0:0] ft0_i,
    output wire [0:0] ft0_o,
    input  wire [3:0] strap_r8pad_slg_x_tok,
    input  wire [0:0] ri_pv_u_g1_j_rst_n,   // reset spine: reset spine hub_Wi -> pv_S_3e, released after 2 clocks
    output wire rst_o_0
);
endmodule
"""

PLAN = {"die": "qwen_kvsys", "partitions": [{"name": "pv_S_3e", "type": "kv3_pv_v3e"}],
        "partition_types": {"kv3_pv_v3e": {
            "module": "kv3_pv_v3e_part", "outline_um": [1080.0, 1520.64],
            "buses": [{"name": "i_vport_W_N_vo", "dir": "in", "width": 524}, {"name": "o_vport_E_N_f", "dir": "out", "width": 1}],
            "ft_slots": [{"name": "ft0", "width": 1}],
            "count_straps": [{"name": "strap_ca_k_ft0_i", "width": 6}],
            "reset": {"tap_um": [535.68, 760.32], "sync_stages": 2}}}}


def _bind(tmp):
    b = tmp / "bind_of_record"
    (b / "rtl").mkdir(parents=True)
    (b / "rtl" / "kv3_pv_v3e_part.sv").write_text(WRAP)
    (b / "bind_report.json").write_text(json.dumps({"die": "qwen_kvsys", "types": {"kv3_pv_v3e": {"module": "kv3_pv_v3e_part"}},
                                                    "bump_ports": []}))
    (b / "bind_parent_id_straps.json").write_text(json.dumps({"types": {"kv3_pv_v3e": {
        "strap_r8pad_slg_x_tok": {"width": 4, "kind": "r8pad_strap"}}}}))
    return b


def test_positive_split_piece_without_spine_pin(tmp_path):
    b = _bind(tmp_path)
    out = A.findings(PLAN, str(tmp_path / "plan.json"), bind_out=str(b))
    hit = [l for l in out if l.startswith("WARN ADV-PORT-PIN kv3_pv_v3e:")]
    assert len(hit) == 1 and "ri_pv_u_g1_j_rst_n" in hit[0] and "extra" in hit[0]
    assert "strap_r8pad" not in hit[0] and "ft0" not in hit[0] and "arst_n" not in hit[0]


def test_fixed_row_clean(tmp_path):
    b = _bind(tmp_path)
    p = copy.deepcopy(PLAN)
    p["partition_types"]["kv3_pv_v3e"]["reset_spine_pins"] = [
        {"name": "ri_pv_u_g1_j_rst_n", "width": 1, "layer": "M7", "sites_um": [[527.04, 760.32]]}]
    out = A.findings(p, str(tmp_path / "plan.json"), bind_out=str(b))
    assert not [l for l in out if "kv3_pv_v3e:" in l]
    assert out[-1].startswith("WARN ADV-PORT-PIN summary: 0 type(s)")


def test_stale_spine_row_missing(tmp_path):
    b = _bind(tmp_path)
    p = copy.deepcopy(PLAN)
    p["partition_types"]["kv3_pv_v3e"]["reset_spine_pins"] = [
        {"name": "ri_pv_u_g1_j_rst_n", "width": 1, "layer": "M7", "sites_um": [[527.04, 760.32]]},
        {"name": "ri_pv_u_g0_j_rst_n", "width": 1, "layer": "M7", "sites_um": [[1071.36, 760.32]]}]
    out = A.findings(p, str(tmp_path / "plan.json"), bind_out=str(b))
    assert any("ri_pv_u_g0_j_rst_n (reset_spine_pins) absent" in l for l in out)


def test_found_beside_plan_and_not_checked(tmp_path):
    _bind(tmp_path)
    assert any("kv3_pv_v3e:" in l for l in A.findings(PLAN, str(tmp_path / "plan.json")))
    out = A.findings(PLAN, str(tmp_path / "nowhere" / "plan.json"))
    assert len(out) == 1 and "not checked" in out[0]
    assert "not checked" in A.findings(None, None, bind_out=str(tmp_path / "bind_of_record"))[0]


def test_stale_bind_carry_over_vs_reshaped(tmp_path):
    b = _bind(tmp_path)
    (tmp_path / "base.json").write_text(json.dumps(PLAN))
    (b / "provenance_bind.json").write_text(json.dumps({"provenance": {"plan": str(tmp_path / "base.json")}}))
    cand = copy.deepcopy(PLAN)
    cand["note"] = "D29 candidate, v3e unchanged"
    (tmp_path / "cand.json").write_text(json.dumps(cand))
    out = A.findings(cand, str(tmp_path / "cand.json"), bind_out=str(b))
    assert any("kv3_pv_v3e:" in l and "ri_pv_u_g1_j_rst_n" in l for l in out)      # carried over from the D28 bind
    cand["partition_types"]["kv3_pv_v3e"]["buses"].append({"name": "i_new", "dir": "in", "width": 3})
    (tmp_path / "cand.json").write_text(json.dumps(cand))
    out = A.findings(cand, str(tmp_path / "cand.json"), bind_out=str(b))
    assert not [l for l in out if "kv3_pv_v3e:" in l] and "1 reshaped type(s)" in out[-1]
