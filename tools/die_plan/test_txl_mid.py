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
foreach {mn blk} {DFF 0 BUFx2 0 INVx1 0 ENC 0 PMA 0 PMAB 1 ENCB 1} { set ::M($mn) [obj master name $mn block $blk] }
proc mt {nm io} { return [obj mterm name $nm io $io] }
proc net {} { return [obj net iterms {}] }
proc conn {i pin io n} { set t [obj iterm inst $i mterm [mt $pin $io] net $n]; s $i iterms [concat [g $i iterms] $t]; s $n iterms [concat [g $n iterms] $t]; return $t }
proc cell {name m x y {st PLACED}} { set i [obj inst name $name master $::M($m) x $x y $y status $st iterms {}]; lappend ::insts $i; return $i }
# one bit of a chain C: ENC@(ax,0) -> INV -> r0 .. r(N-2) -> q -> BUF -> PMA@(bx,0); every hop has an INV left at GPL x=gx
proc chain {C b N ax bx gx {pm PMA} {em ENC}} {
  set e [cell "$C.enc$b" $em $ax 0]; set n [net]; conn $e Y OUTPUT $n
  set names {}; for {set k 0} {$k < $N-1} {incr k} { lappend names "$C.g_reg.r\\\[$k\\\]\\\[$b\\\]\$_DFF_P_" }; lappend names "$C.q\\\[$b\\\]\$_DFF_P_"
  set out {}; set k 0
  foreach nm $names {
    set v [cell "$C.inv[incr k]_$b" INVx1 $gx 0]; conn $v A INPUT $n; set n [net]; conn $v Y OUTPUT $n
    set f [cell $nm DFF $gx 0]; conn $f D INPUT $n; set n [net]; conn $f QN OUTPUT $n; lappend out $f $v
  }
  set u [cell "$C.buf$b" BUFx2 $gx 0]; conn $u A INPUT $n; set n [net]; conn $u Y OUTPUT $n
  set p [cell "$C.pma$b" $pm $bx 0]; conn $p D INPUT $n
  return [concat $out [list $u]]
}
proc ord::get_db_block {} { return $::BLK }
proc ord::get_db_tech {} { return $::BLK }
'''


def mock_run(tmp_path, body, chains=None, face=None):
    env = 'set ::env(OT_TXL_MID_CHAINS) {%s}\n' % chains if chains is not None else 'array unset ::env OT_TXL_MID_CHAINS\n'
    env += 'set ::env(OT_TXL_MID_FACE) %s\n' % face if face is not None else 'array unset ::env OT_TXL_MID_FACE\n'
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


# ---- OT_TXL_MID_FACE (SERDES-TXPIPE 11-14): the macro end's row sits at the macro pin ----
def test_face_targets(tmp_path):
    r = run(tmp_path, "puts [join [join [ot_txl_mid::face_targets 0 0 900 0 3 snk]]]\n"
                      "puts [join [join [ot_txl_mid::face_targets 0 0 900 0 3 src]]]\n"
                      "puts [join [join [ot_txl_mid::face_targets 0 0 900 0 1 snk]]]\n"
                      "puts [join [join [ot_txl_mid::face_targets 0 0 900 0 3 {}]]]")
    assert r.returncode == 0, r.stderr
    l = r.stdout.splitlines()
    assert nums(l[0]) == [300, 0, 600, 0, 900, 0]
    assert nums(l[1]) == [0, 0, 300, 0, 600, 0]
    assert nums(l[2]) == [900, 0]
    assert nums(l[3]) == [225, 0, 450, 0, 675, 0]


FACE_BITS = "chain u_txl 0 4 0 1000 0 PMAB\n"


def _rows(p, C="u_txl"):
    return [p[f"{C}.g_reg.r\\[{k}\\]\\[0\\]$_DFF_P_"][0] for k in range(3)] + [p[f"{C}.q\\[0\\]$_DFF_P_"][0]]


def test_face_sink_macro_last_row_at_pin(tmp_path):
    r = mock_run(tmp_path, FACE_BITS, face="1")
    assert r.returncode == 0, r.stderr
    assert "macro-face anchored 1" in r.stdout
    x = _rows(pos(r.stdout))
    assert all(abs(a - b) <= 3 for a, b in zip(x[:3], [250, 500, 750]))   # k/4 of enc 0 -> pin 1001
    assert abs(x[3] - 1001) <= 12 and not (991.36 <= x[3] <= 1010.64)          # at the pin, just outside its 8.64 halo


def test_face_off_is_even_rule(tmp_path):
    a = mock_run(tmp_path, FACE_BITS)
    b = mock_run(tmp_path, FACE_BITS, face="0")
    assert a.returncode == 0 and b.returncode == 0, a.stderr + b.stderr
    assert a.stdout == b.stdout and "macro-face" not in a.stdout
    x = _rows(pos(a.stdout))
    assert all(abs(u - v) <= 3 for u, v in zip(x, [200, 400, 600, 800]))   # (k+1)/5, unchanged


def test_face_source_macro_first_row_at_pin(tmp_path):
    r = mock_run(tmp_path, "chain u_rxf 0 4 0 1000 0 PMA ENCB\n", chains="u_rxf", face="1")
    assert r.returncode == 0, r.stderr
    assert "macro-face anchored 1" in r.stdout
    x = _rows(pos(r.stdout), "u_rxf")
    assert 1 < x[0] <= 12                                                   # at the source macro pin, outside its halo
    assert all(abs(a - b) <= 4 for a, b in zip(x[1:], [251, 501, 751]))     # k/4 of src pin 1 -> sink 1001


# Production RXNEG hierarchy: falling-edge vector, not an ot_pl_pad.q array.
RXNEG = r"""
for {set bit 0} {$bit < 545} {incr bit} {
  chain u_bound.u_core.u_rxf $bit 1 0 1000 800 PMA ENCB
}
foreach i $::insts {
  set n [g $i name]
  if {[string first {u_rxf.q} $n]>=0} {
    s $i name [string map {{u_rxf.q} {u_rxf_q} {$_DFF_P_} {$_DFF_N_}} $n]
  }
}
"""


def test_rxneg_actual_hierarchy_moves_all_545_bits(tmp_path):
    r = mock_run(tmp_path, RXNEG, chains="u_rxf", face="1")
    assert r.returncode == 0, r.stderr
    assert "chain u_rxf bits moved 545 of 545," in r.stdout
    assert "macro-face anchored 545" in r.stdout
    p = pos(r.stdout)
    stations = {k: v for k, v in p.items() if "u_rxf_q" in k}
    assert len(stations) == 545
    assert all(1 < xy[0] <= 12 for xy in stations.values())


def test_rxneg_missing_valid_bit_refuses_incomplete_width(tmp_path):
    r = mock_run(tmp_path, RXNEG.replace("$bit < 545", "$bit < 544"),
                 chains="u_rxf", face="1")
    assert r.returncode != 0
    assert "RXNEG face width 544, expected 545" in r.stderr


def test_explicit_missing_chain_is_not_silent_zero(tmp_path):
    r = mock_run(tmp_path, BITS, chains="u_rxf", face="1")
    assert r.returncode != 0
    assert "requested chain u_rxf has no register endpoints" in r.stderr


PHASE_PAIR = r"""
chain u_dec.u_face_p_d 0 1 100 1000 800
set ::M(DFFL) [obj master name DFFLQNx2_ASAP7_75t_R block 0]
foreach i $::insts {
  if {[g $i name] eq "u_dec.u_face_p_d.enc0"} {
    s $i name {u_bound.u_core.u_rxf_q\[0\]$_DFF_N_}
    s $i master $::M(DFFL)
  }
}
"""


def test_rxneg_halfcycle_pair_adjacent_when_opted_in(tmp_path):
    body = "set ::env(OT_TXL_MID_RXNEG_PAIR) 1\n" + PHASE_PAIR
    r = mock_run(tmp_path, body, chains="u_dec.u_face_p_d", face="1")
    assert r.returncode == 0, r.stderr
    p = pos(r.stdout)
    src = p[r"u_bound.u_core.u_rxf_q\[0\]$_DFF_N_"]
    dst = p[r"u_dec.u_face_p_d.q\[0\]$_DFF_P_"]
    assert abs(src[0] - dst[0]) + abs(src[1] - dst[1]) <= 10


def test_rxneg_pair_default_off_preserves_even_placement(tmp_path):
    r = mock_run(tmp_path, PHASE_PAIR, chains="u_dec.u_face_p_d", face="1")
    assert r.returncode == 0, r.stderr
    p = pos(r.stdout)
    assert abs(p[r"u_dec.u_face_p_d.q\[0\]$_DFF_P_"][0] - 551) <= 3



def test_rxneg_valid_scalar_face_row_pairs_like_data(tmp_path):
    body = ("set ::env(OT_TXL_MID_RXNEG_PAIR) 1\n"
            + PHASE_PAIR.replace("u_face_p_d", "u_face_p_v")
            + r"""
foreach i $::insts {
  if {[string first {u_face_p_v.q} [g $i name]] >= 0} {
    s $i name {u_bound.u_core.u_dec.u_face_p_v.q$_DFF_P_}
  }
}
""")
    r = mock_run(tmp_path, body, chains="u_dec.u_face_p_v", face="1")
    assert r.returncode == 0, r.stderr
    p = pos(r.stdout)
    src = p[r"u_bound.u_core.u_rxf_q\[0\]$_DFF_N_"]
    dst = p["u_bound.u_core.u_dec.u_face_p_v.q$_DFF_P_"]
    assert abs(src[0] - dst[0]) + abs(src[1] - dst[1]) <= 10



def test_rxneg_valid_launch_halfcycle_also_pairs_locally(tmp_path):
    body = "set ::env(OT_TXL_MID_RXNEG_PAIR) 1\n" + RXNEG + r"""
set ::M(DFFL) [obj master name DFFLQNx2_ASAP7_75t_R block 0]
foreach i $::insts {
  set n [g $i name]
  if {$n eq "u_bound.u_core.u_rxf.enc544"} {
    s $i name {u_bound.u_core.rs_r[1]$_DFF_PN0_}
    s $i master $::M(DFF)
    s $i x 200; s $i y 100
  }
  if {[string first {u_rxf_q\[544\]} $n]>=0} {s $i master $::M(DFFL)}
}
"""
    r = mock_run(tmp_path, body, chains="u_rxf", face="1")
    assert r.returncode == 0, r.stderr
    p = pos(r.stdout)
    src = p["u_bound.u_core.rs_r[1]$_DFF_PN0_"]
    dst = p[r"u_bound.u_core.u_rxf_q\[544\]$_DFF_N_"]
    assert abs(src[0] - dst[0]) + abs(src[1] - dst[1]) <= 10
    assert "bits moved 545 of 545" in r.stdout


COMB_SINK = r'''
set ::M(AND) [obj master name AND2x2_ASAP7_75t_R block 0]
chain u_dec.u_rck_transport4 545 4 0 100 0 AND
set g1 [lindex [lsearch -inline -all -glob $::insts *] end]
set n1 [net]; conn $g1 Y OUTPUT $n1
set g2 [cell "u_dec.u_syn.g_ampipe.cmp" AND 120 0]; conn $g2 A INPUT $n1
set n2 [net]; conn $g2 Y OUTPUT $n2
set am [cell "u_dec.u_syn.g_ampipe.am_a\$_DFF_P_" DFF 5000 0]; conn $am D INPUT $n2
'''


def test_comb_sink_walks_to_register(tmp_path):
    """FAM-S81-SERDES-R7 11-23: a q whose first load is logic spaces its rows to the register the logic feeds
    (am_a), and its cone moves onto the last leg; before this the rows stopped at the gate 100 um away."""
    r = mock_run(tmp_path, COMB_SINK, chains="u_dec.u_rck_transport4")
    assert r.returncode == 0, r.stderr
    assert "comb-sink bits to registers 1, cone cells moved 3" in r.stdout
    p = pos(r.stdout)
    xs = [p[k][0] for k in p if "u_rck_transport4" in k and "DFF" in k]
    assert sorted(xs) == pytest.approx([1000, 2000, 3000, 4000], abs=5)
    q = p["u_dec.u_rck_transport4.q\\[545\\]$_DFF_P_"][0]
    for g in ("u_dec.u_rck_transport4.pma545", "u_dec.u_syn.g_ampipe.cmp"):
        assert q <= p[g][0] <= 5001
    assert p["u_dec.u_syn.g_ampipe.am_a$_DFF_P_"] == (5000, 0)


def test_comb_sink_without_register_keeps_old_endpoint(tmp_path):
    body = "set ::M(AND) [obj master name AND2x2_ASAP7_75t_R block 0]\nchain u_dec.u_rck_transport4 545 4 0 1000 0 AND\n"
    r = mock_run(tmp_path, body, chains="u_dec.u_rck_transport4")
    assert r.returncode == 0, r.stderr
    assert "comb-sink" not in r.stdout
    xs = sorted(v[0] for k, v in pos(r.stdout).items() if "u_rck_transport4" in k and "DFF" in k)
    assert xs == pytest.approx([200, 400, 600, 800], abs=5)
