"""CORE-DIRECT (FABLE-FIX-KV-HGI 11-20): tap_balance.tcl never pads an early core tap whose port is inside the core it
clocks (opt-in OT_TAP_CORE_DIRECT=1; gen_phys.tap_core_direct).  Default off: the padding loop is the old one."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402

TB = (HERE / "tap_balance.tcl").read_text()


def test_default_off(monkeypatch):
    monkeypatch.delenv("OT_TAP_CORE_DIRECT", raising=False)
    assert gen_phys.tap_core_direct({}) is False
    assert gen_phys.tap_core_direct(None) is False
    assert gen_phys.tap_core_direct({"core_tap_direct": True}) is True


def test_env_wins(monkeypatch):
    monkeypatch.setenv("OT_TAP_CORE_DIRECT", "1")
    assert gen_phys.tap_core_direct({}) is True
    monkeypatch.setenv("OT_TAP_CORE_DIRECT", "0")
    assert gen_phys.tap_core_direct({"core_tap_direct": True}) is False
    monkeypatch.setenv("OT_TAP_CORE_DIRECT", "yes")
    with pytest.raises(ValueError):
        gen_phys.tap_core_direct({})


def test_loop_guard_is_flagged_and_before_any_edit():
    i = TB.index("    if {$d <= $tb_tol} continue\n    if {$tb_cdirect && [dict exists $tb_coreonly $n]")
    j = TB.index("    set todo 1\n", i)
    guard = TB[i:j]
    assert "continue\n    }\n" in guard and "dbInst_create" not in guard and "disconnect" not in guard
    # flag default: unset or anything but "1" is off
    assert 'set tb_cdirect [expr {[info exists ::env(OT_TAP_CORE_DIRECT)] && $::env(OT_TAP_CORE_DIRECT) eq "1"}]' in TB
    # only core-only taps are marked, and the mark is rebuilt by every measure
    assert TB.count("dict set tb_coreonly $n 1") == 1
    k = TB.index("proc tb_measure")
    assert "set tb_coreonly {}" in TB[k:k + 400]


def _proc(name):
    i = TB.index(f"proc {name} ")
    depth = 0
    for j in range(TB.index("{", TB.index("}", i)), len(TB)):      # body brace after the arg list
        c = TB[j]
        depth += c == "{"
        depth -= c == "}"
        if depth == 0:
            return TB[i:j + 1]
    raise AssertionError(name)


STUBS = r"""
# minimal odb stand-ins: an object is a proc taking the method name
proc box {name x0 y0 x1 y1} { proc $name {m} [format { switch $m { xMin {return %d} yMin {return %d} xMax {return %d} yMax {return %d} } } $x0 $y0 $x1 $y1] }
proc inst {name box block} {
  proc ${name}_master {m} [format { return %d } $block]
  proc $name {m} [format { switch $m { getName {return %s} getBBox {return %s} getMaster {return %s_master} } } $name $box $name]
}
proc iterm {name inst} { proc $name {m} [format { return %s } $inst] }
namespace eval ord { proc get_db_block {} { return blk } }
proc blk {m p} { global ITERMS; return [expr {[dict exists $ITERMS $p] ? [dict get $ITERMS $p] : "NULL"}] }
box core_box 0 0 216000 216000
box other_box 300000 0 516000 216000
inst coreA core_box 1
inst coreB other_box 1
inst flopC core_box 0
iterm itA coreA; iterm itA2 coreA; iterm itB coreB; iterm itC flopC
set ITERMS [dict create coreA/clk itA coreA/clk2 itA2 coreB/clk itB flopC/CLK itC]
box port_in 107900 107900 108100 108100
box port_out 250000 100000 250100 100100
proc bt_in {m} { return port_in }
proc bt_out {m} { return port_out }
"""


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh")
@pytest.mark.parametrize("cores,bt,want", [
    ("{coreA/clk clk_c1 0 238}", "bt_in", "coreA"),                               # the KV head-core case
    ("{coreA/clk clk_c1 0 238} {coreA/clk2 clk_c1 0 238}", "bt_in", "coreA"),     # several pins of ONE core
    ("{coreA/clk clk_c1 0 238}", "bt_out", ""),                                   # port outside the core: pad as before
    ("{coreA/clk clk_c1 0 238} {coreB/clk clk_c1 0 238}", "bt_in", ""),           # two cores on one tap
    ("{flopC/CLK clk_c1 0 238}", "bt_in", ""),                                    # not a hard core
    ("{gone/clk clk_c1 0 238}", "bt_in", ""),                                     # unknown pin
    ("{coreA/clk clk_c2 0 238}", "bt_in", ""),                                    # no sink of this tap
])
def test_direct_core(tmp_path, cores, bt, want):
    drv = tmp_path / "drv.tcl"
    drv.write_text(STUBS + _proc("tb_direct_core") + f"\nset tb_cores [list {cores}]\nputs \"R=[tb_direct_core clk_c1 {bt}]\"\n")
    out = subprocess.run(["tclsh", str(drv)], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == f"R={want}"


def test_tcl_complete():
    if shutil.which("tclsh") is None:
        pytest.skip("tclsh")
    out = subprocess.run(["tclsh"], input=f"set f [open {HERE / 'tap_balance.tcl'}]; puts [info complete [read $f]]\n",
                         capture_output=True, text=True)
    assert out.stdout.strip() == "1"


def test_config_line(monkeypatch):
    src = (HERE / "gen_phys.py").read_text()
    assert re.search(r'\*\(\["export OT_TAP_CORE_DIRECT = 1"\] if tap_core_direct\(P\.clock\) else \[\]\),', src)
