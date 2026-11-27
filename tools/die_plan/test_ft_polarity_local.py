"""ft_polarity_local.tcl station matching on the real bound FT names (S81 t47 current819 kit: u_bound.u_ft_ft2_o_5 /
u_bound.u_ft_ft6_o_7 last stations; the canonical _sN form) and its opt-in (gen_phys._ft_polarity_local)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
TCL = HERE / "ft_polarity_local.tcl"

NAMES = {   # instance name -> expected station group ('' = not an FT station flop)
    "u_bound.u_ft_ft2_o_5/q[597]$_DFF_P_": "u_bound.u_ft_ft2_o_5",
    "u_bound.u_ft_ft6_o_7/q[22]$_DFF_P_": "u_bound.u_ft_ft6_o_7",
    "u_bound.u_ft_ft2_i_0/q[1]$_DFF_P_": "u_bound.u_ft_ft2_i_0",
    "u_ft_spare_ft2_o_s3/q[1]$_DFF_P_": "u_ft_spare_ft2_o_s3",
    "u_ft_ft2_o_s5/q[1]$_DFF_P_": "u_ft_ft2_o_s5",
    "u_bound.u_ft_ft2_o_5/eq$_DFF_PNN_": "",
    "u_bound.u_ft_ft2_o_5/_1269_": "",
    "u_bound.u_u_lf1_u_vp_g_wr1_u_w.wdo_q[1][14]$_DFF_P_": "",
}


def station_regexes():
    res = re.findall(r"regexp \{(\^[^}]*)\} \$fpl_name -> fpl_group", TCL.read_text())
    assert len(res) == 2 and res[0] == res[1], res      # group scan and placement use one pattern
    return res[0]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_station_regex_matches_bound_and_canonical_names():
    pat = station_regexes()
    script = "".join(f"puts [expr {{[regexp {{{pat}}} {{{n}}} -> g] ? $g : {{-}}}}]\n" for n in NAMES)
    out = subprocess.run(["tclsh"], input=script, capture_output=True, text=True, check=True).stdout.split()
    assert out == [g or "-" for g in NAMES.values()]


def test_opt_in_three_ways(monkeypatch):
    import gen_phys as G
    monkeypatch.delenv("OT_FT_POLARITY_LOCAL", raising=False)
    tn = "ot_s81sl_leaf__t47"
    assert not G._ft_polarity_local({}, tn)
    assert G._ft_polarity_local({"ft_polarity_local": True}, tn)
    assert G._ft_polarity_local({"ft_polarity_local_types": ["ot_s81sl_leaf__t47"]}, tn)
    assert G._ft_polarity_local({"ft_polarity_local_types": ["ot_s81sl_leaf"]}, "ot_s81sl_leaf__t62")
    assert not G._ft_polarity_local({"ft_polarity_local_types": ["ot_s81sl_leaf__t28"]}, tn)
    monkeypatch.setenv("OT_FT_POLARITY_LOCAL", "1")
    assert G._ft_polarity_local({}, tn)


def test_hook_is_shipped_and_sourced():
    src = (HERE / "gen_phys.py").read_text()
    assert '"ft_polarity_local.tcl"' in src
    assert 'export OT_FT_POLARITY_LOCAL = 1' in src
    assert "source /work/ft_polarity_local.tcl" in (HERE / "face_flops.tcl").read_text()


def test_exact_type_rows_emit_canonically_and_default_stays_off(tmp_path, monkeypatch):
    import gen_phys as G
    monkeypatch.delenv("OT_FT_POLARITY_LOCAL", raising=False)
    tn, group = "test_ft", "u_bound.u_ft_test_o_0"
    group_only = {"ft_polarity_local_group_by_type": {tn: group}}
    sites = {"ft_polarity_local_sites_by_type": {tn: [[1, 8.64, 4.86], [0, 8.64, 4.59]]}}
    table = tmp_path / "ft_polarity_local_sites.tsv"
    assert G._ft_polarity_local_exports(sites, "other_ft", tmp_path) == []
    with pytest.raises(ValueError, match="exact group"):
        G._ft_polarity_local_exports(sites, tn, tmp_path)
    assert G._ft_polarity_local_exports(group_only | sites, tn, tmp_path) == [
        "export OT_FT_POLARITY_LOCAL = 1", f"export OT_FT_POLARITY_LOCAL_GROUP = {group}",
        "export OT_FT_POLARITY_LOCAL_SITES = /work/ft_polarity_local_sites.tsv",
    ]
    assert table.read_text() == "0\t8.64\t4.59\n1\t8.64\t4.86\n"
    sites["ft_polarity_local_sites_by_type"][tn].append([0, 9, 5])
    with pytest.raises(ValueError, match="duplicate"):
        G._ft_polarity_local_exports(group_only | sites, tn, tmp_path)
    assert len(G._ft_polarity_local_exports(group_only, tn, tmp_path)) == 2
    assert not table.exists()


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_authored_stock_hook_rejects_stale_or_overlapping_payload_without_moving_any_cell(tmp_path):
    # The mock exports only methods called on the retained QN/INV cone.
    mock = r"""
