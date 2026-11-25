"""FABLE-FIX-S81-SERDES2 11-17: PHY-REGION-ROWS-1 (no row overlaps a PHY supply region), PG-RAIL-CHECK-1 (every row has connected
VDD/VSS rails), PAD-IN-DIRECT-1 (input macro_pin pads keep their direct net), PG-PIN-CUT-DEFAULT (macro_pin pad types get the PG
face / island cuts) and the two pre-detail-route ECO hooks for existing databases."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import gen_phys as G

HERE = Path(__file__).resolve().parent
TCLSH = shutil.which("tclsh")


def _tcl(script):
    return subprocess.run([TCLSH], input=script, capture_output=True, text=True, check=True).stdout.strip()


# ---------------------------------------------------------------- PHY-REGION-ROWS-1
def test_region_rows_tcl_carries_the_rects_and_the_body():
    t = G.phy_region_rows_tcl([[314.928, 921.24, 2575.69, 1205.82], [10, 20, 30, 40]])
    assert t.splitlines()[1] == "set prr_rects {{314.928 921.24 2575.69 1205.82} {10 20 30 40}}"
    assert "odb::dbRow_destroy $row" in t and t.count("odb::dbRow_create") == 2
    assert t.index("set prr_rects") < t.index("foreach prr_r $prr_rects")


ROW_MODEL = r"""
# minimal odb row model: rows are dicts in ::rows, the hook's odb calls are replaced
namespace eval odb {}
namespace eval ord {}
proc ord::get_db_block {} { return BLK }
set ::rows {}; set ::nrow 0
proc mkrow {name ox oy ns} { set h row[incr ::nrow]; dict set ::rows $h [dict create name $name ox $ox oy $oy ns $ns]
  proc $h {m args} "rowm $h \$m" ; return $h }
proc rowm {h m} { set r [dict get $::rows $h]; set w 54
  switch $m { getBBox { set b bb$h; set x0 [dict get $r ox]; set x1 [expr {$x0 + [dict get $r ns] * $w}]; set y0 [dict get $r oy]
                        proc $b {q} "switch \$q {xMin {return $x0} xMax {return $x1} yMin {return $y0} yMax {return [expr {$y0 + 270}]}}"; return $b }
              getSite { return SITE } getOrigin { return [list [dict get $r ox] [dict get $r oy]] } getName { return [dict get $r name] }
              getOrient { return R0 } getDirection { return HORIZONTAL } getSpacing { return 54 } getSiteCount { return [dict get $r ns] } } }
proc SITE {m} { return 54 }
proc BLK {m} { switch $m { getDbUnitsPerMicron { return 1000 } getRows { return [dict keys $::rows] } } }
proc odb::dbRow_destroy {h} { dict unset ::rows $h }
proc odb::dbRow_create {b name site ox oy ori dir ns sp} { mkrow $name $ox $oy $ns }
"""


@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
def test_overlapping_rows_are_replaced_by_their_outside_pieces():
    # die rows 0..100 um (1851 sites of 0.054); region x 30.024..70.2 (site-aligned west edge), y 10..20
    out = _tcl(ROW_MODEL + """
mkrow below 0 9000 1851          ;# y 9.00..9.27 : below the region, untouched
mkrow thru  0 10260 1851         ;# crosses the region: two pieces
mkrow west  0 10530 600          ;# ends at 32.4 um: overlaps the region by 2.376 um -> trimmed to the region edge
mkrow tiny  29700 10800 10       ;# 29.7..30.24: the outside piece is 6 sites < 20 -> dropped
set prr_rects {{30.024 10 70.2 20}}
source %s
foreach h [dict keys $::rows] { set r [dict get $::rows $h]; puts "[dict get $r name] [dict get $r ox] [dict get $r ns]" }
""" % (HERE / "phy_region_rows.tcl"))
    lines = out.splitlines()
    assert lines[0] == "OT_PHY_REGION_ROWS 1 region(s): 3 overlapping rows replaced by 3 pieces outside the region", lines
    rows = {ln.split()[0]: tuple(map(int, ln.split()[1:])) for ln in lines[1:]}
    assert rows["below"] == (0, 1851)
    assert rows["thru_rw"] == (0, 556) and rows["thru_re"] == (70200, 551)       # 556 * 54 = 30024; 0 + 1300 * 54 = 70200
    assert rows["west_rw"] == (0, 556) and "west_re" not in rows and not any(k.startswith("tiny") for k in rows)
    for name, (ox, ns) in rows.items():
        if name != "below":
            assert ox + ns * 54 <= 30024 or ox >= 70200, (name, ox, ns)             # no piece inside the region


@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
def test_full_width_region_removes_the_rows_inside_it():
    # HEAD hd_serdes form: PHY supply region over the whole die width from y 400 up (phy_pg.json rect 0 400 2885.76 1226.88, no macro).
    # 3047 of its 5672 rows had no rail: the rows inside the region.  They have no piece outside it, so they go; rows below stay.
    out = _tcl(ROW_MODEL + """
