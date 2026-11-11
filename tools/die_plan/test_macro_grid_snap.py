"""KW-FIX-44 11-10 (COORD, DIE-S81-85 bksel vC2 P at y 201.96): static macro origins snap to the kit track grid"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import macro_grid_snap as M

TRACKS = M.tracks_for("make_tracks M5 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048\n"
                      "make_tracks M4 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048\n")


def lef(tmp, pins_m4=(("a", 0.0, 0.012, 0.192, 0.036), ("b", 0.0, 0.108, 0.192, 0.132)), pins_m5=()):
    body = ""
    for n, x0, y0, x1, y1 in pins_m4:
        body += f"  PIN {n}\n    DIRECTION INPUT ;\n    PORT\n      LAYER M4 ;\n        RECT {x0} {y0} {x1} {y1} ;\n    END\n  END {n}\n"
    for n, x0, y0, x1, y1 in pins_m5:
        body += f"  PIN {n}\n    DIRECTION INPUT ;\n    PORT\n      LAYER M5 ;\n        RECT {x0} {y0} {x1} {y1} ;\n    END\n  END {n}\n"
    body += "  PIN VDD\n    USE POWER ;\n    PORT\n      LAYER M4 ;\n        RECT 0 0.001 10 0.002 ;\n    END\n  END VDD\n"
    p = Path(tmp) / "pk.lef"
    p.write_text(f"MACRO PK\n  CLASS BLOCK ;\n  SIZE 10 BY 10 ;\n{body}END PK\n")
    return p


def pl(p, x, y, inst="u_q.u_s.u_pk", o="R0"):
    return {"inst": inst, "inst_db": inst, "master": "PK", "lef": p, "x": x, "y": y, "o": o}


def test_off_grid_p_snaps_to_row_grid_preferring_216(tmp_path):
    p = lef(tmp_path)
    assert M.off_track(M.lef_master(p, "PK"), 100.0, 201.96, "R0", TRACKS) == {"x": 0, "y": 2}
    out, rows = M.snap_all([pl(p, 100.0, 201.96)], (400.0, 400.0), TRACKS)
    assert (out[0]["x"], out[0]["y"]) == (100.0, 200.88)          # the die owner's on-grid vC3 site
    assert rows[0]["off_track_pins"] == 2 and rows[0]["snapped_um"] == [100.0, 200.88]
    assert M.off_track(M.lef_master(p, "PK"), 100.0, 200.88, "R0", TRACKS) == {"x": 0, "y": 0}


def test_on_grid_macros_untouched_and_no_receipt(tmp_path):
    p = lef(tmp_path)
    src = [pl(p, 100.0, 200.88), pl(p, 120.0, 203.04, inst="u2")]
    out, rows = M.snap_all(src, (400.0, 400.0), TRACKS)
    assert out == src and rows == []
    M.write_receipt(tmp_path, rows)
    assert not (tmp_path / M.RECEIPT).exists()


def test_overlap_and_outline_pick_the_other_side(tmp_path):
    p = lef(tmp_path)
    blocker2 = pl(p, 100.0, 191.04, inst="u_blk2")                 # on grid; 191.04..201.04 overlaps a P at 200.88
    out, rows = M.snap_all([pl(p, 100.0, 201.96), blocker2], (400.0, 400.0), TRACKS)
    assert out[0]["y"] == 203.04 and out[1] == blocker2
    out, rows = M.snap_all([pl(p, 100.0, 201.96)], (400.0, 212.0), TRACKS)   # 203.04 + 10 leaves a 212 outline
    assert out[0]["y"] == 200.88


def test_unresolved_keeps_plan_origin(tmp_path):
    p = lef(tmp_path)
    out, rows = M.snap_all([pl(p, 100.0, 201.96), pl(p, 100.0, 191.04, inst="lo"), pl(p, 100.0, 205.92, inst="hi")],
                           (400.0, 400.0), TRACKS)
    assert out[0]["y"] == 201.96 and "unresolved" in rows[0]
    M.write_receipt(tmp_path, rows)
    assert json.loads((tmp_path / M.RECEIPT).read_text())["macros"][0]["inst"] == "u_q.u_s.u_pk"


def test_x_axis_on_site_grid(tmp_path):
    p = lef(tmp_path, pins_m4=(), pins_m5=(("c", 0.012, 0.0, 0.036, 0.192),))   # M5 pin centre x 0.024
    out, rows = M.snap_all([pl(p, 100.008, 200.88)], (400.0, 400.0), TRACKS)  # on the 0.054 site grid: site steps
    assert out[0]["x"] == 99.792 and out[0]["y"] == 200.88                      # 4 sites, ties -> lower
    out, rows = M.snap_all([pl(p, 100.061, 200.88)], (400.0, 400.0), TRACKS)  # off the site grid: 1-nm steps
    assert out[0]["x"] == 100.08
    assert M.off_track(M.lef_master(p, "PK"), 100.08, 200.88, "R0", TRACKS)["x"] == 0


def test_opt_out_and_missing_master(tmp_path):
    p = lef(tmp_path)
    src = [pl(p, 100.0, 201.96)]
    assert M.snap_all(src, (400.0, 400.0), TRACKS, env={"OT_MACRO_GRID_SNAP": "0"}) == (src, [])
    q = dict(src[0], master="NOPE")
    assert M.snap_all([q], (400.0, 400.0), TRACKS) == ([q], [])


def test_mirrored_orient_uses_placed_pins(tmp_path):
    p = lef(tmp_path)
    s = M.lef_master(p, "PK")
    # MX mirrors y about the height 10: pin a -> centre 9.976, so the origin needs y = 0.032 mod 0.048, which no 0.27-row
    # origin reaches: the row grid is dropped (receipt off_row) and the nearest 1-nm on-track origin is taken
    out, rows = M.snap_all([pl(p, 100.0, 201.96, o="MX")], (400.0, 400.0), TRACKS)
    assert M.off_track(s, out[0]["x"], out[0]["y"], "MX", TRACKS) == {"x": 0, "y": 0}
    assert out[0]["y"] == 201.968 and rows[0]["off_row"] is True


def test_gen_phys_writes_snapped_macro_place():
    src = (Path(__file__).resolve().parent / "gen_phys.py").read_text()
    assert "_MGS.snap_all(placed, (w, h), _MGS.tracks_for(make_tracks_tcl(P)))" in src
    assert "place_macro -macro_name {{{q['inst_db']}}}" in src


TR_TEXT = ("make_tracks M5 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048\n"
           "make_tracks M4 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048\n")


def core_kit(tmp):
    kd = Path(tmp) / "kit"
    (kd / "macros").mkdir(parents=True)
    p = lef(tmp, pins_m4=(), pins_m5=(("c", 0.012, 0.0, 0.036, 0.192),))
    (kd / "macros" / "PK.lef").write_text(p.read_text())
    (kd / "make_tracks.tcl").write_text(TR_TEXT)
    return kd


def test_core_sites_snap_mplace_and_hard_children_together(tmp_path):
    kd = core_kit(tmp_path)
    mplace = {"PK": [(100.061, 200.88, "R0"), (200.064, 200.88, "R0")]}       # first off (x), second on grid
    hcb = [dict(master="PK", inst="u_a", orient="R0", at=[100.061, 200.88]),  # the same site as mplace[0] (legacy)
           dict(master="PK", inst="u_b", orient="R0", at=[300.061, 100.0])]
    mp, hc, rows = M.snap_core_sites(kd, mplace, hcb, (400.0, 400.0))
    assert mp["PK"][0] == (100.08, 200.88, "R0") and mp["PK"][1] == (200.064, 200.88, "R0")
    assert hc[0]["at"] == [100.08, 200.88] and hc[1]["at"] == [300.048, 100.0]
    assert mplace["PK"][0] == (100.061, 200.88, "R0")                          # input not mutated
    assert len([r for r in rows if "snapped_um" in r]) == 2
    assert (kd / M.RECEIPT).is_file()


def test_core_sites_on_grid_same_objects(tmp_path):
    kd = core_kit(tmp_path)
    mplace, hcb = {"PK": [(200.064, 200.88, "R0")]}, [dict(master="PK", inst="u", orient="R0", at=[300.048, 100.0])]
    assert M.snap_core_sites(kd, mplace, hcb, (400.0, 400.0)) == (mplace, hcb, [])
    assert not (kd / M.RECEIPT).exists()


LEGACY_MP = """set b [ord::get_db_block]
foreach {master sites} {PK {{100.061 200.88 R0} {200.064 200.88 R0}}} {
  foreach i $hit s $sites { lassign $s x y orient }
}
set hit {}
foreach i [$blk getInsts] { if {[[$i getMaster] getName] eq "PK" && [regexp {u_b} [$i getName]]} { lappend hit $i } }
$i setOrient R0
$i setLocation 0 0
$i setLocation [expr {round(300.061 * $dbu) - [$bb xMin]}] [expr {round(100.0 * $dbu) - [$bb yMin]}]
"""


def test_existing_kit_macro_place_rewritten(tmp_path):
    kd = core_kit(tmp_path)
    (kd / "config.mk").write_text("export CORE_AREA = 0 0 400 400\nexport MAKE_TRACKS = /work/make_tracks.tcl\n")
    (kd / "macro_place.tcl").write_text(LEGACY_MP)
    rows = M.snap_kit(kd)                                                     # dry: nothing written
    assert len([r for r in rows if "snapped_um" in r]) == 2
    assert (kd / "macro_place.tcl").read_text() == LEGACY_MP
    assert M.main([str(kd), "--write"]) == 0
    txt = (kd / "macro_place.tcl").read_text()
    assert "{100.08 200.88 R0} {200.064 200.88 R0}" in txt and "round(300.048 * $dbu)" in txt
    assert M.snap_kit(kd) == []                                               # idempotent


def test_core_generators_call_the_snap():
    root = Path(__file__).resolve().parents[2] / "physical" / "die_plan"
    for f in ("s81/cores/legacy/gen_core_kit_legacy.py", "qwen_compute/cores/legacy/gen_core_kit_qc.py"):
        if (root / f).is_file():
            assert "MGS.snap_core_sites(kd, mplace, hcb, (w, h))" in (root / f).read_text()
