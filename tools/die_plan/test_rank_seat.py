"""RANK-SEAT (FABLE-FIX-S81-COL-RANKSEAT 11-22): every bit of a wide register rank FIRM on a line instead of a point block.
  plan partition_types[].relay_rank_sites {rank: {line_um, order}}   explicit rows (kit_istations.rank_sites_lines)
  plan budgets.rank_line_types {type regex: {min_bits, span_um, min_um}}   auto lines for packed lane-pad ranks (auto_rank_line)
  rs_rank_line (RANK_TCL) run in tclsh against the REAL ff_put_near of face_flops.tcl and is_dffs of TCL_HEAD.
    python3 -m pytest -q tools/die_plan/test_rank_seat.py"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_phys  # noqa: E402
import kit_istations as K  # noqa: E402
import schema  # noqa: E402

TCLSH = shutil.which("tclsh")
needs_tclsh = pytest.mark.skipif(TCLSH is None, reason="no tclsh")
FF = (HERE / "face_flops.tcl").read_text()


def _proc(src, name):
    i = src.index(f"proc {name} ")
    return src[i:src.index("\n}\n", i) + 3]


# a block of flops with name, location and placement status; the station grid of face_flops.tcl (2.16 x 0.27 um cells)
MOCK = r'''
set ::nid 0; set ::insts {}
proc mk_flop {name x y st} {
  set h ::inst_$::nid; incr ::nid
  set ::nm($h) $name; set ::loc($h) [list $x $y]; set ::st($h) $st
  interp alias {} $h {} inst_cmd $h
  lappend ::insts $h
  if {$st eq "FIRM"} { dict set ::ff_gocc "[expr {int($x / 2160)}],[expr {int($y / 270)}]" 1 }
}
proc inst_cmd {h cmd args} {
  switch -- $cmd {
    getName { return $::nm($h) } getMaster { return master } getPlacementStatus { return $::st($h) }
    setPlacementStatus { set ::st($h) [lindex $args 0]; return } setOrient { return }
    getLocation { return $::loc($h) } setLocation { set ::loc($h) $args; return }
  }
  error "inst $cmd"
}
proc master {cmd args} { switch -- $cmd { getName { return DFFHQNx1_ASAP7_75t_R } getWidth { return 1080 } getHeight { return 270 } } }
proc blk {cmd args} { if {$cmd eq "getInsts"} { return $::insts }; error "blk $cmd" }
proc ff_hits_explicit {args} { return 0 }
proc ff_pair_row_blocked {r} { return 0 }
set ff_blk blk; set ff_dbu 1000
set ff_gocc {}; set ff_x0 0; set ff_y0 0; set ff_x1 1442880; set ff_y1 1278720; set ff_rh 270; set ff_sw 54; set ff_cpitch 2160
set ff_orient {}; set ff_ns_stride 1; set ff_ns_inset 0; set ff_core_boxes {}
set is_miss {}; set is_dff_all_ok 0; set is_dff_lit [dict create]
'''
REPORT = r'''
foreach h $::insts { puts "AT\t$::nm($h)\t[lindex $::loc($h) 0]\t[lindex $::loc($h) 1]\t$::st($h)" }
puts "MISS [llength $is_miss] $is_miss"
'''


def _run(tmp_path, flops, calls, pre=""):
    put = FF[FF.index("proc ff_put_near {f x y} {"):FF.index("ot_ff_tick explicit_reserve_and_landed")]
    body = [MOCK, _proc(FF, "ff_core_hit"), put, _proc(K.TCL_HEAD, "is_dffs"), K.RANK_TCL, f"set ::env(RESULTS_DIR) {{{tmp_path}}}",
            f"set is_fh [open {{{tmp_path}/ot_face_flops.txt}} a]", pre]
    body += [f"mk_flop {{{n}}} {x} {y} {st}" for n, x, y, st in flops] + calls + ["close $is_fh", REPORT]
    f = tmp_path / "t.tcl"
    f.write_text("\n".join(body) + "\n")
    r = subprocess.run([TCLSH, str(f)], capture_output=True, text=True)
    assert r.returncode == 0 and not r.stderr, r.stdout[-2000:] + r.stderr[-2000:]
    at = {}
    for ln in r.stdout.splitlines():
        p = ln.split("\t")
        if p[0] == "AT":
            at[p[1]] = (int(p[2]), int(p[3]), p[4])
    return r.stdout, at


def _rank(inst, reg, n, sep=".", block=(1414800, 639000)):
    """n flops <inst><sep><reg>[b], FIRM in a packed block (10 columns) as the station hook leaves them"""
    out = []
    for b in range(n):
        nm = f"u_bound.{inst}{sep}{reg}".replace("[", "\\[").replace("]", "\\]") + f"\\[{b}\\]$_DFF_P_"
        out.append((nm, block[0] + (b % 10) * 2160, block[1] + (b // 10) * 270, "FIRM"))
    return out


def _bits(at, inst, reg, sep="."):
    key = f"u_bound.{inst}{sep}{reg}".replace("[", "\\[").replace("]", "\\]")
    out = {}
    for n, v in at.items():
        m = re.fullmatch(re.escape(key) + r"\\\[(\d+)\\\]\$_DFF_P_", n)
        if m:
            out[int(m.group(1))] = v
    return out


@needs_tclsh
def test_block_becomes_a_column_line_in_bit_order(tmp_path):
    """col_h9_r0_p3 form: 1,104 bits packed in 21.6 x 29 um at the E edge -> a 180-um line along y, bit 0 at the low end"""
    decoys = [("u_bound.u_lpad_xo_i0.r\\[0\\]\\[5\\]$_DFF_P_", 500000, 500040, "FIRM"), ("u_bound.u_lpad_xo_i0_x.q\\[1\\]$_DFF_P_", 600000, 600210, "PLACED"),
              ("u_bound.u_ist_a_0/eq$_DFF_PN0_", 700000, 700110, "FIRM")]
    out, at = _run(tmp_path, _rank("u_lpad_xo_i0", "q", 1104) + decoys, ["rs_rank_line {u_lpad_xo_i0.r[1] u_lpad_xo_i0.q} 1430 564 1430 744 asc"])
    assert "OT_RELAY_RANK u_lpad_xo_i0.q: 1104 of 1104 bits FIRM on the line (1430, 564) - (1430, 744), 180.0 um, order asc" in out
    b = _bits(at, "u_lpad_xo_i0", "q")
    assert len(b) == 1104 and all(v[2] == "FIRM" for v in b.values()) and len({v[:2] for v in b.values()}) == 1104      # one cell per flop
    ys = [b[k][1] for k in range(1104)]
    assert min(ys) >= 564000 - 2700 and max(ys) <= 744000 + 2700 and max(ys) - min(ys) >= 170000
    assert sum(ys[k + 50] > ys[k] for k in range(0, 1050)) == 1050                                                       # bit order kept along the line
    assert len({v[0] for v in b.values()}) <= 4 and all(abs(v[0] - 1430000) <= 2 * 2160 for v in b.values())             # a line, not a block
    assert at[decoys[0][0]] == (500000, 500040, "FIRM") and at[decoys[1][0]][2] == "PLACED" and at[decoys[2][0]][:2] == (700000, 700110)
    rows = [ln.split("\t") for ln in (tmp_path / "ot_face_flops.txt").read_text().splitlines()]
    assert len(rows) == 1104 and all(r[1] == "rank" and r[4] == "-" for r in rows)
    assert "MISS 0" in out


@needs_tclsh
def test_diagonal_line_gives_every_bit_its_own_row_and_column_band(tmp_path):
    """the turn form: 45 degrees from the corner into the inside of the turn; desc = bit 0 at the far end"""
    out, at = _run(tmp_path, _rank("u_lpad_xo_i0", "q", 1104), ["rs_rank_line {u_lpad_xo_i0.q} 1351 743 1440 654 desc"])
    b = _bits(at, "u_lpad_xo_i0", "q")
    assert len({v[:2] for v in b.values()}) == 1104
    assert b[0][0] > b[1103][0] + 80000 and b[0][1] < b[1103][1] - 80000                 # bit 0 at (1440, 654), the last bit at (1351, 743)
    xs = sorted(v[0] for v in b.values()); ys = sorted(v[1] for v in b.values())
    assert xs[-1] - xs[0] >= 85000 and ys[-1] - ys[0] >= 85000
    per_col = {}
    for v in b.values():
        per_col.setdefault(v[0], []).append(v[1])
    assert max(max(c) - min(c) for c in per_col.values()) <= 16000                       # a band along the diagonal, never a tall block


@needs_tclsh
def test_alternative_name_slash_separator_and_freed_cells(tmp_path):
    """ot_dp_dly names its last stage q; a kept hierarchy writes inst/q[b]; the old block cells are free again"""
    out, at = _run(tmp_path, _rank("u_ist_f_2", "q", 300, sep="/", block=(108000, 54000)),
                   ["rs_rank_line {u_ist_f_2.r[3] u_ist_f_2.q} 400 900 580 900 asc", 'puts "OLD [dict exists $ff_gocc 50,200] [dict exists $ff_gocc 59,229]"'])
    b = _bits(at, "u_ist_f_2", "q", sep="/")
    assert "OT_RELAY_RANK u_ist_f_2.q: 300 of 300" in out and "OLD 0 0" in out
    assert all(400000 - 2 * 2160 <= v[0] <= 580000 + 2 * 2160 and abs(v[1] - 900000) <= 10 * 270 for v in b.values())
    assert b[0][0] < b[150][0] < b[299][0]


@needs_tclsh
def test_two_dimensional_rank_and_untouched_sibling_ranks(tmp_path):
    flops = _rank("u_lpad_x_i0", "r[0]", 64) + _rank("u_lpad_x_i0", "r[1]", 64, block=(900000, 300240)) + _rank("u_lpad_x_i0", "q", 64, block=(950400, 400140))
    out, at = _run(tmp_path, flops, ["rs_rank_line {u_lpad_x_i0.r[0]} 100 100 100 160 asc"])
    assert "OT_RELAY_RANK u_lpad_x_i0.r[0]: 64 of 64" in out
    assert all(abs(v[0] - 100000) <= 2160 for v in _bits(at, "u_lpad_x_i0", "r[0]").values())
    assert all(v[0] >= 900000 for v in _bits(at, "u_lpad_x_i0", "r[1]").values()) and all(v[0] >= 950400 for v in _bits(at, "u_lpad_x_i0", "q").values())


@needs_tclsh
def test_a_rank_without_registers_is_a_reported_miss(tmp_path):
    out, at = _run(tmp_path, _rank("u_lpad_a", "q", 8), ["rs_rank_line {u_lpad_zz.r[0] u_lpad_zz.q} 10 10 10 90 asc"])
    assert "OT_RELAY_RANK SEAT-MISS WARNING rank u_lpad_zz.r[0] u_lpad_zz.q matches no register" in out
    assert "MISS 1 relay_rank_sites:u_lpad_zz.r\\[0\\]" in out or "MISS 1 {relay_rank_sites:u_lpad_zz.r[0]}" in out
    assert (tmp_path / "ot_relay_sites_unmatched.txt").read_text() == "rank:u_lpad_zz.r[0]\n"
    assert all(v[2] == "FIRM" and v[0] >= 1414800 for v in at.values())                  # nothing moved


@needs_tclsh
def test_line_on_the_north_edge_stays_clear_of_the_face_bank_search(tmp_path):
    """row-stride kits: ff_put_near's N/S face search stops when a bank does not fit the pin retention; a rank line never enters it"""
    out, at = _run(tmp_path, _rank("u_lpad_a", "q", 600), ["rs_rank_line {u_lpad_a.q} 600 1278.72 780 1278.72 asc"], pre="set ff_ns_stride 2")
    b = _bits(at, "u_lpad_a", "q")
    assert "600 of 600" in out and "MISS 0" in out                                  # no "NS face bank cannot fit" stop
    assert max(v[1] for v in b.values()) <= 1278720 - 10000 and min(v[1] for v in b.values()) >= 1278720 - 11000 - 40 * 270


