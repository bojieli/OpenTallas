"""C-STATION-BIT-SCRAMBLE 11-26 (STATION-BITORDER): opt-in OT_FT_LANE_MONO=1 keeps an ft bank in bit order around hard cores.

Runs the REAL face_flops.tcl helpers and the REAL ft-station pass (tclsh, OpenDB mocked) on the real inputs of S81
ot_s81sl_kv_leaf__t3 slot ft3 (testdata/station_bitorder_t3_ft3.json: gen pins.json, ft_stations.txt, the placed macro
boxes + 1.08 um FF-CORE-BOX halo, CORE_AREA, and the 3_place lst seats of kit ot_s81sl_kv_leaf__t3_1125193009).  ft3 is a
landed regs-only slot, k 4, 669 bits; its plan centre line runs on the left edge of rxsb (y 878), vs (y 531) and ve_u_s
(y 184), so the lane offsets of bits ~570-667 put their station targets inside those cores.

Flag off (default): the spiral leaves each core on whichever side is nearest free, station by station, so the high bits
zigzag right / left / right by ~100 um and hop 0 of bit 635 goes from a 356 um plan to > 500 um, as in the placed kit.
Flag on: each bit's chain is planned once (core exits chosen by a small DP over the chain, longest leg first), so no bank
is out of bit order and no bit changes side between stations; 94 hops > 405 um (max 533.8) drop to 3 (max 411.5).
The same harness (_run(mono, fx)) replays any placed kit slot (landed or unlanded) from its own gen inputs.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SRC = (HERE / "face_flops.tcl").read_text()
FIX = json.loads((HERE / "testdata" / "station_bitorder_t3_ft3.json").read_text())
DBU = 1000


def _procs():
    out = []
    for m in re.finditer(r"^proc (\w+) \{", SRC, re.M):
        i = m.start(); depth = 0; groups = 0; k = SRC.index("{", i)
        while groups < 2:
            if SRC[k] == "{":
                depth += 1
            elif SRC[k] == "}":
                depth -= 1
                if depth == 0:
                    groups += 1
            k += 1
        out.append(SRC[i:k])
    return "\n".join(out)


def _station_pass():
    a = SRC.index("set ff_st 0; set ff_st_miss 0")
    return SRC[a:SRC.index("close $ff_out", a)]


def _mock(fx):
    """mocked OpenDB for one ft slot of fx (the fixture schema): landed (ring at the in pin, stations recovered from the out
    port) or unlanded (station 0 = the in-face register at its placed seat fx['st0'], stations chained by ff_next_station)"""
    sl, k = fx["slot"], fx["k"]
    x0, y0, x1, y1 = (round(v * DBU) for v in fx["core"])
    lines = [
        "set ot_ff_t0 [clock milliseconds]; set ot_ff_tl $ot_ff_t0",
        f"set ff_dbu {DBU}; set ff_sw 54; set ff_rh 270; set ff_cpitch [expr {{$ff_sw * 40}}]",
        f"set ff_x0 {x0}; set ff_y0 {y0}; set ff_x1 {x1}; set ff_y1 {y1}",
        "set ff_ns_stride 1; set ff_ns_inset 0; set ff_gocc {}; set ff_explicit_occ {}; set ff_done {}; set ff_out stdout",
        "set ff_orient {}; for {set y $ff_y0} {$y + $ff_rh <= $ff_y1} {incr y $ff_rh} { dict set ff_orient $y R0 }",
        "set ff_mono_n 0; set ff_mono_bits 0",
        "set ff_core_boxes {" + " ".join("{%d %d %d %d}" % tuple(round(v * DBU) for v in b[:4]) for b in fx["boxes"]) + "}",
        f"set ff_ft [dict create {sl} [list {k} {fx['fin']} {fx['fout']} {{{' '.join(str(v) for v in fx['regs'])}}}]]",
        "proc mff {m} { return [expr {$m eq \"getName\" ? \"DFFHQNx1_ASAP7_75t_R\" : ($m eq \"getWidth\" ? 1080 : 270)}] }",
        "proc flop {b j m args} { global st; set n \"u_ft_" + sl + "_o_${j}_q$b\"",
        "  switch -- $m { getName { return $n } getMaster { return mff } getPlacementStatus { return [expr {[info exists st($n)] ? $st($n) : \"PLACED\"}] }",
        "    getLocation { global st0; return [expr {$j == 0 && [info exists st0($b)] ? $st0($b) : {}}] }",
        "    setPlacementStatus { set st($n) [lindex $args 0] } setOrient { } setLocation { } default { error \"flop $m\" } } }",
        "proc bbx {x y m} { return [expr {$m in {xMin xMax} ? $x : $y}] }",
        "proc bterm {io b x y m args} { switch -- $m { getSigType { return SIGNAL } getIoType { return [expr {$io eq \"i\" ? \"INPUT\" : \"OUTPUT\"}] }",
        "  getName { return \"" + sl + "_${io}\\[$b\\]\" } getNet { return \"N${io}$b\" } getBBox { return \"BB${io}$b\" } default { error \"bterm $m\" } } }",
        "set bts {}",
    ]
    for b, (x, y) in (fx.get("st0") or {}).items():
        lines.append(f"set st0({b}) [list {round(x * DBU)} {round(y * DBU)}]")
    for io, pins in (("i", fx["pins_i"]), ("o", fx["pins_o"])):
        for b, (x, y) in pins.items():
            X, Y = round(x * DBU), round(y * DBU)
            lines.append(f"interp alias {{}} BT{io}{b} {{}} bterm {io} {b} {X} {Y}; interp alias {{}} BB{io}{b} {{}} bbx {X} {Y}; lappend bts BT{io}{b}")
    lines += [
        "proc blk {m args} { global bts; if {$m eq \"getBTerms\"} { return $bts }",
        "  if {$m eq \"findBTerm\"} { if {[regexp {\\[([0-9]+)\\]$} [lindex $args 0] -> b]} { return BTo$b }; return NULL }; error \"blk $m\" }",
        "set ff_blk blk",
    ]
    body = "\n".join(lines) + "\n" + _procs() + "\n"
    body += "proc F {b j} { set a F_${b}_$j; if {[llength [info commands $a]] == 0} { interp alias {} $a {} flop $b $j }; return $a }\n"
    if fx.get("landed", True):
        # landed slot: the ring is at the in pin; the k stations of bit b are the flops u_ft_<slot>_o_<j>[b]
        body += "proc ff_lands_ring {net} { return 1 }\n"
        body += ("proc ff_landed_stations {onet k} { regexp {([0-9]+)$} $onet -> b; set r {}\n"
                 "  for {set j 0} {$j < $k} {incr j} { lappend r [F $b $j] }; return $r }\n")
    else:
        body += "proc ff_lands_ring {net} { return 0 }\n"
        body += "proc ff_from_in {net depth} { if {[regexp {^Ni([0-9]+)$} $net -> b]} { return [F $b 0] }; return {} }\n"
        body += ("proc ff_next_station {f} { regexp {^F_([0-9]+)_([0-9]+)$} $f -> b j\n"
                 f"  if {{$j + 1 < {k}}} {{ return [F $b [expr {{$j + 1}}]] }}; return {{}} }}\n")
    return body


def _run(mono, fx=None):
    """-> ({bit: {station: (x, y) um}}, RESULT line); unlanded slots also carry station 0 (the in-face register seat)"""
    fx = fx or FIX
    if not shutil.which("tclsh"):
        pytest.skip("tclsh unavailable")
    env = "set ::env(OT_FT_LANE_MONO) 1\n" if mono else "catch {unset ::env(OT_FT_LANE_MONO)}\n"
    script = env + _mock(fx) + _station_pass() + '\nputs "RESULT mono=$ff_mono_n bits=$ff_mono_bits miss=$ff_st_miss lst=$ff_lst st=$ff_st"\n'
    r = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, timeout=600)
    assert r.returncode == 0 and not r.stderr, (r.stdout[-2000:] + r.stderr[-2000:])
    seats = {}
    for ln in r.stdout.splitlines():
        p = ln.split("\t")
        m = re.fullmatch(r"l?st(\d+)", p[1]) if len(p) >= 5 else None
        if m:
            seats.setdefault(int(p[4].rsplit("[", 1)[1][:-1]), {})[int(m.group(1))] = (float(p[2]), float(p[3]))
    res = [ln for ln in r.stdout.splitlines() if ln.startswith("RESULT")][0]
    for b, (x, y) in (fx.get("st0") or {}).items():
        if int(b) in seats:
            seats[int(b)][0] = (x, y)
    return seats, res


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def hops(seats):
    return {b: [md(s[j], s[j + 1]) for j in sorted(s) if j + 1 in s] for b, s in seats.items()}


def inversions(seats, j, um=20.0, axis=0):
    """adjacent bits (bit order = pin order along the lane) whose station-j seats are reversed by more than um"""
    bs = [b for b in sorted(seats) if j in seats[b]]
    return sum(1 for a, b in zip(bs, bs[1:]) if seats[a][j][axis] - seats[b][j][axis] > um)


def zigzag(seats, um=50.0, axis=0, landed=True):
    """bits whose cross-lane (x) step between internal stations changes sign by more than um each way (the last step of a
    landed slot runs to the out-face register at the bit's own out pin and is not a station side choice)"""
    n = 0
    for s in seats.values():
        d = [s[j + 1][axis] - s[j][axis] for j in sorted(s) if j + 1 in s]
        if landed:
            d = d[:-1]
        if any(a > um and b < -um or a < -um and b > um for a, b in zip(d, d[1:])):
            n += 1
    return n


@pytest.fixture(scope="module")
def runs():
    return {False: _run(False), True: _run(True)}


def test_fixture_is_the_real_placed_zigzag():
    placed = {int(b): dict(enumerate(tuple(p) for p in v)) for b, v in FIX["placed"].items()}
    h = hops(placed)
    assert max(max(v) for v in h.values()) == pytest.approx(534.3, abs=0.1)        # bit 635 hop 0
    assert max(h[635]) == pytest.approx(534.3, abs=0.1)
    assert zigzag(placed) > 10
    assert sum(1 for v in h.values() for x in v if x > 405) > 60


def test_flag_off_reproduces_the_zigzag(runs):
    seats, res = runs[False]
    assert "mono=0" in res and "miss=0" in res, res
    assert len(seats) == 669
    h = hops(seats)
    assert max(max(v) for v in h.values()) > 480, max(max(v) for v in h.values())
    assert zigzag(seats) > 10
    assert sum(1 for v in h.values() for x in v if x > 405) > 40


def test_flag_on_keeps_bit_order_and_405(runs):
    seats, res = runs[True]
    assert "miss=0" in res, res
    assert len(seats) == 669
    n = int(re.search(r"mono=(\d+)", res).group(1))
    assert n > 100, res
    h = hops(seats)
    # 94 hops > 405 (max 533.8) -> 3 (max 411.5): the rest is bank density in the 32 um corridor between ve_u_m and ve_u_s
    # at y 184 (bits 516-518 left of every core, plan hop 382 + 23-29 um spiral spill), not a side change
    assert sum(1 for v in h.values() for x in v if x > 405) <= 3, sorted((max(v), b) for b, v in h.items())[-5:]
    assert max(max(v) for v in h.values()) < 412.0, sorted((max(v), b) for b, v in h.items())[-5:]
    assert zigzag(seats) == 0
    assert all(inversions(seats, j) == 0 for j in range(FIX["k"] - 1)), [inversions(seats, j) for j in range(FIX["k"])]


def test_flag_on_leaves_targets_outside_cores_unchanged(runs):
    off, _ = runs[False]
    on, _ = runs[True]
    # the low bits never touch a core: same seats with and without the flag
    assert all(off[b] == on[b] for b in range(0, 300)), [b for b in range(0, 300) if off[b] != on[b]][:5]