namespace eval ord {proc get_db_block {} {return blk}}
proc make {handle methods} {
    proc $handle {method args} [list dispatch $methods]
}
proc dispatch {methods} {
    upvar 1 method method args args
    if {$method eq "setLocation"} { lappend ::moves $args; return }
    if {[string match set* $method]} {return}
    return [dict get $methods $method]
}
proc ff_core_hit {boxes x y w h} {
    foreach rect $boxes {
        lassign $rect a b c d
        if {$x<$c && $a<$x+$w && $y<$d && $b<$y+$h} {return 1}
    }
    return 0
}
proc ff_hits_explicit {x y w h} {return 0}
proc ff_pair_row_blocked {r} {return 0}
set moves {}
set ff_x0 4320; set ff_x1 20000; set ff_y0 4320; set ff_y1 9000
set ff_dbu 1000; set ff_sw 54; set ff_rh 270
set ff_orient {4320 R0 4590 MX 4860 R0}
make core {xMin 4320 xMax 20000 yMin 4320 yMax 9000}
make blk {getCoreArea core getInsts {ff0 inv0 ff1 inv1}}
make df {getName DFFHQN getHeight 270 isBlock 0}
make iv {getName INVx1 getHeight 270 getWidth 162 isBlock 0}
make qn {getName QN}
make a {getName A}
foreach bit {0 1} y {4320 4590} {
    set name [format {u_bound.u_ft_test_o_0/q[%s]$_DFF_P_} $bit]
    make ff$bit [dict create getName $name getMaster df getPlacementStatus FIRM getBBox bbox$bit getITerms q$bit]
    make bbox$bit [dict create xMin 4320 xMax 5400 yMin $y yMax [expr {$y+270}]]
    make q$bit [dict create isOutputSignal 1 isInputSignal 0 getMTerm qn getNet net$bit]
    make inv$bit [dict create getName inv$bit getMaster iv getPlacementStatus PLACED]
    make load$bit [dict create isInputSignal 1 getMTerm a getInst inv$bit]
    make net$bit [dict create getBTerms {} getITerms [list q$bit load$bit]]
}
"""
    sites = tmp_path / "sites.tsv"
    script = tmp_path / "run.tcl"
    script.write_text(mock + f"""
set ::env(RESULTS_DIR) {{{tmp_path}}}
set ::env(OT_FT_POLARITY_LOCAL) 1
set ::env(OT_FT_POLARITY_LOCAL_GROUP) u_bound.u_ft_test_o_0
set ::env(OT_FT_POLARITY_LOCAL_SITES) {{{sites}}}
if {{[catch {{source {{{TCL}}}}} problem]}} {{ puts "reject $problem"; puts "moves $moves"; exit 1 }}
puts "moves $moves"
""")
    sites.write_text("0\t8.64\t4.59\n1\t8.64\t4.86\n")
    out = subprocess.run(["tclsh", str(script)], capture_output=True, text=True, check=True)
    assert "launch pairs 2" in out.stdout and "moves {8640 4590} {8640 4860}" in out.stdout
    for rows, reason in (
        ("0\t8.64\t4.59\n", "unexpected"),
        ("0\t8.64\t4.59\n1\t8.64\t4.59\n", "fixed cell"),
        ("0\t8.64\t4.59\n1\t8.641\t4.86\n", "legal row grid"),
    ):
        sites.write_text(rows)
        failed = subprocess.run(["tclsh", str(script)], capture_output=True, text=True)
        assert failed.returncode == 1 and reason in failed.stdout
        assert failed.stdout.splitlines()[-1] == "moves "
