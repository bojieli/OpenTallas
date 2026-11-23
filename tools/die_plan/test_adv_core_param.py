"""ADV-CORE-PARAM tests: fixture cut from the real positive, KV D28 44c3cbf51e50 (epyc8 kv-plan-r6/d29/base_d28.json) on the
rh12_rebind tree: type kv3_hg_v1p2 / partition hg_EN_2, krq lane L362 (o_ectl_Q_N_rq, 9 cycles) + krs lane L2053
(o_slg_Q_N_krsp -> i_slg_Q_N_krsp, 14 cycles) -> bind regen RESPONSE_LAT 31 / QK_ISSUE_AGE 42, while the signed qkd_ectlk_q0..q3
views (kvhg1_views_1116) were built at 37/26 (CORE_QK / CORE_RL guard in cores/harden/ectlk_q/qkd_ectl3_kiss_st_cols.sv).
Negative = the D29 row ROWS_KV-PLAN-R6-ECTLRL (rq 5->3, krsp 8->5 stations: lanes 9->7, 14->11 -> 26/37)."""
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_core_param as A  # noqa: E402

GUARD = """// fixture copy of the D28 tree guard (header trimmed)
`default_nettype none
module qkd_ectl3_kiss_st_cols #(
    parameter integer HXK = 13,
    parameter integer MUT = 0,
    parameter integer QK_ISSUE_AGE = 37,
    parameter integer RESPONSE_LAT = 26
) (input wire [2:0] ck);
    // the values the hardened qkd_ectlk_q0..q3 views of record were built at
    localparam integer CORE_QK = 37;
    localparam integer CORE_RL = 26;
    localparam integer CORE_HXK = 15;
    generate
        if (HXK != CORE_HXK || MUT != 0 || QK_ISSUE_AGE != CORE_QK || RESPONSE_LAT != CORE_RL) begin : g_param_mismatch
            qkd_ectl3_kiss_st_cols__columns_built_for_other_params u_param_mismatch ();
        end
    endgenerate
    qkd_ectlk_columns_legacy #(.QK_ISSUE_AGE(QK_ISSUE_AGE), .RESPONSE_LAT(RESPONSE_LAT)) u_cols (.ck(ck));
endmodule
"""
COLS = "".join(f"module qkd_ectlk_q{k} #(parameter integer QK_ISSUE_AGE = 37, parameter integer RESPONSE_LAT = 26, "
               f"parameter integer HXK = 15) (input wire ck);\nendmodule\n" for k in range(4))


def _tree(tmp, guard=GUARD):
    d = tmp / "physical" / "die_plan" / "qwen_kvsys" / "cores" / "harden" / "ectlk_q"
    d.mkdir(parents=True)
    (d / "qkd_ectl3_kiss_st_cols.sv").write_text(guard)
    (d / "qkd_ectlk_columns.sv").write_text(COLS)
    (tmp / "tools" / "die_plan").mkdir(parents=True)
    return tmp


def _plan(krq=9, krs=14):
    hcs = [dict(inst=f"ectl_q{k}", module=f"qkd_ectlk_q{k}", physical_inst=f"u_bound.u_ectl.u_cols.u_columns.u_q{k}",
                lef=f"physical/die_plan/qwen_kvsys/kvhg1_views_1116/qkd_ectlk_q{k}/qkd_ectlk_q{k}.lef") for k in range(4)]
    return {
        "die": {"name": "qwen_kvsys"},
        "partition_types": {"kv3_hg_v1p2": {"hard_cores": hcs}, "kv3_pc_v1": {"hard_cores": []}},
        "partitions": [{"name": "hg_EN_2", "type": "kv3_hg_v1p2"}, {"name": "pc_EN_2", "type": "kv3_pc_v1"}],
        "ports": [{"id": "L362_0", "src": {"part": "hg_EN_2", "bus": "o_ectl_Q_N_rq"}, "dst": {"part": "pc_EN_2", "bus": "i_ectl_Q_N_rq"}},
                  {"id": "L2053_0", "src": {"part": "pc_EN_2", "bus": "o_slg_Q_N_krsp"},
                   "dst": {"part": "hg_EN_2", "bus": "i_slg_Q_N_krsp"}}],
        "lanes": [{"id": "L362", "ports": ["L362_0"], "note": "p2p ectl_EN_0.rq", "fixed_cycles": krq - 4},
                  {"id": "L2053", "ports": ["L2053_0"], "note": "p2p slg_EN_0.krsp", "fixed_cycles": krs - 5}],
        "latency": {"lanes": {"L362": {"cycles": krq}, "L2053": {"cycles": krs}}},
    }


