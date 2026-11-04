"""FWDCLK-1: 2nd+ forwarded-clock buffer of a source tap gets its own sink location; POST_CTS check of dead exports."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landing_contract as LC  # noqa: E402
from test_cts0114_fwd import _P  # noqa: E402


def _pin(n, s):
    return {"name": n, "kind": "clock", "dir": "out", "source_clock_port": s}


def _plan(*pins):
    return _P({"landing_contract": {"pins": list(pins)}})


STEP = "[$cland_m getHeight] *"


def test_one_export_per_tap_has_no_offset():
    s = LC.export_tcl(_plan(_pin("fclk_out_a", "clk_t1"), _pin("fclk_out_b", "clk_t2")), "T")
    assert STEP not in s


def test_one_export_per_tap_text_is_blockwise_independent():
    """the text of a one-export tap does not depend on the other taps: only source-sharing adds a line."""
    a = LC.export_tcl(_plan(_pin("fclk_out_a", "clk_t1")), "T")
    both = LC.export_tcl(_plan(_pin("fclk_out_a", "clk_t1"), _pin("fclk_out_b", "clk_t2")), "T")
    assert both.startswith(a)


def test_shared_tap_rows_distinct_first_unchanged():
    s = LC.export_tcl(_plan(_pin("fclk_out_a", "clk"), _pin("fclk_out_b", "clk"), _pin("fclk_out_c", "clk"),
                            _pin("fclk_out_d", "clk_t1")), "T")
    assert re.findall(r"\$cland_y \+ (\d+) \* \[\$cland_m getHeight\]", s) == ["1", "2"]
    blocks = re.split(r"(?=^set cland_dst )", s, flags=re.M)[1:]
    assert [STEP in b for b in blocks] == [False, True, True, False]
    for b in blocks:   # the offset is applied before the location is set
        if STEP in b:
            assert b.index(STEP) < b.index("setLocation")


def test_offset_moves_toward_core_centre():
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    line = next(ln for ln in LC.export_tcl(_plan(_pin("a", "clk"), _pin("b", "clk")), "T").split("\n") if STEP in ln)
    def run(y):
        tcl = ("proc m {c} {return 270}\nproc ca {c} {if {$c eq \"yMin\"} {return 0}; return 1000}\n"
               f"set cland_m m\nset cland_ca ca\nset cland_y {y}\n{line}\nputs $cland_y\n")
        return int(subprocess.run(["tclsh"], input=tcl, capture_output=True, text=True, check=True).stdout)
    assert run(100) == 370 and run(900) == 630


MOCK = r"""
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc mk {name body} {proc $name {m args} $body}
mk blk {switch $m {findBTerm {set n [lindex $args 0]; if {[info commands bt_$n] ne ""} {return bt_$n}; return NULL}}}
mk bt_good {switch $m {getNet {return n_good}}}
mk bt_dead {switch $m {getNet {return n_dead}}}
mk n_good {switch $m {getBTerms {return {bt_good}} getITerms {return {y1}} getName {return n_good}}}
mk bt_good2 {switch $m {getIoType {return OUTPUT}}}
mk y1 {switch $m {isOutputSignal {return 1} isInputSignal {return 0} getInst {return b1}}}
mk b1 {switch $m {getITerms {return {a1 y1}} getName {return b1}}}
mk a1 {switch $m {isInputSignal {return 1} isOutputSignal {return 0} getNet {return n_clk}}}
mk n_clk {switch $m {getBTerms {return {bt_clk}} getSigType {return CLOCK} getName {return n_clk}}}
mk bt_clk {switch $m {getIoType {return INPUT} getName {return clk}}}
mk n_dead {switch $m {getBTerms {return {}} getITerms {return {y2}} getName {return n_dead}}}
mk y2 {switch $m {isOutputSignal {return 1} isInputSignal {return 0} getInst {return b2}}}
mk b2 {switch $m {getITerms {return {a2 y2}} getName {return cland_fwd_dead}}}
mk a2 {switch $m {isInputSignal {return 1} isOutputSignal {return 0} getNet {return NULL}}}
"""


def _check(tmp_path, names):
    if not shutil.which("tclsh"):
        pytest.skip("no tclsh")
    txt = LC.export_check_tcl(_plan(*[_pin(n, "clk") for n in names]), "T")
    fail = tmp_path / "FAIL_POSTCTS"
    txt = txt.replace("/work/FAIL_POSTCTS", str(fail))
    # bt_good is an output: its own BTerm on the net must not count as the source
    mock = MOCK.replace("mk bt_good {switch $m {getNet {return n_good}}}",
                        "mk bt_good {switch $m {getNet {return n_good} getIoType {return OUTPUT} getName {return good}}}")
    script = tmp_path / "check.tcl"
    script.write_text(mock + txt)
    r = subprocess.run(["tclsh", str(script)], capture_output=True, text=True)
    return r, fail


def test_check_passes_live_port(tmp_path):
    r, fail = _check(tmp_path, ["good"])
    assert r.returncode == 0, r.stderr
    assert "OT_CLAND_EXPORT_CHECK good: OK clk" in r.stdout and not fail.exists()


def test_check_stops_on_dead_port(tmp_path):
    r, fail = _check(tmp_path, ["good", "dead"])
    assert r.returncode != 0 and "OT_CLAND_EXPORT_CHECK FAIL 1 dead" in r.stderr
    assert "cland_fwd_dead input has no net" in fail.read_text()


def test_no_exports_no_check():
    assert LC.export_check_tcl(_plan(), "T") == ""


def test_check_uses_vector_bterm_name():
    s = LC.export_check_tcl(_plan(_pin("fclk_out_o", "clk")), "T", frozenset({"fclk_out_o"}))
    assert "{fclk_out_o[0]}" in s


def test_cts_post_sources_check_when_present():
    t = (HERE / "cts_post.tcl").read_text()
    assert "landing_export_check.tcl" in t and "file exists" in t


def test_export_source_tap_moves_only_planned_taps(monkeypatch):
    import export_source_tap as EST
    pins = [_pin("fclk_out_a", "clk"), _pin("fclk_out_b", "clk"), _pin("fclk_out_c", "clk"), _pin("fclk_out_d", "clk")]
    pins[0]["source_clock_tap"], pins[1]["source_clock_tap"], pins[2]["source_clock_tap"] = "clk_t1", "clk", "clk_t9"
    raw = {"partition_types": {"T": {"clock": {"landing_contract": {"pins": pins}}}, "U": {}}}
    monkeypatch.setattr(EST.S, "Plan", lambda r: None)
    monkeypatch.setattr(EST.S, "tap_grid", lambda P, tn: [("clk", 0, 0), ("clk_t1", 1, 1)])
    changed, missing = EST.apply(raw)
    assert changed == {"T": [["fclk_out_a", "clk", "clk_t1"]]} and missing == {"T": [["fclk_out_c", "clk_t9"]]}
    assert [p["source_clock_port"] for p in pins] == ["clk_t1", "clk", "clk", "clk"]
    assert raw["partition_types"]["T"]["clock"]["landing_contract"]["forwarded_clock_only_inputs"] is True