mkrow below  80 399600 53400      ;# y 399.60..399.87: untouched
mkrow edge   80 399870 53400      ;# y 399.87..400.14: overlaps the region by 0.14 um -> removed
mkrow inside 80 800010 53400
mkrow top    80 1226610 53400     ;# last row under the region top
set prr_rects {{0 400 2885.76 1226.88}}
source %s
foreach h [dict keys $::rows] { puts [dict get [dict get $::rows $h] name] }
""" % (HERE / "phy_region_rows.tcl"))
    lines = out.splitlines()
    assert lines[0] == "OT_PHY_REGION_ROWS 1 region(s): 3 overlapping rows replaced by 0 pieces outside the region", lines
    assert lines[1:] == ["below"]


# ---------------------------------------------------------------- PG-RAIL-CHECK-1
@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
def test_rail_cover_rule():
    pre = "set ::env(OT_PG_RAIL_CHECK_NO_RUN) 1\nsource %s\n" % (HERE / "pg_rail_check.tcl")
    assert _tcl(pre + "puts [prc::covers {{0 500} {500 1000}} 0 1000 600]") == "1"
    assert _tcl(pre + "puts [prc::covers {{0 300} {1000 2000}} 0 2000 600]") == "0"      # 700 gap
    assert _tcl(pre + "puts [prc::covers {{0 300} {800 2000}} 0 2000 600]") == "1"       # 500 gap tolerated
    assert _tcl(pre + "puts [prc::covers {} 0 2000 600]") == "0"                         # no rail at all
    assert _tcl(pre + "puts [prc::covers {{700 2000}} 0 2000 600]") == "0"               # row starts 700 before the rail


def test_rail_check_fails_closed_and_is_in_the_post_pdn_chain(monkeypatch):
    t = (HERE / "pg_rail_check.tcl").read_text()
    assert 'error "OT_PG_RAIL_CHECK FAIL' in t and "[prc::env OT_PG_RAIL_CHECK_FAIL 1] ne \"0\"" in t
    code = "\n".join(line for line in t.splitlines() if not line.lstrip().startswith("#"))
    for banned in ("_destroy", "_create", "setDoNotTouch", " connect ", "disconnect"):        # read-only
        assert banned not in code, banned
    gp = (HERE / "gen_phys.py").read_text()
    assert 'post_pdn.append("/work/pg_rail_check_hook.tcl")' in gp
    assert gp.index('post_pdn.append("/work/pg_pin_check_hook.tcl")') < gp.index('post_pdn.append("/work/pg_rail_check_hook.tcl")')
    assert 'export PRE_TAPCELL_TCL = /work/phy_region_rows.tcl"] if phy_doms' in gp
    monkeypatch.delenv("OT_PG_RAIL_CHECK", raising=False)
    assert G.pg_rail_check_on()
    monkeypatch.setenv("OT_PG_RAIL_CHECK", "0")
    assert not G.pg_rail_check_on()
    monkeypatch.setenv("OT_PG_RAIL_CHECK", "warn")
    assert G.pg_rail_check_on()


# ---------------------------------------------------------------- PAD-IN-DIRECT-1
def test_pad_dont_touch_rows_carry_the_direction():
    bumps = [dict(port="io_pma_tx", module="ot_s81_pma_txm", pin="pma_tx", dir="output", width=544),
             dict(port="io_pma_rx", module="ot_s81_pma_rxm", pin="pma_rx", dir="input", width=544)]
    tcl = G.pad_bump_dt_tcl(bumps)
    rows = re.search(r"set pdt_rows \{(.*)\}\n", tcl).group(1)
    assert rows == "{io_pma_tx ot_s81_pma_txm pma_tx 544 output} {io_pma_rx ot_s81_pma_rxm pma_rx 544 input}"
    assert '$pdt_dir eq "input" ? [[lindex $pdt_it 0] isInputSignal] : [[lindex $pdt_it 0] isOutputSignal]' in tcl
    gp = (HERE / "gen_phys.py").read_text()
    assert 'bump_out = pad_bumps(P, tn, root=root)' in gp and '[b for b in pad_bumps(P, tn) if b["dir"] == "output"]' not in gp


# ---------------------------------------------------------------- PG-PIN-CUT-DEFAULT
def test_macro_pin_pad_types_get_the_pg_cuts_by_default(monkeypatch):
    monkeypatch.delenv("OT_PG_FACE_CUT", raising=False)
    pma = {"pads": [{"name": "io_pma_rx", "macro_pin": {"inst": "u_prx", "pin": "pma_rx"}}]}
    plain = {"pads": [{"name": "a"}]}
    assert G.macro_pin_pad_type(pma) and not G.macro_pin_pad_type(plain) and not G.macro_pin_pad_type({})
    assert G.pg_face_cut_on(pma) and not G.pg_face_cut_on(plain)
    assert not G.pg_face_cut_on(dict(pma, pg_face_cut=False))            # explicit type key wins
    assert G.pg_face_cut_on(dict(plain, pg_face_cut=True))
    monkeypatch.setenv("OT_PG_FACE_CUT", "1")
    assert G.pg_face_cut_on(plain)


# ---------------------------------------------------------------- ECO hooks for existing databases
@pytest.mark.skipif(TCLSH is None, reason="tclsh not installed")
def test_notch_cut_arithmetic():
    pre = "proc puts_ {a} {}\nset ::env(OT_PG_PIN_NOTCH) 0\nnamespace eval ord {}\nsource %s\n" % (HERE / "pg_pin_notch.tcl")
    assert _tcl(pre + "puts [ppn::cut 0 1000 {{400 600}}]").endswith("{0 400} {600 1000}")
    assert _tcl(pre + "puts [ppn::cut 0 1000 {{-50 200}}]").endswith("{200 1000}")
    assert _tcl(pre + "puts [ppn::cut 0 1000 {{400 600} {500 900}}]").endswith("{0 400} {900 1000}")
    assert _tcl(pre + "puts [ppn::cut 0 1000 {{-5 2000}}]").splitlines()[-1] in ("", "OT_PG_PIN_NOTCH off")


def test_notch_only_removes_vias_of_the_notched_layer():
    t = (HERE / "pg_pin_notch.tcl").read_text()
    body = t[t.index("foreach v $boxes"):t.index("odb::dbSBox_destroy $sb")]
    assert "ppn::via_on $v $L" in body and body.index("ppn::via_on") < body.index("odb::dbSBox_destroy $v")


def test_pad_in_direct_walks_buffer_chains_and_is_generic():
    t = (HERE / "pad_in_direct.tcl").read_text()
    code = "\n".join(line for line in t.splitlines() if not line.lstrip().startswith("#"))
    assert "pma" not in code and "serdes" not in code                     # any die input pin on any block pin
    assert 'string match "BUF*"' in code and "isBlock" in code and "for {set d 0} {$d < 16}" in code
    assert code.index("$mt connect $net") < code.index("odb::dbInst_destroy $i") < code.index("odb::dbNet_destroy $o")


def test_every_generated_kit_runs_the_rail_check_last(monkeypatch):
    import copy
    import tempfile
    import schema
    import test_gen_phys_pg_island_cut as TI
    monkeypatch.delenv("OT_PG_RAIL_CHECK", raising=False)
    P = schema.Plan(copy.deepcopy(TI.PAIR))
    with tempfile.TemporaryDirectory() as d:
        G.write_type_kit(P, "fa", d, [])
        cfg = (Path(d) / "fa" / "config.mk").read_text()
        assert "export POST_PDN_TCL = /work/pg_rail_check_hook.tcl" in cfg or "export POST_PDN_TCL = /work/post_pdn.tcl" in cfg
        assert (Path(d) / "fa" / "pg_rail_check.tcl").read_bytes() == (HERE / "pg_rail_check.tcl").read_bytes()
        # a kit without a PHY supply region: advisory (COORD 11-17, R-MINIMAL)
        assert "set ::env(OT_PG_RAIL_CHECK_FAIL) 0" in (Path(d) / "fa" / "pg_rail_check_hook.tcl").read_text()


def test_rail_check_blocks_only_on_phy_region_kits(monkeypatch):
    monkeypatch.delenv("OT_PG_RAIL_CHECK", raising=False)
    assert G.pg_rail_check_blocking(True) == 1 and G.pg_rail_check_blocking(False) == 0
    monkeypatch.setenv("OT_PG_RAIL_CHECK", "warn")
    assert G.pg_rail_check_blocking(True) == 0
    monkeypatch.setenv("OT_PG_RAIL_CHECK", "fail")
    assert G.pg_rail_check_blocking(False) == 1
    t = (HERE / "pg_rail_check.tcl").read_text()
    assert "ADVISORY_FAIL" in t and "opentallas.pg_rail_check.v1" in t
    assert t.index("pg_rail_check.json") < t.index("error \"OT_PG_RAIL_CHECK FAIL")     # the record is written before a FAIL stops the kit
