"""VIEW-DEFINES (COORD r535): hard-core views must be bound under the define set they were built with."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import view_define_check as V

RTL = """
module core_bf (input wire clk, output wire q);
`ifdef FORM_SV
    reg a;
`endif
`ifdef FORM_FW
    reg b;
`endif
    leaf u_l (.clk(clk));
endmodule
module core_ba (input wire clk);
    acore u_a (.clk(clk));
endmodule
module acore (input wire clk);
`ifdef FORM_FW
    reg c;
`endif
endmodule
module leaf (input wire clk);
`ifdef LEAF_OPT
    reg d;
`endif
endmodule
module plain (input wire clk);
`ifdef DIE_ONLY
    reg e;
`endif
endmodule
"""


def _tree(tmp, bf_defines, ba_defines=None):
    (tmp / "rtl").mkdir()
    (tmp / "rtl/cores.sv").write_text(RTL)
    (tmp / "rtl/core_bf_bb.v").write_text("module core_bf (input wire clk, output wire q); `ifdef STUB_ONLY `endif endmodule\n")
    for name, d in (("bf", bf_defines), ("ba", ba_defines), ("plain", None)):
        vd = tmp / "views" / name
        vd.mkdir(parents=True)
        (vd / f"core_{name}_tt.lib").write_text("library(x) {}\n")
        if d is not None:
            (vd / f"core_{name}.view.json").write_text(json.dumps(dict(bind_defines=d)))
    plan = {"partition_types": {"t1": {"hard_cores": [
        dict(module="core_bf", lib="views/bf/core_bf_tt.lib"),
        dict(module="core_ba", lib="views/ba/core_ba_tt.lib"),
        dict(module="plain", lib="views/plain/core_plain_tt.lib")]}}}
    return plan


def test_matching_declared_sets_pass(tmp_path):
    plan = _tree(tmp_path, ["FORM_SV", "FORM_FW"], ["FORM_FW"])
    errors, adv, rows = V.check(plan, ["FORM_SV", "FORM_FW"], tmp_path)
    assert errors == []
    assert {r["module"]: r["verdict"] for r in rows}["core_bf"] == "MATCH"


def test_view_built_with_define_the_die_lacks_fails(tmp_path):
    # the S81 D5c case: signed bf built with SVREG+FWPIPE, die set has FWPIPE only
    plan = _tree(tmp_path, ["FORM_SV", "FORM_FW"], ["FORM_FW"])
    errors, _, _ = V.check(plan, ["-DFORM_FW"], tmp_path)
    assert len(errors) == 1 and "core_bf" in errors[0] and "built WITH FORM_SV" in errors[0]


def test_view_built_without_die_define_fails(tmp_path):
    plan = _tree(tmp_path, ["FORM_SV", "FORM_FW"], [])
    errors, _, _ = V.check(plan, ["FORM_SV", "FORM_FW"], tmp_path)
    assert len(errors) == 1 and "core_ba" in errors[0] and "built WITHOUT FORM_FW" in errors[0]


def test_undeclared_view_in_a_tracked_family_fails(tmp_path):
    # the S81 ba0/ba1 case: no declared set, but the RTL reads a define a declared view of the die also reads
    plan = _tree(tmp_path, ["FORM_SV", "FORM_FW"], None)
    errors, _, rows = V.check(plan, ["FORM_SV", "FORM_FW"], tmp_path)
    assert len(errors) == 1 and "core_ba" in errors[0] and "FORM_FW" in errors[0]
    assert {r["module"]: r["verdict"] for r in rows}["core_ba"] == "UNDECLARED_TRACKED"


def test_undeclared_untracked_is_advisory_only(tmp_path):
    plan = _tree(tmp_path, ["FORM_SV", "FORM_FW"], ["FORM_FW"])
    errors, adv, rows = V.check(plan, ["FORM_SV", "FORM_FW", "DIE_ONLY"], tmp_path)
    assert errors == [] and len(adv) == 1 and "plain" in adv[0]


def test_reads_follow_instances_and_skip_bb_stubs(tmp_path):
    _tree(tmp_path, [], None)
    mod, info = V.rtl_index(tmp_path)
    assert V.reads("core_bf", mod, info) == {"FORM_SV", "FORM_FW", "LEAF_OPT"}
    assert V.reads("core_ba", mod, info) == {"FORM_FW"}
    assert "STUB_ONLY" not in set().union(*(m for m, _ in info.values()))


def test_gate_summary(tmp_path):
    plan = _tree(tmp_path, ["FORM_SV", "FORM_FW"], ["FORM_FW"])
    errors, summ = V.gate(plan, {"defines": ["FORM_FW"]}, tmp_path)
    assert summ["errors"] == len(errors) == 1 and summ["views"] == 3
