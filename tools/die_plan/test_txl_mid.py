"""OT_TXL_MID hook (tools/die_plan/txl_mid.tcl): station geometry, tclsh only."""
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = Path(__file__).resolve().parent / "txl_mid.tcl"
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def run(tmp_path, body, env_on=False):
    t = tmp_path / "t.tcl"
    head = 'set ::env(OT_TXL_MID) 1\n' if env_on else 'array unset ::env OT_TXL_MID\n'
    t.write_text(head + f"source {TCL}\n" + body)
    return subprocess.run(["tclsh", str(t)], capture_output=True, text=True)


def nums(s):
    return [float(x) for x in s.split()]


def test_targets_even(tmp_path):
    r = run(tmp_path, "puts [join [join [ot_txl_mid::targets 0 0 500 1000 4]]]")
    assert r.returncode == 0, r.stderr
    assert nums(r.stdout) == [100, 200, 200, 400, 300, 600, 400, 800]


CORE = "{0 0 1000 1000}"


def test_free_target_stays(tmp_path):
    r = run(tmp_path, f"puts [ot_txl_mid::nearest_free 50 50 {{{{200 200 300 300}}}} {CORE} 5 400]")
    assert nums(r.stdout) == [50, 50]


def test_target_in_macro_moves_to_nearest_free(tmp_path):
    r = run(tmp_path, f"puts [ot_txl_mid::nearest_free 50 50 {{{{45 45 55 55}}}} {CORE} 5 400]")
    x, y = nums(r.stdout)
    assert not (45 <= x <= 55 and 45 <= y <= 55) and abs(x - 50) + abs(y - 50) <= 10


def test_prefers_small_y_move(tmp_path):
    r = run(tmp_path, f"puts [ot_txl_mid::nearest_free 500 500 {{{{480 440 520 560}}}} {CORE} 5 400]")
    x, y = nums(r.stdout)
    assert not (480 <= x <= 520 and 440 <= y <= 560) and y == 500


def test_core_limits_search(tmp_path):
    r = run(tmp_path, f'puts "<[ot_txl_mid::nearest_free 50 50 {{{{-10 -10 1010 1010}}}} {CORE} 5 400]>"')
    assert r.stdout.strip() == "<>"


def test_off_needs_no_openroad(tmp_path):
    r = run(tmp_path, 'puts ok')
    assert r.returncode == 0 and r.stdout.strip() == "ok"


def test_on_without_openroad_fails_loudly(tmp_path):
    r = run(tmp_path, 'puts never', env_on=True)
    assert r.returncode != 0


# ---- mock OpenDB (tclsh): enough of dbBlock/dbInst/dbITerm/dbNet for ot_txl_mid::run ----
MOCK = r'''
namespace eval ord {}
set ::O [dict create]; set ::nid 0
proc obj {kind args} { set n "o[incr ::nid]"; dict set ::O $n [dict merge [dict create kind $kind] $args]; proc $n {m args} "mcall $n \$m {*}\$args"; return $n }
proc g {o k} { dict get $::O $o $k }
proc s {o k v} { dict set ::O $o $k $v }
proc mcall {o m args} {
  switch -- $m {
    getName { return [g $o name] }
    getMaster { return [g $o master] }
    isBlock { return [g $o block] }
    getIoType { return [g $o io] }
    getSigType { return SIGNAL }
    getMTerm { return [g $o mterm] }
    getInst { return [g $o inst] }
    getNet { return [g $o net] }
    getITerms { return [g $o iterms] }
    getPlacementStatus { return [g $o status] }
    setPlacementStatus { s $o status [lindex $args 0] }
    setLocation { s $o x [lindex $args 0]; s $o y [lindex $args 1] }
    getBBox { if {[g $o kind] eq "iterm"} { set i [g $o inst] } else { set i $o }; return [obj box x0 [g $i x] y0 [g $i y] x1 [expr {[g $i x]+2}] y1 [expr {[g $i y]+2}]] }
    xMin { return [g $o x0] } yMin { return [g $o y0] } xMax { return [g $o x1] } yMax { return [g $o y1] }
    getDbUnitsPerMicron { return 1 }
    getCoreArea { return [obj box x0 0 y0 0 x1 100000 y1 100000] }
    getInsts { return [g $o insts] }
  }
}
set ::insts {}
array set ::M {}
foreach {mn blk} {DFF 0 BUFx2 0 INVx1 0 ENC 0 PMA 0} { set ::M($mn) [obj master name $mn block $blk] }
proc mt {nm io} { return [obj mterm name $nm io $io] }
proc net {} { return [obj net iterms {}] }
proc conn {i pin io n} { set t [obj iterm inst $i mterm [mt $pin $io] net $n]; s $i iterms [concat [g $i iterms] $t]; s $n iterms [concat [g $n iterms] $t]; return $t }
proc cell {name m x y {st PLACED}} { set i [obj inst name $name master $::M($m) x $x y $y status $st iterms {}]; lappend ::insts $i; return $i }
# one bit of a chain C: ENC@(ax,0) -> INV -> r0 .. r(N-2) -> q -> BUF -> PMA@(bx,0); every hop has an INV left at GPL x=gx
proc chain {C b N ax bx gx} {
  set e [cell "$C.enc$b" ENC $ax 0]; set n [net]; conn $e Y OUTPUT $n
  set names {}; for {set k 0} {$k < $N-1} {incr k} { lappend names "$C.g_reg.r\\\[$k\\\]\\\[$b\\\]\$_DFF_P_" }; lappend names "$C.q\\\[$b\\\]\$_DFF_P_"
  set out {}; set k 0
  foreach nm $names {
    set v [cell "$C.inv[incr k]_$b" INVx1 $gx 0]; conn $v A INPUT $n; set n [net]; conn $v Y OUTPUT $n
    set f [cell $nm DFF $gx 0]; conn $f D INPUT $n; set n [net]; conn $f QN OUTPUT $n; lappend out $f $v
  }
  set u [cell "$C.buf$b" BUFx2 $gx 0]; conn $u A INPUT $n; set n [net]; conn $u Y OUTPUT $n
  set p [cell "$C.pma$b" PMA $bx 0]; conn $p D INPUT $n
  return [concat $out [list $u]]
}
proc ord::get_db_block {} { return $::BLK }
proc ord::get_db_tech {} { return $::BLK }
'''


