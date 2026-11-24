"""ENTRY-FALL-BIND 11-24 (FABLE flow review c7edf6f5): bind_cells.sv carries the opt-in cells gen_rtl writes into ot_dp_cells.sv
(S81 serdes reset.pin_entry_fall -> ot_dp_rrelay_fn: kit_rtl 'leaf modules without a source'), and the report-only leaf source check"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind
import gen_rtl

BASE = "`timescale 1ns/1ps\nmodule ot_dp_st (input wire clk);\nendmodule\n"


def _plan(**reset):
    return {"partition_types": {"serdes__t2": {"reset": dict(reset)}, "other": {"reset": {}}}}


def test_entry_fall_cell_appended_once():
    out = bind.optional_gen_cells(_plan(pin_entry_fall=True), BASE)
    assert out.startswith(BASE) and gen_rtl.ENTRY_FALL_CELLS in out
    assert out.count("module ot_dp_rrelay_fn ") == 1
    assert bind.optional_gen_cells(_plan(pin_entry_fall=True), out) == out          # already present: not duplicated


def test_plan_without_opt_in_cells_is_byte_identical():
    assert bind.optional_gen_cells(_plan(), BASE) == BASE
    assert bind.optional_gen_cells(_plan(pin_entry_fall=False), BASE) == BASE


def test_bind_cells_match_gen_rtl_for_entry_fall():
    """every module gen_rtl adds to ot_dp_cells.sv for an entry-fall plan is defined in the bind cell text too"""
    import re
    cells = bind.optional_gen_cells(_plan(pin_entry_fall=True), gen_rtl.CELLS)
    gen_mods = set(re.findall(r"^\s*module\s+(\w+)", gen_rtl.CELLS + gen_rtl.ENTRY_FALL_CELLS, re.M))
    assert gen_mods <= set(re.findall(r"^\s*module\s+(\w+)", cells, re.M))


def test_leaf_source_report_names_missing_cell_and_never_raises():
    top = ("module s81_bound_top (input wire clk);\n"
           "    ot_dp_rrelay_fn u_rst_fall_0 (.clk(clk), .d(1'b0), .q());\n"
           "    ot_dp_rrelay u_rst_1 (.clk(clk), .d(1'b0), .q());\n"
           "    ot_s81_serdes__t2 #(.W(4)) u_serdes_t2 (.clk(clk));\n"
           "    hard_pma u_pma (.clk(clk));\n"
           "endmodule\n")
    rep = bind.leaf_source_report(top, BASE, known={"ot_s81_serdes__t2", "hard_pma"})
    assert rep["gate"] == "REPORT" and rep["missing"] == ["ot_dp_rrelay_fn"] and rep["n_missing"] == 1 and rep["checked"] == 4
    fixed = bind.optional_gen_cells(_plan(pin_entry_fall=True), BASE)
    assert bind.leaf_source_report(top, fixed, known={"ot_s81_serdes__t2", "hard_pma"})["missing"] == []