def test_positive_d28_ectl_42_31_vs_37_26(tmp_path):
    out = A.findings(_plan(), "base_d28.json", str(_tree(tmp_path)))
    hit = [l for l in out if l.startswith("WARN ADV-CORE-PARAM kv3_hg_v1p2:")]
    assert len(hit) == 1, out
    assert "RESPONSE_LAT 31 / QK_ISSUE_AGE 42" in hit[0] and "built RESPONSE_LAT 26 / QK_ISSUE_AGE 37" in hit[0]
    assert "krq 9 (L362) + krs 14 (L2053) = 31" in hit[0] and "to 18 cycles" in hit[0]
    assert out[-1].startswith("WARN ADV-CORE-PARAM summary: 1 ")


def test_negative_d29_ectlrl_restores_26_37(tmp_path):
    assert A.findings(_plan(krq=7, krs=11), "ectlrl.json", str(_tree(tmp_path))) == []


def test_rebuilt_views_at_42_31_clear_the_d28_plan(tmp_path):
    g = GUARD.replace("CORE_QK = 37", "CORE_QK = 42").replace("CORE_RL = 26", "CORE_RL = 31")
    out = A.findings(_plan(), "base_d28.json", str(_tree(tmp_path, g)))
    # family clean; only the record-consistency note (guard 42/31 vs q0..q3 header defaults 37/26) remains
    assert not [l for l in out if "kv_ectl" in l], out
    assert any("header defaults" in l for l in out), out


def test_registry_defaults_without_guard(tmp_path):
    t = _tree(tmp_path, guard="// no guard\n")
    (t / "physical/die_plan/qwen_kvsys/cores/harden/ectlk_q/qkd_ectl3_kiss_st_cols.sv").write_text(
        GUARD.replace("built_for_other_params", "unused_stub"))  # guard pattern gone; registry = module defaults
    reg = {"entries": [{"die": "qwen_kvsys", "module": f"qkd_ectlk_q{k}", "params": {"QK_ISSUE_AGE": 37, "RESPONSE_LAT": 26}}
                       for k in range(4)]}
    (t / "tools/die_plan/hard_core_built_params.json").write_text(json.dumps(reg))
    out = A.findings(_plan(), "p.json", str(t))
    assert any("kv3_hg_v1p2" in l and "registry" in l for l in out), out
    assert A.findings(_plan(7, 11), "p.json", str(t)) == []


def test_param_wrap_vs_landing_manifest(tmp_path):
    t = _tree(tmp_path)
    v = t / "physical/die_plan/qwen_kvsys/kvhg1_views_1116/kv_cland_w1063_ew_dbe00"
    (v / "landing_evidence").mkdir(parents=True)
    (v / "landing_evidence/manifest.json").write_text(json.dumps({"master": "kv_cland_w1063_ew_dbe00", "D": 4, "width": 1063}))
    p = _plan(7, 11)
    row = dict(inst="cl_0", module="kv_cland_w1063_ew_dbe00", lef=str(v.relative_to(t) / "kv_cland_w1063_ew_dbe00.lef"),
               param_wrap={"base": "ot_dp_clk_landing_cas", "params": {"W": 1063, "DEPTH": 4, "RSTREP": 35}})
    p["partition_types"]["kv3_hg_v1p2"]["hard_cores"].append(row)
    assert A.findings(p, "p.json", str(t)) == []
    p2 = copy.deepcopy(p)
    p2["partition_types"]["kv3_hg_v1p2"]["hard_cores"][-1]["param_wrap"]["params"]["DEPTH"] = 5
    out = A.findings(p2, "p.json", str(t))
    assert any("cl_0" in l and "DEPTH 5" in l and "DEPTH 4" in l for l in out), out


def test_hard_params_sidecar_vs_registry(tmp_path):
    t = _tree(tmp_path)
    reg = {"entries": [{"die": "qwen_kvsys", "module": "dsdv_idx_tx_n32", "params": {"FACE": 2, "RDL": 1}}]}
    (t / "tools/die_plan/hard_core_built_params.json").write_text(json.dumps(reg))
    (t / "hp.json").write_text(json.dumps({"schema": "opentallas.frame_kit.hard_params.v1",
                                           "masters": {"dsdv_idx_tx_n32": {"FACE": 0, "RDL": 1}}}))
    (t / "ab.json").write_text(json.dumps({"base": ".", "hard_params": ["hp.json"]}))
    out = A.findings(_plan(7, 11), "p.json", str(t), asbuilt=str(t / "ab.json"))
    assert any("dsdv_idx_tx_n32" in l and "FACE 0" in l and "FACE 2" in l for l in out), out


def test_never_raises():
    out = A.findings({"partition_types": {"x": {"hard_cores": [None, 3]}}, "ports": "bad", "lanes": 7}, "p", "/nonexistent")
    assert isinstance(out, list) and all(l.startswith("WARN ADV-CORE-PARAM") for l in out)
    out = A.findings(None, "p")
    assert len(out) == 1 and "not checked" in out[0]