def test_plan_rows_become_calls_and_bad_rows_fail_closed():
    t = dict(relay_rank_sites={"u_lpad_xo_i0.q": dict(line_um=[[1440, 654], [1351, 743]], order="desc", note="p3"),
                               "u_lpad_x_i0.r[0]": dict(line_um=[[1421.5, 778], [1421.5, 958]])})
    ln = K.rank_sites_lines("t", t)
    assert ln[0] == K.RANK_TCL and ln[1:] == ["rs_rank_line {u_lpad_x_i0.r[0]} 1421.500 778.000 1421.500 958.000 asc",
                                              "rs_rank_line {u_lpad_xo_i0.q} 1440.000 654.000 1351.000 743.000 desc"]
    assert K.rank_sites_lines("t", {}) == [] and K.relay_sites_lines("t", {}) == []                    # absent = nothing emitted
    assert K.relay_sites_lines("t", t) == ln                                                           # no relay_sites needed
    both = K.relay_sites_lines("t", dict(t, relay_sites={"u_x.q[0]": [1.0, 2.0]}))
    assert both[0] == K.RELAY_TCL and both[-3:] == ln and both.index(ln[0]) > [i for i, x in enumerate(both) if x.startswith("rs_place_all")][0]
    assert K.relay_sites_only_tcl("t", t).count("rs_rank_line {") == 2 + K.RANK_TCL.count("rs_rank_line {")
    for bad in ({"u_a.q": dict(line_um=[[1, 2]])}, {"u_a.q": dict(line_um=[[1, 2], [3, "4"]])}, {"u_a.q": dict(line_um=[[1, 2], [3, 4]], order="up")},
                {"u_a.q": [1, 2]}, {"u_a q": dict(line_um=[[1, 2], [3, 4]])}, {"u_cland_x.q": dict(line_um=[[1, 2], [3, 4]])},
                {"u_a.q": dict(line_um=[[1, 2], [3, 4]], span_um=3)}):
        with pytest.raises(SystemExit):
            K.rank_sites_lines("t", dict(relay_rank_sites=bad))


