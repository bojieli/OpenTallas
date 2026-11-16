"""HCPARAM-ALL: built hard-core parameters vs the parameters the bound RTL really instantiates (S81 idx FACE/RDL/... class)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hard_core_param_all as A

CORE = """
module dsdv_idx_tx_n32 #(
    parameter integer V = 276, parameter integer IK = 4, parameter integer EK = 5,
    parameter integer UID = 8'h5C,  // comment, with comma
    parameter bit SRAM_MACRO = 0, parameter integer MUT = 0,
    parameter integer RDL = 0, parameter integer WDL = 0, parameter integer FACE = 0, parameter integer PDC = 0
)(input ck, input rst);
endmodule
module dsdv_bk_sel_vmtx #(parameter integer V = 276, parameter integer MUT = 0, parameter integer TX_MUT = 0,
    parameter bit TX_SRAM = 1, parameter integer SELE = 1)(input clk, input rst_n);
    dsdv_idx_tx_n32 #(.V(V), .IK(4), .EK(5), .UID(8'h5C), .SRAM_MACRO(TX_SRAM), .MUT(TX_MUT)) u_tx (.ck(clk), .rst(rst_n));
    generate if (SELE != 0) begin : g_sel
        dsdv_other #(.W(V)) u_ids (.ck(clk));
    end else begin : g_nosel
        dsdv_idx_tx_n32 #(.FACE(1)) u_dead (.ck(clk), .rst(rst_n));
    end endgenerate
endmodule
module dsdv_other #(parameter integer W = 1)(input ck); endmodule
"""
TOP = """module s81p_bk_sel__t2 (input clk, input rst_n);
    dsdv_bk_sel_vmtx #(.IDX_MUT(0), .MUT(0), .SELE(1), .SEL_MUT(0), .TX_MUT(0), .TX_SRAM(1'b1), .V(276), .VM_MUT(0)) u_core (.clk(clk), .rst_n(rst_n));