def mock_run(tmp_path, body, chains=None):
    env = 'set ::env(OT_TXL_MID_CHAINS) {%s}\n' % chains if chains is not None else 'array unset ::env OT_TXL_MID_CHAINS\n'
    tail = 'set ::BLK [obj block insts $::insts]\n'
    return run(tmp_path, MOCK + env + body + tail +
               'set r [ot_txl_mid::run]\nforeach i $::insts { puts "POS [g $i name] [g $i x] [g $i y]" }\n')


def pos(out):
    return {l.split()[1]: (float(l.split()[2]), float(l.split()[3])) for l in out.splitlines() if l.startswith("POS ")}


BITS = "chain u_txl 0 4 0 1000 0\nchain u_dec.u_rck_transport4 0 4 2000 0 2000\n"


def test_default_moves_txl_only_and_matches_explicit(tmp_path):
    a = mock_run(tmp_path, BITS)
    b = mock_run(tmp_path, BITS, chains="u_txl")
    assert a.returncode == 0 and b.returncode == 0, a.stderr + b.stderr
    assert a.stdout == b.stdout                       # unset == "u_txl": same moves, same log line
    assert "OT_TXL_MID bits moved 1 of 1," in a.stdout and "chain" not in a.stdout
    p = pos(a.stdout)
    assert all(v == ((0, 0) if k.endswith(".pma0") else (2000, 0)) for k, v in p.items() if k.startswith("u_dec."))  # untouched


def test_rck_transport4_chain_even(tmp_path):
    r = mock_run(tmp_path, BITS, chains="u_txl u_dec.u_rck_transport4")
    assert r.returncode == 0, r.stderr
    assert "chain u_dec.u_rck_transport4 bits moved 1 of 1," in r.stdout
    p = pos(r.stdout)
    rows = [p[f"u_dec.u_rck_transport4.g_reg.r\\[{k}\\]\\[0\\]$_DFF_P_"][0] for k in range(3)] + \
           [p["u_dec.u_rck_transport4.q\\[0\\]$_DFF_P_"][0]]
    assert all(abs(a - b) <= 2 for a, b in zip(rows, [1600, 1200, 800, 400]))   # source 2000 -> sink 0, (k+1)/5


def test_hop_cells_move_onto_their_hop(tmp_path):
    r = mock_run(tmp_path, BITS, chains="u_dec.u_rck_transport4")
    p = pos(r.stdout)
    C = "u_dec.u_rck_transport4"
    st = [2000] + [p[f"{C}.g_reg.r\\[{k}\\]\\[0\\]$_DFF_P_"][0] for k in range(3)] + [p[f"{C}.q\\[0\\]$_DFF_P_"][0], 0]
    invs = [p[f"{C}.inv{k}_0"][0] for k in range(1, 5)]
    for k, x in enumerate(invs):                      # the D inverter of station k sits mid-hop (station k-1 -> k)
        assert abs(x - (st[k] + st[k + 1]) / 2) <= 2   # iterm centre vs cell origin: 1-um mock cells
    assert abs(p[f"{C}.buf0"][0] - (st[4] + st[5]) / 2) <= 2   # q -> PMA buffer mid-hop
    assert "hop cells moved 5" in r.stdout
