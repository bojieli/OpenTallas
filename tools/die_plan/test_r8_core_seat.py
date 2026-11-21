"""R8-CORE-SEAT (FABLE-FIX-QC-STRAP 11-21): budgets.r_r8_core_seat -> OT_R8_CORE_SEAT = 1 in the kit, the pass in core_input_chain.tcl"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import schema as S  # noqa: E402

SRC = (HERE / "core_input_chain.tcl").read_text()


def test_budget_selects_types():
    on = gen_phys.r8_core_seat_on
    assert on({}, "slw_st_a_v2__cl9f076a5c") is False and on({"r_r8_core_seat": False}, "x") is False
    assert on({"r_r8_core_seat": []}, "x") is False
    assert on({"r_r8_core_seat": True}, "anything") is True
    b = {"r_r8_core_seat": ["slw_st_a", "sle_st_a"]}
    assert on(b, "slw_st_a_v2__cl9f076a5c") is True and on(b, "sle_st_a_v1__cl67389ecd") is True
    assert on(b, "sle_ctl__cla4f6f12f") is False and on(b, None) is False


def test_schema_has_the_key():
    sub = S.SCHEMA["properties"]["budgets"]["properties"]["r_r8_core_seat"]
    assert {"type": "boolean"} in sub["anyOf"]


def test_pass_is_opt_in_and_complete():
    i = SRC.index("# R8-CORE-SEAT")
    j = SRC.index("# lever 7 (HOLD-FLOW-R 11-17)")
    blk = SRC[i:j]
    code = "\n".join(ln for ln in blk.split("\n") if not ln.startswith("#"))
    # the whole pass sits behind the env guard: unset = nothing runs
    assert code.lstrip().startswith('if {[info exists ::env(OT_R8_CORE_SEAT)] && $::env(OT_R8_CORE_SEAT) eq "1"} {')
    assert code.count("{") == code.count("}") and code.count("[") == code.count("]")
    # it never moves FIRM / plan-sited cells and only reads the netlist
    assert "nc_mov" in blk and not re.search(r"\b(connect|disconnect|destroy|create|swapMaster)\b", blk.replace("dict create", ""))
    assert "OT_R8_CORE_SEAT pins" in blk
    tclsh = __import__("shutil").which("tclsh")
    if tclsh:
        r = subprocess.run([tclsh], input="puts [info complete [read [open {%s}]]]" % (HERE / "core_input_chain.tcl"), text=True,
                           capture_output=True)
        assert r.stdout.strip() == "1"


def test_cone_regexes():
    fixed = re.compile(r"_f[./](?:r\[[0-9]+\]|q)")
    assert fixed.search("u_bound.u_r8b_strap_r8pad_u_r0_rs_n_c_p_f.q[2]$_DFF_P_")
    assert fixed.search("u_bound.u_r8b_strap_r8pad_u_r0_rs_n_c_p_f.r[3][2]$_DFF_P_")
    assert not fixed.search("u_bound.u_r8b_strap_r8pad_u_r0_rs_n_c_p.r[0][2]$_DFF_P_")
    assert "{_f[./](?:r\\[[0-9]+\\]|q)}" in SRC
