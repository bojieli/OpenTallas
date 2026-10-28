"""FLOW-GEN-2 (f) (COORD 10-28): kit_contract.macro_pin_grid FAILs a hard macro whose origin puts its signal pins off
the preferred-direction track grid of their layer (KV pv_pair: a pair 18 nm off M4, 794 off-grid pin warnings,
DRT-0255)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_contract as KC  # noqa: E402

LEF = """VERSION 5.8 ;
MACRO ot_fix_ram
  CLASS BLOCK ;
  SIZE 4.8 BY 4.8 ;
  PIN d
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0 0.0 0.192 0.024 ;
    END
  END d
  PIN q
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0 0.048 0.192 0.072 ;
    END
  END q
  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
    PORT
      LAYER M4 ;
        RECT 0 0.1 4.8 0.13 ;
    END
  END VDD
END ot_fix_ram
END LIBRARY
"""


def _kit(tmp, sites, tracks=None):
    kd = Path(tmp)
    (kd / "macros").mkdir(parents=True, exist_ok=True)
    (kd / "macros" / "ot_fix_ram.lef").write_text(LEF)
    rows = "\n".join(f"  {{u{i}}} ot_fix_ram {x} {y} {o}" for i, (x, y, o) in enumerate(sites))
    (kd / "macro_placement.tcl").write_text("foreach {inst master x y orient} {\n" + rows + "\n} {\n"
                                            "  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact\n}\n")
    cfg = ["export MACRO_PLACEMENT_TCL = /work/macro_placement.tcl"]
    if tracks:
        (kd / "make_tracks.tcl").write_text(tracks)
        cfg.append("override export MAKE_TRACKS = /work/make_tracks.tcl")
    (kd / "config.mk").write_text("\n".join(cfg) + "\n")
    return kd


def test_on_grid_macro_passes(tmp_path):
    err, info = KC.macro_pin_grid(_kit(tmp_path, [(8.64, 17.28, "R0")]))
    assert err == [] and info["pins"] == 2 and info["tracks"] == "platform"


def test_18nm_off_m4_fails(tmp_path):
    err, info = KC.macro_pin_grid(_kit(tmp_path, [(8.64, 17.28, "R0"), (15.552, 17.298, "R0")]))
    assert len(err) == 1 and "#1" in err[0] and "2 signal pin(s) off" in err[0] and "18.0 nm" in err[0]
    assert info["worst_off_nm"] == 18.0


def test_mirror_needs_its_own_origin(tmp_path):
    # SIZE 4.8 = 100 M4 pitches: MX puts the pin centres at h - 0.012 -> 24 nm off the 0.012 + k 0.048 grid ...
    err, _ = KC.macro_pin_grid(_kit(tmp_path, [(8.64, 17.28, "MX")]))
    assert len(err) == 1 and "24.0 nm" in err[0]
    # ... and an origin shifted by half a pitch puts them back on it
    err, _ = KC.macro_pin_grid(_kit(tmp_path, [(8.64, 17.304, "MX")]))
    assert err == []


def test_kit_make_tracks_override_is_the_grid(tmp_path):
    tr = "make_tracks M4 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048\n"
    err, info = KC.macro_pin_grid(_kit(tmp_path, [(8.64, 17.28, "R0")], tracks=tr))
    assert info["tracks"] == "make_tracks.tcl" and len(err) == 1 and "12.0 nm" in err[0]


def test_in_contract_and_fails_closed(tmp_path):
    assert "macro_pin_grid" in KC.CHECKS
    rep = KC.run_all(_kit(tmp_path, [(15.552, 17.298, "R0")]))
    assert rep["macro_pin_grid"]["verdict"] == "FAIL"


def test_no_macros_is_na(tmp_path):
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = x\n")
    assert KC.macro_pin_grid(tmp_path) == ([], dict(applies=False))