def test_schema_declares_the_keys_and_the_json_matches():
    tp = schema.SCHEMA["properties"]["partition_types"]["additionalProperties"]["properties"]
    bp = schema.SCHEMA["properties"]["budgets"]["properties"]
    assert tp["relay_rank_sites"]["additionalProperties"]["required"] == ["line_um"]
    assert {"rank_line_types", "grt_cong_iters", "grt_cong_iters_types"} <= set(bp)
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert on_disk["properties"]["partition_types"]["additionalProperties"]["properties"]["relay_rank_sites"] == tp["relay_rank_sites"]
    for k in ("rank_line_types", "grt_cong_iters", "grt_cong_iters_types"):
        assert on_disk["properties"]["budgets"]["properties"][k] == bp[k]


def test_rank_line_cfg_longest_regex_and_defaults():
    b = dict(rank_line_types={"^col_": {}, "^col_h9_r0_p3__": dict(span_um=120, min_bits=512)})
    assert K.rank_line_cfg(b, "col_h9_r0_p6__t1__pv0") == dict(min_bits=512, span_um=180.0, min_um=40.0)
    assert K.rank_line_cfg(b, "col_h9_r0_p3__t1__cl8") == dict(min_bits=512, span_um=120.0, min_um=40.0)
    assert K.rank_line_cfg(b, "ot_s81sl_leaf__t1") is None and K.rank_line_cfg({}, "col_x") is None and K.rank_line_cfg(None, "col_x") is None