endmodule
"""
SIGNED_VB = dict(V=276, IK=4, EK=5, UID=92, SRAM_MACRO=1, MUT=0, RDL=1, WDL=1, FACE=2, PDC=1)


def _bind(tmp_path, top=TOP, core=CORE):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "s81p_bk_sel__t2.sv").write_text(top)
    (tmp_path / "core.sv").write_text(core)
    (tmp_path / "bind.f").write_text(str(tmp_path / "core.sv") + "\n")
    return tmp_path


def _plan(reg_path, tmp_path, extra=None):
    row = dict(inst="u_bk_sel.u_tx", module="dsdv_idx_tx_n32", lib="physical/s81_die_views/closed_import/dsdv_idx_tx_n32/x_tt.lib")
    row.update(extra or {})
    reg = tmp_path / "reg.json"
    reg.write_text(json.dumps(dict(entries=[dict(module="dsdv_idx_tx_n32", params=reg_path,
                                                 source="signed vb kit config.mk VERILOG_TOP_PARAMS")])))
    return dict(die="s81", partition_types={"bk_sel__t2": dict(module="s81p_bk_sel__t2", hard_cores=[row])}), reg


def test_idx_nested_instance_takes_defaults_not_the_signed_face(tmp_path):
    b = _bind(tmp_path)
    plan, reg = _plan(SIGNED_VB, tmp_path)
    r = A.check_plan(plan, b, None, registry=reg)
    got = {x["param"]: (x["built_value"], x["die_value"], x["kind"]) for x in r["rows"]}
    assert got == {"RDL": (1, 0, "DIFF"), "WDL": (1, 0, "DIFF"), "FACE": (2, 0, "DIFF"), "PDC": (1, 0, "DIFF")}
    assert r["owner"] == "DIE-S81-92" and r["rows_checked"] == 1
    assert "u_core.u_tx" in r["mismatches"][0] and "HARD_CORE" not in r["mismatches"][0]


def test_instance_that_passes_the_built_set_is_clean(tmp_path):
    core = CORE.replace(".MUT(TX_MUT))", ".MUT(TX_MUT), .RDL(1), .WDL(1), .FACE(2), .PDC(1))")
    b = _bind(tmp_path, core=core)
    plan, reg = _plan(SIGNED_VB, tmp_path)
    r = A.check_plan(plan, b, None, registry=reg)
    assert r["mismatches"] == [] and r["rows_checked"] == 1


def test_untaken_generate_branch_is_not_the_core(tmp_path):
    # u_dead (FACE 1) sits in the SELE == 0 branch; SELE is 1 -> only u_tx exists
    b = _bind(tmp_path)
    plan, reg = _plan(SIGNED_VB, tmp_path)
    paths = {x["path"] for x in A.check_plan(plan, b, None, registry=reg)["rows"]}
    assert paths == {"u_core.u_tx"}


def test_parent_parameter_flows_through_the_hierarchy(tmp_path):
    top = TOP.replace(".TX_MUT(0)", ".TX_MUT(3)")
    b = _bind(tmp_path, top=top)
    plan, reg = _plan(dict(SIGNED_VB, MUT=0, RDL=0, WDL=0, FACE=0, PDC=0), tmp_path)
    r = A.check_plan(plan, b, None, registry=reg)
    assert [(x["param"], x["built_value"], x["die_value"]) for x in r["rows"]] == [("MUT", 0, 3)]


def test_die_override_the_built_record_does_not_list(tmp_path):
    core = CORE.replace(".MUT(TX_MUT))", ".MUT(TX_MUT), .PDC(1))")
    b = _bind(tmp_path, core=core)
    plan, reg = _plan(dict(V=276, IK=4, EK=5, UID=92, SRAM_MACRO=1, MUT=0), tmp_path)
    r = A.check_plan(plan, b, None, registry=reg)
    assert [(x["param"], x["kind"], x["built_value"], x["die_value"]) for x in r["rows"]] == [("PDC", "DIE_OVERRIDE", 0, 1)]


def test_labels_and_unresolved_are_not_errors(tmp_path):
    core = CORE.replace("parameter integer MUT = 0,", "parameter integer MUT = 0, parameter INSTANCE = 0,")
    top = TOP.replace(".V(276)", ".V(276)").replace("u_core (", "u_core (")
    b = _bind(tmp_path, top=top, core=core.replace(".MUT(TX_MUT))", ".MUT(TX_MUT), .FACE(`UNDEFINED_MACRO), .INSTANCE(7))"))
    plan, reg = _plan(dict(SIGNED_VB, RDL=0, WDL=0, FACE=2, PDC=0, INSTANCE=1), tmp_path)
    r = A.check_plan(plan, b, None, registry=reg)
    assert r["mismatches"] == [] and r["unresolved"] >= 1


def test_signed_core_without_built_record_fails_unless_allowlisted(tmp_path):
    b = _bind(tmp_path)
    plan, _ = _plan(SIGNED_VB, tmp_path)
    r = A.check_plan(plan, b, None, registry=tmp_path / "missing.json", allow={})
    assert r["no_built"] == 1 and r["rows_checked"] == 0
    assert len(r["mismatches"]) == 1 and "[NO_RECORD]" in r["mismatches"][0] and r["rows"][0]["kind"] == "NO_RECORD"
    ok = A.check_plan(plan, b, None, registry=tmp_path / "missing.json", allow={("s81", "dsdv_idx_tx_n32"): "no record on rtx-pro/AGIdock"})
    assert ok["mismatches"] == [] and ok["allowed"] == 1 and ok["rows_checked"] == 0


def test_param_wrap_rows_stay_with_hard_core_param(tmp_path):
    b = _bind(tmp_path)
    plan, reg = _plan(SIGNED_VB, tmp_path, extra=dict(param_wrap=dict(base="x", params={})))
    assert A.check_plan(plan, b, None, registry=reg)["rows_total"] == 0


def test_view_dir_config_mk_is_the_built_record(tmp_path):
    view = tmp_path / "physical" / "v"
    view.mkdir(parents=True)
    (view / "config.mk").write_text("export VERILOG_TOP_PARAMS = V 276 IK 4 EK 5 UID 92 SRAM_MACRO 1 MUT 0 FACE 2 PDC 1 RDL 1 WDL 1\n")
    b = _bind(tmp_path / "b") if (tmp_path / "b").mkdir() is None else None
    plan, _ = _plan(SIGNED_VB, tmp_path)
    plan["partition_types"]["bk_sel__t2"]["hard_cores"][0]["lib"] = "physical/v/x_tt.lib"
    r = A.check_plan(plan, b, tmp_path, registry=tmp_path / "none.json")
    assert {x["param"] for x in r["rows"]} == {"RDL", "WDL", "FACE", "PDC"} and "config.mk" in r["rows"][0]["source"]


def test_expression_evaluator():
    sc = {"W": 8, "N": 3}.get
    ev = lambda s: A.evaluate(s, sc)
    assert ev("W*2+1") == 17 and ev("8'h5C") == 92 and ev("$clog2(W)") == 3 and ev("N > 2 ? 10 : 20") == 10
    assert ev("1'b1") == 1 and ev("(W << 2) | N") == 35 and ev("UNKNOWN + 1") is None and ev("`M") is None
    assert ev("W != 0 && N == 3") == 1 and ev('"abc"') == "abc"


def test_defines_select_the_ifdef_branch():
    t = "module m #(parameter integer A = `ifdef X 5 `else 7 `endif)(input c);\nendmodule\n"
    assert A.parse_modules(t, "f", ["X"])[0].header[0][1].strip() == "5"
    assert A.parse_modules(t, "f", [])[0].header[0][1].strip() == "7"


def test_owner_lane_per_die():
    assert A.die_owner({"die": {"name": "s81"}}) == "DIE-S81-92" and A.die_owner({"die": {"name": "s81_head"}}) == "HEAD-100"
    assert A.die_owner({"die": {"name": "qwen_compute"}}) == "DIE-QC-103" and A.die_owner({"die": "qwen_kvsys"}) == "KV-102"


class _Binder:
    def __init__(self, plan, base, types=None, ab=None):
        self.plan, self.base, self.types, self.ab = plan, str(base), types or plan["partition_types"], ab or {}


def test_bind_gate_returns_errors_and_honours_the_off_switch(tmp_path, monkeypatch):
    b = _bind(tmp_path)
    plan, reg = _plan(SIGNED_VB, tmp_path)
    orig = A.check_plan
    monkeypatch.setattr(A, "check_plan", lambda *a, **k: orig(*a, registry=reg, **k))
    errs = A.gate(_Binder(plan, tmp_path), b, [str(tmp_path / "core.sv")])
    assert len(errs) == 1 and errs[0].startswith("HARD_CORE_PARAM_ALL type bk_sel__t2 row u_bk_sel.u_tx")
    monkeypatch.setenv("OT_HCPARAM_ALL", "0")
    assert A.gate(_Binder(plan, tmp_path), b, []) == []


def test_view_shared_by_instances_with_different_parameters(tmp_path):
    top = ("module s81p_bk_sel__t2 (input clk, input rst_n);\n"
           "  dsdv_idx_tx_n32 #(.FACE(2)) u_a (.ck(clk), .rst(rst_n));\n  dsdv_idx_tx_n32 #(.FACE(0)) u_b (.ck(clk), .rst(rst_n));\nendmodule\n")
    b = _bind(tmp_path, top=top)
    plan, _ = _plan(SIGNED_VB, tmp_path)
    row2 = dict(plan["partition_types"]["bk_sel__t2"]["hard_cores"][0], inst="u_b")
    row1 = dict(row2, inst="u_a")
    plan["partition_types"]["bk_sel__t2"]["hard_cores"] = [row1, row2]
    r = A.check_plan(plan, b, None, registry=tmp_path / "none.json", allow={("s81", "dsdv_idx_tx_n32"): "test"})
    assert [x["kind"] for x in r["rows"]] == ["VIEW_SHARED_DIFF"] and "FACE" in r["mismatches"][0]


def test_registry_keyed_by_module_and_record_sha_survives_a_swapped_view_dir(tmp_path):
    # TRIDX: the swapped view dir has no config.mk and a different path; the registry still resolves by module + record sha
    view = tmp_path / "physical" / "swapped_tridx"
    view.mkdir(parents=True)
    (view / "x_tt.lib").write_text("lib")
    (view / "PROVENANCE.json").write_text(json.dumps(dict(routed_db_sha256="ab" * 32)))
    b = _bind(tmp_path / "b") if (tmp_path / "b").mkdir() is None else None
    plan, reg = _plan(SIGNED_VB, tmp_path)
    plan["partition_types"]["bk_sel__t2"]["hard_cores"][0]["lib"] = "physical/swapped_tridx/x_tt.lib"
    j = json.loads(reg.read_text())
    j["entries"][0]["records"] = ["ab" * 32]
    j["entries"].append(dict(module="dsdv_idx_tx_n32", params=dict(SIGNED_VB, FACE=1), records=["cd" * 32], source="older record"))
    reg.write_text(json.dumps(j))
    r = A.check_plan(plan, b, tmp_path, registry=reg, allow={})
    assert r["rows_checked"] == 1 and {x["param"] for x in r["rows"]} == {"RDL", "WDL", "FACE", "PDC"}
    assert "record sha" in r["rows"][0]["source"] and "older" not in r["rows"][0]["source"]
    # two parameter sets and no sha match -> no record -> error, never a silent pass
    (view / "PROVENANCE.json").write_text(json.dumps(dict(routed_db_sha256="ee" * 32)))
    r = A.check_plan(plan, b, tmp_path, registry=reg, allow={})
    assert r["rows_checked"] == 0 and r["rows"][0]["kind"] == "NO_RECORD"


def test_built_parameter_the_bound_source_does_not_declare_is_an_error(tmp_path):
    # the frozen portfix178 source: no FACE / PDC / MLK / LKL in the module header
    core = CORE.replace("parameter integer FACE = 0, parameter integer PDC = 0", "parameter integer ZZ = 0")
    b = _bind(tmp_path, core=core)
    plan, reg = _plan(SIGNED_VB, tmp_path)
    r = A.check_plan(plan, b, None, registry=reg, allow={})
    nd = {x["param"] for x in r["rows"] if x["kind"] == "NOT_DECLARED"}
    assert nd == {"FACE", "PDC"} and "no such parameter in the die module" in r["mismatches"][0]


def test_module_with_no_source_in_bind_f_is_an_error_when_the_record_has_parameters(tmp_path):
    b = _bind(tmp_path, core="module dsdv_bk_sel_vmtx #(parameter V=1)(input clk, input rst_n);\n  dsdv_idx_tx_n32 #(.V(V)) u_tx (.ck(clk));\nendmodule\n")
    plan, reg = _plan(SIGNED_VB, tmp_path)
    r = A.check_plan(plan, b, None, registry=reg, allow={})
    assert [x["kind"] for x in r["rows"]] == ["NO_SOURCE"]


def test_core_the_die_rtl_does_not_instantiate_is_an_error_unless_allowlisted(tmp_path):
    b = _bind(tmp_path, top="module s81p_bk_sel__t2 (input clk, input rst_n);\nendmodule\n")
    plan, reg = _plan(SIGNED_VB, tmp_path)
    r = A.check_plan(plan, b, None, registry=reg, allow={})
    assert r["not_found"] == 1 and r["rows"][0]["kind"] == "NO_RECORD" and "no instance" in r["rows"][0]["source"]
    r = A.check_plan(plan, b, None, registry=reg, allow={("s81", "dsdv_idx_tx_n32"): "A0 master replaces the inner module"})
    assert r["mismatches"] == [] and r["allowed"] == 1


def test_allowlist_needs_die_and_reason(tmp_path):
    f = tmp_path / "allow.json"
    f.write_text(json.dumps(dict(entries=[dict(die="s81", modules=["a", "b"], reason="r"), dict(die="kv", module="c"),
                                          dict(module="d", reason="no die")])))
    assert A.load_allow(f) == {("s81", "a"): "r", ("s81", "b"): "r"}


def test_memory_macros_are_counted_separately_not_unchecked(tmp_path):
    b = _bind(tmp_path)
    plan, reg = _plan(SIGNED_VB, tmp_path)
    plan["partition_types"]["bk_sel__t2"]["hard_cores"].append(
        dict(inst="u_m", module="ot_sram_1r1w_32x64_m1", lib="physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/x_tt.lib"))
    r = A.check_plan(plan, b, None, registry=reg, allow={})
    assert r["macro"] == 1 and all(x["kind"] != "NO_RECORD" for x in r["rows"])


PVJ_CORE = """
module ot_qwen_tp8_pv_join_t #(parameter integer MUT=0, J_LAT=7, RESET_PIN=0, OUTPUT_LOAD_LOCAL=0)(input wire clk, rst_n);
endmodule
module ot_qwen_tp8_pv_col #(parameter integer MUT=0, RESET_PIN=0)(input wire clk, rst_n);
    ot_qwen_tp8_pv_join_t #(.MUT(MUT),.RESET_PIN(RESET_PIN)) u_join(.clk(clk),.rst_n(rst_n));
