"""KW-FIX-25/AUTORENDER 11-06: advisory layout PNGs + smells.json of every kit build.  Local, no Docker/OpenROAD: the smell
calculator on small dumps, and the flow.sh hook (grt183_make.sh patch, layout_render_hook.sh) with a fake openroad."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CF = ROOT / "physical/common_flow"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
sys.path.insert(0, str(CF))
import core_flow  # noqa: E402
import kit_resume as KR  # noqa: E402
import layout_smells as LS  # noqa: E402

HOOK = CF / "layout_render_hook.sh"
WRAP = CF / "grt183_make.sh"
LAYERS = ["L\tM2\t2\tHORIZONTAL\t0.036", "L\tM3\t3\tVERTICAL\t0.036", "L\tM4\t4\tHORIZONTAL\t0.048", "L\tM5\t5\tVERTICAL\t0.048"]


def dump(tmp_path, lines, stage="grt", die=(0, 0, 200, 100)):
    d = "\t".join(str(v) for v in die)
    head = ["H\t%s\t%d\t0\ttop" % (stage, len([l for l in lines if l.startswith("I\t")])), "D\t" + d, "C\t" + d] + LAYERS
    p = tmp_path / "dump.tsv"
    p.write_text("\n".join(head + list(lines)) + "\n")
    return str(p)


def inst(i, master, x, y, w=1.0, h=1.0, name=None, block=0, top=0):
    return "I\t%s\t%s\t%s\t%d\t%d\t%g\t%g\t%g\t%g" % (i, name or "u" + str(i), master, block, top, x, y, x + w, y + h)


def pin(name, net, x, y, io="INPUT", sig="SIGNAL", layer="M4"):
    return "P\t%s\t%s\t%s\t%s\t%s\t%g\t%g\t%g\t%g" % (name, net, sig, io, layer, x, y, x, y)


def net(name, *terms, sig="SIGNAL"):
    return "N\t%s\t%s\t%s" % (name, sig, " ".join(terms))


def L(i, mt="A", sig="SIGNAL", xy=""):
    return "%s:%s:INPUT:%s:%s" % (i, mt, sig, xy)


def O(i, mt="Y"):
    return "%s:%s:OUTPUT:SIGNAL:" % (i, mt)


def test_opposite_face_traces_through_buffers(tmp_path):
    # west pin, a buffer next to it, its flop at x=190 (0.95 W); the near pin's flop stays next to the pin
    p = dump(tmp_path, [pin("far", "n1", 0, 50), pin("near", "n3", 0, 20),
                        inst(1, "BUFx2_ASAP7_75t_R", 1, 50), inst(2, "DFFHQNx1_ASAP7_75t_R", 190, 50), inst(3, "DFFHQNx1_ASAP7_75t_R", 5, 20),
                        net("n1", L(1)), net("n2", O(1), L(2, "D")), net("n3", L(3, "D"))])
    c = LS.compute(p)["checks"]["opposite_face_pins"]
    assert c["flag"] and c["value"] == 1 and c["pins_checked"] == 2
    o = c["offenders"][0]
    assert o["pin"] == "far" and o["face"] == "W" and o["ratio"] > 0.9 and o["x"] == 0 and o["y"] == 50


def test_opposite_face_output_pin_uses_its_driver(tmp_path):
    # output on the N face, driver at the S edge through one inverter: 0.9 H
    p = dump(tmp_path, [pin("o", "n2", 100, 100, io="OUTPUT"), inst(1, "DFFHQNx1_ASAP7_75t_R", 100, 5), inst(2, "INVx1_ASAP7_75t_R", 100, 95),
                        net("n1", O(1, "QN"), L(2)), net("n2", O(2))])
    c = LS.compute(p)["checks"]["opposite_face_pins"]
    assert c["value"] == 1 and c["offenders"][0]["face"] == "N"


def test_pin_track_use(tmp_path):
    # 300 M4 pins in 15 um of the W face: 300 / (20 / 0.048) = 0.72; 10 pins on the E face stay low
    pins = [pin("a[%d]" % i, "a%d" % i, 0, 10 + i * 0.05) for i in range(300)] + [pin("b[%d]" % i, "b%d" % i, 200, 10 + i) for i in range(10)]
    c = LS.compute(dump(tmp_path, pins))["checks"]["pin_track_use"]
    assert c["flag"] and c["value"] == pytest.approx(0.72, abs=0.001)
    o = c["offenders"][0]
    assert (o["face"], o["layer"], o["pins"]) == ("W", "M4", 300) and o["x"] == 0
    assert 10 < o["y"] < 25


def test_channel_guides_vs_tracks(tmp_path):
    # vertical 1-um channel between two macros, blocked up to M5: tracks = 1/0.036 (M3) + 1/0.048 (M5) = 48.6; 60 nets on M3 through it
    lines = [inst(1, "ram", 10, 10, 50, 80, block=1, top=5), inst(2, "ram", 61, 10, 50, 80, block=1, top=5)]
    for i in range(60):
        lines += [net("c%d" % i, ""), "G\tc%d\t3\t60.2\t0\t60.8\t100" % i]
    r = LS.compute(dump(tmp_path, lines))
    c = r["checks"]["channel_tracks"]
    assert c["source"] == "grt_guides" and c["flag"]
    o = [x for x in c["offenders"] if x["b"] != "die edge"][0]
    assert o["gap_um"] == 1 and o["nets"] == 60 and o["tracks"] == pytest.approx(48.6, abs=0.1) and o["x"] == 60.5


def test_channel_estimate_is_labelled_and_no_macro_is_no_flag(tmp_path):
    lines = [inst(1, "ram", 10, 10, 50, 80, block=1, top=5), inst(2, "ram", 61, 10, 50, 80, block=1, top=5), inst(3, "DFFHQNx1_ASAP7_75t_R", 60.5, 2),
             inst(4, "DFFHQNx1_ASAP7_75t_R", 60.5, 97), net("n", O(3, "QN"), L(4, "D"))]
    c = LS.compute(dump(tmp_path, lines, stage="place"))["checks"]["channel_tracks"]
    assert c["source"] == "flight_bbox_estimate" and "ESTIMATE" in c["method"]
    c = LS.compute(dump(tmp_path, [pin("a", "a", 0, 1)]))["checks"]["channel_tracks"]
    assert c["value"] is None and not c["flag"]


@pytest.mark.parametrize("along", ["V", "H"])
def test_place_channel_selects_pressure_after_scoring_wider_gaps(tmp_path, along):
    # Forty 1-um gaps hide a 9-um gap with 500 complete crossings and 437.5 tracks.
    def xy(x, y):
        return (x, y) if along == "V" else (y, x)

    lines = [inst(i, "ram", *xy(x, 10), *xy(2, 80), block=1, top=5)
             for i, x in enumerate([10 + 3*i for i in range(41)] + [141], 1)]
    for i in range(500):
        n = "wide%d" % i
        lines.extend([net(n), pin(n + "a", n, *xy(132, 20)), pin(n + "b", n, *xy(141, 80))])
    p = dump(tmp_path, lines, stage="place", die=(0, 0, 200, 200))
    r = LS.check_channels(LS.Design(p), set())
    assert r["flag"] and r["channels"] > 40 and len(r["offenders"]) == LS.TOP
    top = r["offenders"][0]
    assert (top["a"], top["b"], top["along"], top["gap_um"]) == ("u41", "u42", along, 9)
    assert top["nets"] == 500 and top["tracks"] == 437.5
    assert top["use"] == pytest.approx(1.143)


def clock_tree_lines():
    # entry at the SW corner; root buffer 1 -> branch buffers 2 (near west) and 3 (far east) -> flops 4 and 5, which are related
    return [pin("clk", "c0", 0, 0, sig="CLOCK"), inst(1, "BUFx4_ASAP7_75t_R", 100, 50), inst(2, "BUFx4_ASAP7_75t_R", 20, 50), inst(3, "BUFx4_ASAP7_75t_R", 180, 50),
            inst(4, "DFFHQNx1_ASAP7_75t_R", 20, 60), inst(5, "DFFHQNx1_ASAP7_75t_R", 180, 60), inst(6, "AND2x2_ASAP7_75t_R", 100, 60),
            net("c0", L(1), sig="CLOCK"), net("c1", O(1), L(2), L(3), sig="CLOCK"), net("c2", O(2), L(4, "CLK", "CLOCK"), sig="CLOCK"), net("c3", O(3), L(5, "CLK", "CLOCK"), sig="CLOCK"),
            net("q", O(4, "QN"), L(6)), net("x", O(6), L(5, "D"))]


def test_clock_entry_divergence(tmp_path):
    c = LS.compute(dump(tmp_path, clock_tree_lines()))["checks"]["clock"]
    e = c["entry"]
    # centroid (100.5, 60.5) from (0, 0) = 161 um, limit 0.4 * 300 = 120
    assert e["flag"] and e["value"] == pytest.approx(161, abs=1) and e["threshold"] == 120
    d = c["divergence"]
    # last common cell = buffer 1; both branches 80 + 10: under 200
    assert d["value"] == pytest.approx(90, abs=2) and not d["flag"] and d["max_unshared_levels"] == 2
    assert d["offenders"][0]["last_common"] == "u1"
    assert c["flag"]


def test_clock_divergence_not_computable_at_place(tmp_path):
    lines = [pin("clk", "c0", 100, 0, sig="CLOCK"), inst(1, "DFFHQNx1_ASAP7_75t_R", 100, 40), net("c0", L(1, "CLK", "CLOCK"))]
    c = LS.compute(dump(tmp_path, lines, stage="place"))["checks"]["clock"]
    assert c["divergence"]["computable"] is False and c["over_macro"]["value"] == 0.0 and not c["entry"]["flag"]


def test_clock_found_from_clk_pin_without_sigtype_and_over_macro(tmp_path):
    lines = [pin("ck", "c0", 0, 50), inst(1, "DFFHQNx1_ASAP7_75t_R", 190, 50), inst(2, "ram", 50, 20, 100, 60, block=1, top=4),
             net("c0", L(1, "CLK")), "G\tc0\t4\t0\t49\t190\t51"]
    r = LS.compute(dump(tmp_path, lines))["checks"]
    assert r["clock"]["over_macro"]["flag"] and r["clock"]["over_macro"]["value"] == 100
    assert r["clock"]["flag"] and r["clock"]["over_macro"]["offenders"][0]["macro"] == "u2"
    assert r["opposite_face_pins"]["value"] == 0     # the clock pin is not judged as a data pin


def test_fanout_spread_through_buffers(tmp_path):
    lines = [inst(1, "DFFHQNx1_ASAP7_75t_R", 10, 10), inst(2, "BUFx2_ASAP7_75t_R", 11, 10), inst(3, "AND2x2_ASAP7_75t_R", 150, 10), inst(4, "AND2x2_ASAP7_75t_R", 12, 12),
             net("n1", O(1, "QN"), L(2)), net("n2", O(2), L(3), L(4))]
    c = LS.compute(dump(tmp_path, lines))["checks"]["fanout_spread"]
    assert c["flag"] and c["count"] == 1 and c["offenders"][0]["driver"] == "u1" and c["offenders"][0]["fanout"] == 2
    assert c["value"] == pytest.approx(140, abs=0.1)


def test_local_density(tmp_path):
    # one 10-um bin holding 8x 1 um x 10 um cells = 0.8; beside it 0.1
    cells = [inst(i, "AND2x2_ASAP7_75t_R", 20 + i, 20, 1, 10) for i in range(8)] + [inst(50, "AND2x2_ASAP7_75t_R", 40, 40, 1, 10), inst(51, "FILLERxp5", 41, 40, 9, 10)]
    c = LS.compute(dump(tmp_path, cells))["checks"]["local_density"]
    assert c["flag"] and c["value"] == pytest.approx(0.8) and c["bins_over"] == 1
    assert (c["offenders"][0]["x"], c["offenders"][0]["y"]) == (25, 25)
    assert c["offenders"][1]["density"] == pytest.approx(0.1)       # the filler is not counted


def test_density_edge_sliver_and_taps_are_not_peaks(tmp_path):
    # DENSITY-CHECK-FIX 11-23: core 0..104 -> last bin column is a 4-um sliver (under half a bin); tap cells on it, and a dense sliver, are no density
    die = (0, 0, 104, 100)
    cells = [inst(i, "TAPCELL_ASAP7_75t_R", 100 + (i % 4), 20 + 10 * (i // 4), 1, 10) for i in range(16)]
    cells += [inst(100 + i, "AND2x2_ASAP7_75t_R", 102.5, 50 + i, 1, 1) for i in range(5)]          # 5 um2 on a 4 x 10 um2 sliver
    cells += [inst(200, "AND2x2_ASAP7_75t_R", 20, 20, 1, 2)]
    c = LS.compute(dump(tmp_path, cells, die=die))["checks"]["local_density"]
    assert not c["flag"] and c["value"] == pytest.approx(0.02) and c["bins"] == 1 and not c["lumps"]


def test_density_lump_is_flagged_even_when_each_bin_is_under_threshold(tmp_path):
    # 12 x 10 bins at 0.4 (> lump_density 0.3, < local_density 0.7) = 12000 um2 connected: a soft block packed tight
    die = (0, 0, 200, 200)
    cells = [inst(i, "AND2x2_ASAP7_75t_R", 20 + 10 * (i % 12), 30 + 10 * (i // 12), 1, 40) for i in range(120)]
    c = LS.compute(dump(tmp_path, cells, die=die))["checks"]["local_density"]
    assert c["flag"] and c["value"] == pytest.approx(0.4) and c["bins_over"] == 0
    assert c["lump_count"] == 1 and c["lumps"][0]["bins"] == 120 and c["lumps"][0]["area_um2"] == 12000
    assert c["offenders"][0]["kind"] == "lump" and c["offenders"][0]["instances"] == 120
    one = LS.one_line(dict(stage="place", checks={"local_density": c}))
    assert "lump(1, 120 bins" in one


def _fixture_density(name, tmp_path):
    import gzip
    p = tmp_path / (name + ".tsv")
    p.write_bytes(gzip.open(HERE / "testdata/layout_density" / (name + "_place.tsv.gz")).read())
    return LS.compute(str(p))["checks"]["local_density"]


def test_kv3_hg_v1p5_place_interior_lump_flagged_not_edge(tmp_path):
    # real KV hg place (FABLE-RC-KV 11-23): g_ex_0 packed ~10x the die median in the centre channel; the 1.385 peaks were outline strips
    c = _fixture_density("kv3_hg_v1p5", tmp_path)
    assert c["flag"] and c["lump_count"] == 1
    lp = c["lumps"][0]
    assert lp["bins"] > 200 and lp["area_um2"] > 20000 and 0.4 < lp["density"] < 0.7
    assert 540 < lp["x"] < 680 and 700 < lp["y"] < 800 and lp["bbox_um"][0] < 570 and lp["bbox_um"][2] > 700
    assert c["value"] < 1.2 and all(r["x"] < 1270 for r in c["offenders"])


def test_kv3_sys_SD_v1_place_clean_density_not_flagged(tmp_path):
    c = _fixture_density("kv3_sys_SD_v1", tmp_path)
    assert not c["flag"] and c["lump_count"] == 0 and c["value"] < 0.7


def test_big_db_says_not_computable(tmp_path):
    p = dump(tmp_path, [pin("a", "a", 0, 1), inst(1, "AND2x2_ASAP7_75t_R", 5, 5), inst(2, "ram", 50, 20, 100, 60, block=1, top=4)])
    r = LS.compute(p)["checks"]
    for k in ("opposite_face_pins", "channel_tracks", "clock", "fanout_spread"):
        assert r[k]["computable"] is False and not r[k]["flag"], k
    assert r["pin_track_use"]["computable"] and r["local_density"]["computable"]


def test_big_db_sampled_connectivity_is_computable_and_labelled(tmp_path):
    """VIS-REOWN 11-25 (COORD: connectivity smells 'not computable' on big KV/QC DBs): layout_render.tcl now dumps sampled nets on a big DB
    with an S line; the four connectivity checks compute and say they are sampled lower bounds"""
    lines = [inst(1, "DFFHQNx1_ASAP7_75t_R", 10, 10), inst(2, "BUFx2_ASAP7_75t_R", 11, 10), inst(3, "AND2x2_ASAP7_75t_R", 150, 10),
             inst(4, "AND2x2_ASAP7_75t_R", 12, 12), net("n1", O(1, "QN"), L(2)), net("n2", O(2), L(3), L(4)), "S\t7\t2\t14"]
    p = dump(tmp_path, lines)
    doc = LS.compute(p)
    for k in ("opposite_face_pins", "channel_tracks", "fanout_spread"):
        assert doc["checks"][k]["computable"], k
    for k in LS.CONN_CHECKS:                       # (clock: this fixture has no clock net, so it stays 'no clock' and unlabelled)
        if doc["checks"][k]["computable"]:
            assert doc["checks"][k]["sampled"] == {"k": 7, "nets_kept": 2, "nets_total": 14} and "SAMPLED big DB" in doc["checks"][k]["method"], k
    assert doc["checks"]["fanout_spread"]["flag"] and doc["sampled_connectivity"]["k"] == 7
    assert "sampled connectivity 1/7 (2 of 14 nets)" in doc["summary"]
    assert "sampled" not in LS.compute(dump(tmp_path, lines[:-1]))["summary"]          # small DB: unchanged


def test_layout_render_samples_instead_of_skipping_big_db_connectivity():
    t = (CF / "layout_render.tcl").read_text()
    assert "no connectivity dump" not in t and "proc lr_keep_full" in t and 'puts $f "S\\t$lr_k\\t$lr_kept\\t$lr_total"' in t


TCL_MOCK = r"""
proc mkobj {name body} { proc $name {m args} $body }
# masters
mkobj mBUF {switch $m { getName {return BUFx2_ASAP7_75t_R} isBlock {return 0} }}
mkobj mAND {switch $m { getName {return AND2x2_ASAP7_75t_R} isBlock {return 0} }}
mkobj mDFF {switch $m { getName {return DFFHQNx1_ASAP7_75t_R} isBlock {return 0} }}
mkobj mRAM {switch $m { getName {return ram} isBlock {return 1} }}
foreach {i m} {iBUF mBUF iAND mAND iDFF mDFF iRAM mRAM} { mkobj $i "return $m" }
foreach {t n} {tA A tCLK CLK tY Y} { mkobj $t "return $n" }
proc it {inst mt} { set nm it_${inst}_$mt; mkobj $nm "switch \$m { getInst {return $inst} getMTerm {return $mt} }"; return $nm }
proc mknet {name sig bterms its} { mkobj $name "switch \$m { getSigType {return $sig} getBTerms {return {$bterms}} getITerms {return {$its}} getName {return $name} }" }
mknet nPlain SIGNAL {} [list [it iAND tA] [it iDFF tY]]
mknet nRep SIGNAL {} [list [it iBUF tA] [it iAND tY]]
mknet nPort SIGNAL {bt1} [list [it iAND tA]]
mknet nMacro SIGNAL {} [list [it iRAM tA] [it iAND tY]]
mknet nClkPin SIGNAL {} [list [it iDFF tCLK]]
mknet nClk CLOCK {} {}
mknet nPwr POWER {} {}
"""


@pytest.mark.skipif(not __import__("shutil").which("tclsh"), reason="no tclsh")
def test_lr_keep_full_keeps_ports_macros_clocks_and_repeater_nets(tmp_path):
    t = (CF / "layout_render.tcl").read_text()
    i = t.index("proc lr_keep_full")
    j = t.index("\n}\n", i) + 3
    (tmp_path / "k.tcl").write_text(TCL_MOCK + t[i:j] + "foreach n {nPlain nRep nPort nMacro nClkPin nClk nPwr} { puts \"$n [lr_keep_full $n]\" }\n")
    out = subprocess.run(["tclsh", str(tmp_path / "k.tcl")], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    got = dict(l.split() for l in out.stdout.split("\n") if l.strip())
    assert got == {"nPlain": "0", "nRep": "1", "nPort": "1", "nMacro": "1", "nClkPin": "1", "nClk": "1", "nPwr": "1"}


TCL_RENDER_MOCK = r"""
proc read_db {path} {}
namespace eval ord {
    proc get_db_block {} { return mock_block }
    proc get_db {} { return mock_db }
}
proc mock_db {method} { return mock_tech }
proc mock_tech {method} { return {} }
proc mock_block {method} {
    switch $method {
        getName { return mock }
        getDbUnitsPerMicron { return 1000 }
        getDieArea - getCoreArea { return mock_box }
        getGCellGrid { return [expr {$::env(MOCK_GRID) ? "mock_grid" : "NULL"}] }
        default { return {} }
    }
}
proc mock_grid {method} { return 1 }
proc mock_box {method} {
    return [expr {$method in {xMin yMin} ? 0 : 100000}]
}
namespace eval gui {
    proc set_display_controls {args} { puts "visibility [join $args |]" }
    proc set_heatmap {name args} { puts "settings $name" }
    proc dump_heatmap {name path} {
        puts "dump $name"
        if {$name eq "RUDY" || $::env(MOCK_ROUTING_CSV)} {
            set f [open $path w]
            puts $f "x0,y0,x1,y1,value (%)"
            puts $f "20,20,25,25,80"
            close $f
        }
    }
}
proc save_image {args} { puts "image [file tail [lindex $args end]]" }
source [lindex $argv 0]
"""


@pytest.mark.skipif(not __import__("shutil").which("tclsh"), reason="no tclsh")
@pytest.mark.parametrize(
    "label,odb,grid,routing_csv,diagnostic,heatmaps,images",
    [
        ("place", "3_5_place_dp.odb", "0", "0", "0", [], ["density", "layout"]),
        ("cts", "4_cts.odb", "0", "0", "0", [], ["density", "layout"]),
        ("4_1_cts", "4_1_cts.odb", "1", "1", "1", [], ["density", "layout"]),
        ("postplace", "5_2_route.odb", "1", "1", "1", [], ["density", "layout"]),
        ("-custom", "5_1_grt.odb", "1", "1", "1", [], ["density", "layout"]),
        ("grt", "4_cts.odb", "1", "1", "1", [], ["density"]),
        ("grt", "5_1_grt.odb", "1", "1", "0", ["Routing"], ["congestion", "density"]),
        ("route", "5_2_route.odb", "1", "1", "1", ["Routing"], ["congestion", "wires"]),
        ("route", "5_2_route.odb", "0", "0", "0", [], ["wires"]),
        ("grt", "5_1_grt-failed.odb", "1", "0", "0", ["Routing"], ["density"]),
        ("grt", "5_1_grt-failed.odb", "1", "0", "1", ["Routing", "RUDY"], ["congestion", "density"]),
    ],
)
def test_renderer_dispatches_heatmaps_only_for_routed_checkpoints(
    tmp_path, label, odb, grid, routing_csv, diagnostic, heatmaps, images,
):
    script = tmp_path / "render.tcl"
    script.write_text(TCL_RENDER_MOCK)
    env = dict(
        os.environ, OT_LR_LABEL=label, OT_LR_ODB=str(tmp_path / odb),
        OT_LR_OUT=str(tmp_path), OT_LR_TOOLS=str(CF), OT_LR_KEEP_DUMP="1",
        OT_LR_RUDY=diagnostic, MOCK_GRID=grid, MOCK_ROUTING_CSV=routing_csv,
    )
    result = subprocess.run(
        ["tclsh", str(script), str(CF / "layout_render.tcl")],
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "OT_LR script stopped" not in result.stdout, result.stdout
    trace = result.stdout.splitlines()
    assert [line.removeprefix("dump ") for line in trace if line.startswith("dump ")] == heatmaps
    assert [line.removeprefix("image ") for line in trace if line.startswith("image ")] == [
        f"{name}.png" for name in images
    ]
    if not heatmaps:
        assert "settings Routing" not in trace and "settings RUDY" not in trace
        assert not any(line.endswith("Congestion|visible|true") for line in trace)
    assert (tmp_path / "dump.tsv").read_text().startswith(f"H\t{label}\t")


def test_main_writes_outputs_and_congestion_skips_macros(tmp_path):
    p = dump(tmp_path, clock_tree_lines() + [inst(9, "ram", 120, 10, 50, 20, block=1, top=4)])
    csv = tmp_path / "c.csv"
    csv.write_text("x0,y0,x1,y1,value (%)\n130,15,131,16,100\n30,30,31,31,95\n60,30,61,31,40\n")
    out, marks, one = tmp_path / "s.json", tmp_path / "m.tsv", tmp_path / "o.txt"
    assert LS.main([p, "--out", str(out), "--congestion", str(csv), "--marks", str(marks), "--one", str(one), "--odb", "/x.odb"]) == 0
    doc = json.loads(out.read_text())
    assert doc["schema"] == LS.SCHEMA and doc["advisory"] is True and set(doc["checks"]) == set(LS.MARK_TAG)
    assert all({"value", "threshold", "flag", "offenders", "computable", "method"} <= set(c) for c in doc["checks"].values())
    assert doc["grt_congestion"]["max_pct"] == 95 and doc["grt_congestion"]["gcells_outside_macros"] == 2
    assert "HOT" in marks.read_text() and "CK" in marks.read_text()
    assert one.read_text().startswith("grt ")


def test_rudy_fallback_is_labelled_and_no_congestion_source(tmp_path):
    p = dump(tmp_path, clock_tree_lines())
    csv = tmp_path / "c.csv"
    csv.write_text("x0,y0,x1,y1,value (%)\n30,30,31,31,123\n")
    doc = LS.compute(p, str(csv), None, "rudy")
    assert doc["grt_congestion"]["source"] == "rudy" and "ESTIMATE" in doc["grt_congestion"]["method"] and "RUDY max 123%" in doc["summary"]
    assert "grt_congestion" not in LS.compute(p, str(csv), None, "none")


# ----- the hook: skipped / never non-zero / bounded / keeps the stage status, with a fake openroad


def hook_kit(tmp_path, cfg=""):
    k = tmp_path / "work"; r = k / "run/results/asap7/t/base"
    r.mkdir(parents=True)
    (k / "config.mk").write_text(cfg)
    for f in core_flow.LAYOUT_RENDER_FILES:
        (k / f).write_bytes((CF / f).read_bytes())
    for f in ("3_5_place_dp.odb", "5_1_grt.odb", "5_2_route.odb"):
        (r / f).write_text("odb " + f)
    return k, r


def fake_or(tmp_path, body):
    f = tmp_path / "fake_openroad"
    f.write_text("#!/bin/bash\necho \"$OT_LR_LABEL $OT_LR_ODB\" >> %s/or_calls.txt\n%s\n" % (tmp_path, body))
    f.chmod(0o755)
    return f


def run_hook(k, tmp_path, stage, rc="0", env=None, or_body="exit 0"):
    e = dict(os.environ, OT_GRT183_WORK=str(k), OPENROAD_EXE=str(fake_or(tmp_path, or_body)), **(env or {}))
    e.pop("RESULTS_DIR", None)
    return subprocess.run(["bash", str(k / "layout_render_hook.sh"), stage, rc], env=e, capture_output=True, text=True, timeout=120)


def or_calls(tmp_path):
    p = tmp_path / "or_calls.txt"
    return p.read_text().splitlines() if p.exists() else []


@pytest.mark.parametrize("env,cfg", [({"OT_LAYOUT_RENDER": "0"}, ""), ({}, "export OT_LAYOUT_RENDER = 0\n")])
def test_hook_opt_out(tmp_path, env, cfg):
    k, r = hook_kit(tmp_path, cfg)
    p = run_hook(k, tmp_path, "5_2_route", env=env)
    assert p.returncode == 0 and or_calls(tmp_path) == [] and not (k / "run/layout_review").exists()


def test_hook_other_stage_does_nothing(tmp_path):
    k, r = hook_kit(tmp_path)
    assert run_hook(k, tmp_path, "4_1_cts").returncode == 0 and or_calls(tmp_path) == []


def test_hook_renders_once_per_odb_and_catches_up_resumed_stages(tmp_path):
    k, r = hook_kit(tmp_path)
    before = {f.name: (f.read_bytes(), f.stat().st_mtime_ns) for f in r.iterdir()}
    assert run_hook(k, tmp_path, "3_5_place_dp").returncode == 0
    assert [c.split()[0] for c in or_calls(tmp_path)] == ["place"]
    assert run_hook(k, tmp_path, "5_1_grt").returncode == 0
    assert [c.split()[0] for c in or_calls(tmp_path)] == ["place", "grt"]      # place not redone, stamp matches
    assert run_hook(k, tmp_path, "5_2_route").returncode == 0
    assert [c.split()[0] for c in or_calls(tmp_path)] == ["place", "grt", "route"]
    assert before == {f.name: (f.read_bytes(), f.stat().st_mtime_ns) for f in r.iterdir()}      # stage outputs untouched
    assert sorted(x.name for x in (k / "run/layout_review").iterdir()) == ["grt", "place", "route", "summary.txt"]


@pytest.mark.parametrize("body", ["exit 3", "kill -SEGV $$", "echo noise; exit 139"])
def test_hook_never_returns_non_zero_on_render_failure(tmp_path, body):
    k, r = hook_kit(tmp_path)
    p = run_hook(k, tmp_path, "5_1_grt", or_body=body)
    assert p.returncode == 0 and "OT_LAYOUT_RENDER grt" in p.stdout and "ERROR" not in p.stdout


def test_hook_is_timeout_bounded(tmp_path):
    k, r = hook_kit(tmp_path)
    (r / "3_5_place_dp.odb").unlink()
    t0 = time.time()
    p = run_hook(k, tmp_path, "5_1_grt", env={"OT_LAYOUT_RENDER_TIMEOUT": "2"}, or_body="exec sleep 100")
    assert p.returncode == 0 and time.time() - t0 < 40 and "render rc 124" in p.stdout


def test_hook_no_odb_or_no_tools_or_missing_results(tmp_path):
    k, r = hook_kit(tmp_path)
    for f in r.iterdir():
        f.unlink()
    assert run_hook(k, tmp_path, "5_2_route").returncode == 0 and or_calls(tmp_path) == []
    r.rmdir()
    assert run_hook(k, tmp_path, "5_2_route").returncode == 0
    (k / "layout_render.tcl").unlink()
    assert run_hook(k, tmp_path, "5_2_route").returncode == 0


def test_hook_failed_grt_renders_failed_odb_and_failed_place(tmp_path):
    k, r = hook_kit(tmp_path)
    (r / "5_1_grt.odb").unlink()
    (r / "5_1_grt-failed.odb").write_text("x")
    run_hook(k, tmp_path, "5_1_grt", "1")
    assert any(c.startswith("grt ") and c.endswith("5_1_grt-failed.odb") for c in or_calls(tmp_path))
    assert run_hook(k, tmp_path, "3_3_place_gp", "0").returncode == 0      # a place step that passed is not a render point


FLOW = '#!/usr/bin/env bash\nset -euo pipefail\n\nexit ${FAKE_RC:-0}\n'


def wrap_kit(tmp_path, with_hook=True):
    k, r = hook_kit(tmp_path)
    if not with_hook:
        for f in core_flow.LAYOUT_RENDER_FILES:
            (k / f).unlink()
    s = tmp_path / "scripts"; s.mkdir()
    (s / "flow.sh").write_text(FLOW)
    (s / "global_route.tcl").write_text("  source_step_tcl PRE GLOBAL_ROUTE\n")
    return k, r, s


@pytest.mark.parametrize("rc", [0, 7])
def test_wrapper_patches_flow_sh_and_stage_status_survives(tmp_path, rc):
    k, r, s = wrap_kit(tmp_path)
    e = dict(os.environ, OT_GRT183_WORK=str(k), OT_GRT183_SCRIPTS=str(s), OPENROAD_EXE=str(fake_or(tmp_path, "exit 9")), FAKE_RC=str(rc))
    e.pop("RESULTS_DIR", None)
    p = subprocess.run(["bash", str(WRAP), "bash", str(s / "flow.sh"), "5_1_grt", "global_route"], env=e, capture_output=True, text=True, timeout=120)
    assert p.returncode == rc, p.stdout + p.stderr
    t = (s / "flow.sh").read_text()
    assert t.count("OT_LAYOUT_RENDER hook") == 1 and t.splitlines()[1] == "set -euo pipefail" and "trap '" in t.splitlines()[2]
    assert "grt" in " ".join(or_calls(tmp_path))
    p = subprocess.run(["bash", str(WRAP), "true"], env=e, capture_output=True, text=True, timeout=120)
    assert (s / "flow.sh").read_text() == t       # idempotent


def test_wrapper_without_kit_hook_leaves_flow_sh(tmp_path):
    k, r, s = wrap_kit(tmp_path, with_hook=False)
    e = dict(os.environ, OT_GRT183_WORK=str(k), OT_GRT183_SCRIPTS=str(s))
    assert subprocess.run(["bash", str(WRAP), "true"], env=e, capture_output=True, text=True, timeout=60).returncode == 0
    assert (s / "flow.sh").read_text() == FLOW


def test_kit_carries_the_files_and_resume_treats_them_as_inert(tmp_path):
    core_flow.stage_grt183(tmp_path)
    for f in core_flow.LAYOUT_RENDER_FILES:
        assert (tmp_path / f).read_bytes() == (CF / f).read_bytes()
        assert KR.is_gate_root(f), f