CFG = dict(min_bits=256, span_um=180.0, min_um=40.0)
IN_E = dict(dir="in", face="E", order="lsb_low")


def _type(cores=(), bands=()):
    return dict(outline_um=[1442.88, 1278.72], hard_cores=[dict(inst=f"c{i}", origin_um=list(b[:2]), outline_um=[b[2] - b[0], b[3] - b[1]]) for i, b in enumerate(cores)],
                clock=dict(landing_contract=dict(bands={f"b{i}": dict(rect_um=list(b)) for i, b in enumerate(bands)})))


def test_auto_line_straight_stage_is_across_the_travel_direction():
    seg, order = K.auto_rank_line(_type(), (700.0, 600.0), (700.0, 900.0), (700.0, 300.0), IN_E, CFG)        # travelling south
    assert seg == (790.0, 600.0, 610.0, 600.0) and order == "asc"                                             # LEFT of south = east end first
    seg, _ = K.auto_rank_line(_type(), (700.0, 600.0), (300.0, 600.0), (1100.0, 620.0), IN_E, CFG)            # travelling east: LEFT = north
    assert seg == (700.0, 690.0, 700.0, 510.0)
    assert K.auto_rank_line(_type(), (700.0, 600.0), (700.0, 900.0), (700.0, 300.0), dict(IN_E, order="msb_low"), CFG)[1] == "desc"
    assert K.auto_rank_line(_type(), (700.0, 600.0), (700.0, 900.0), (700.0, 300.0), dict(dir="in", face="N"), CFG)[1] == "desc"