endmodule
"""


def _pvj(tmp_path, reset_pin):
    (tmp_path / "rtl").mkdir()
    (tmp_path / "rtl" / "kv3_pv_v1.sv").write_text(
        "module kv3_pv_v1 (input clk, input rst_n);\n"
        f"    ot_qwen_tp8_pv_col #(.MUT(0), .RESET_PIN({reset_pin})) u_col (.clk(clk), .rst_n(rst_n));\nendmodule\n")
    (tmp_path / "core.sv").write_text(PVJ_CORE)
    (tmp_path / "bind.f").write_text(str(tmp_path / "core.sv") + "\n")
    row = dict(inst="u_col.u_join", module="ot_qwen_tp8_pv_join_t",
               lib="physical/die_plan/qwen_kvsys/pvview_1103/views/ot_qwen_tp8_pv_join_t/ot_qwen_tp8_pv_join_t_tt.lib")
    return dict(die="qwen_kvsys", partition_types={"kv3_pv_v1": dict(module="kv3_pv_v1", hard_cores=[row])})


def test_kv_pv_join_registry_record_is_the_signed_wrapper_reset_pin_1(tmp_path):
    # r137: the signed pv_join kit top is a parameterless wrapper whose u_leaf is built #(.J_LAT(7), .MUT(0), .RESET_PIN(1))
    # (signed 6_final.v holds u_leaf.g_reset_pin.rst_q; signed lib has setup/hold on rst_n); config.mk lists no params
    e = [x for x in json.loads(A.REGISTRY.read_text())["entries"]
         if x.get("die") == "qwen_kvsys" and x["module"] == "ot_qwen_tp8_pv_join_t"]
    assert len(e) == 1 and e[0]["params"] == {"J_LAT": 7, "MUT": 0, "RESET_PIN": 1}
    plan = _pvj(tmp_path / "die", 1) if (tmp_path / "die").mkdir() is None else None
    r = A.check_plan(plan, tmp_path / "die", None, registry=A.REGISTRY, allow={})
    assert r["mismatches"] == [] and r["rows_checked"] == 1
    plan = _pvj(tmp_path / "zero", 0) if (tmp_path / "zero").mkdir() is None else None
    r = A.check_plan(plan, tmp_path / "zero", None, registry=A.REGISTRY, allow={})
    assert {(x["param"], x["built_value"], x["die_value"]) for x in r["rows"]} == {("RESET_PIN", 1, 0)}


def test_explicit_unsigned_future_child_not_matched_to_other_signed_module(tmp_path):
    b = _bind(tmp_path)
    plan, reg = _plan(SIGNED_VB, tmp_path, extra=dict(note="UNSIGNED until its kit signs off"))
    row = plan["partition_types"]["bk_sel__t2"]["hard_cores"][0]
    del row["lib"]
    r = A.check_plan(plan, b, None, registry=reg)
    assert r["mismatches"] == [] and r["unsigned"] == 1
    assert r["rows_total"] == 1 and r["rows_checked"] == 0


def test_unsigned_note_does_not_hide_real_signed_view_mismatch(tmp_path):
    b = _bind(tmp_path)
    plan, reg = _plan(SIGNED_VB, tmp_path, extra=dict(note="UNSIGNED old note; now signed"))
    r = A.check_plan(plan, b, None, registry=reg)
    assert r["unsigned"] == 0 and r["rows_checked"] == 1
    assert any(x["param"] == "FACE" for x in r["rows"])


def test_missing_signed_view_is_not_treated_as_future_unsigned(tmp_path):
    b = _bind(tmp_path)
    plan, reg = _plan(SIGNED_VB, tmp_path, extra=dict(note="SIGNED view accidentally missing"))
    del plan["partition_types"]["bk_sel__t2"]["hard_cores"][0]["lib"]
    r = A.check_plan(plan, b, None, registry=reg)
    assert r["unsigned"] == 0 and r["rows_checked"] == 1
    assert any(x["param"] == "FACE" for x in r["rows"])