def test_auto_line_slides_off_the_edge_and_off_a_core():
    seg, _ = K.auto_rank_line(_type(), (1442.88, 923.256), (1442.88, 1100.7), (1442.88, 625.8), IN_E, CFG)    # p6 r[0]: on the E edge, going south
    assert seg == (1440.88, 923.256, 1260.88, 923.256)                                                        # the whole span into the type
    seg, _ = K.auto_rank_line(_type(cores=[(1300.0, 900.0, 1350.0, 950.0)]), (1442.88, 923.256), (1442.88, 1100.7), (1442.88, 625.8), IN_E, CFG)
    assert seg == (1440.88, 923.256, 1352.88, 923.256)                                                        # stops 2 um short of the core
    assert K.auto_rank_line(_type(cores=[(1410.0, 900.0, 1442.0, 950.0)]), (1430.0, 923.0), (1430.0, 1100.0), (1430.0, 600.0), IN_E, CFG) is None   # site in a core
    assert K.auto_rank_line(_type(cores=[(1300.0, 800.0, 1420.0, 1000.0)]), (1442.88, 923.256), (1442.88, 1100.7), (1442.88, 625.8), IN_E, CFG) is None  # 19 um free < min_um


def test_auto_line_turn_is_a_diagonal_into_the_inside_of_the_turn():
    """col_h9_r0_p3 u_lpad_xo_i0.q: in from the north along the E edge, out to the west; u_cf under it, the xo_i0 landing band north-west"""
    t = _type(cores=[(1131.84, 604.8, 1412.64, 673.92)], bands=[(1313.28, 739.584, 1351.08, 979.548)])
    seg, order = K.auto_rank_line(t, (1442.88, 653.958), (1442.88, 859.566), (1166.394, 604.854), IN_E, CFG)
    assert order == "asc" and seg[:2] == (1440.88, 653.958)                       # right turn: the corner point is the LEFT end, bit 0 there
    dx, dy = seg[2] - seg[0], seg[3] - seg[1]
    assert dx == -dy and -89.0 <= dx <= -87.0                                    # north-west at 45 degrees, stopped by the landing band (+ halo)
    seg, order = K.auto_rank_line(_type(), (300.0, 300.0), (300.0, 100.0), (100.0, 300.0), dict(dir="in", face="S"), CFG)    # north then west = left turn
    assert seg[2:] == (300.0, 300.0) and seg[0] < 300.0 and seg[1] < 300.0 and order == "asc"                                # the inside (south-west) is the LEFT end
    # a turn with no room on the diagonal falls back to a line across the outgoing direction
    t2 = _type(cores=[(1300.0, 660.0, 1436.0, 900.0)])
    seg, _ = K.auto_rank_line(t2, (1440.0, 654.0), (1440.0, 860.0), (1166.0, 605.0), IN_E, CFG)
    assert seg == (1440.0, 564.0, 1440.0, 744.0)                # LEFT of west = the south end


def test_grt_iterations_from_the_plan_and_the_env_wins(monkeypatch):
    monkeypatch.delenv("OT_GRT_CONG_ITERS", raising=False)
    b = dict(grt_cong_iters_types={"^col_": 50, "^col_h10_r2__": 30}, grt_cong_iters=12)
    assert gen_phys._grt_cong_iters(b, "col_h9_r0_p3__t1") == 50 and gen_phys._grt_cong_iters(b, "col_h10_r2__t1") == 30
    assert gen_phys._grt_cong_iters(b, "ot_s81sl_leaf__t1") == 12 and gen_phys._grt_cong_iters({}, "col_x") == 10 and gen_phys._grt_cong_iters() == 10
    monkeypatch.setenv("OT_GRT_CONG_ITERS", "20")
    assert gen_phys._grt_cong_iters(b, "col_h9_r0_p3__t1") == 20
