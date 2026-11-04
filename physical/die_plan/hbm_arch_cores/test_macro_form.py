#!/usr/bin/env python3
"""DIE-HBM-66: macro_form.py snaps to the KIT tracks.  The pin below is on the platform M4 grid (offset 12) and off the kit
grid (offset 24): the path-for-text bug left it in place with moves [], the fix moves it 12 nm in y.
  python3 -m pytest physical/die_plan/hbm_arch_cores/test_macro_form.py"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEF = """MACRO toy
  SIZE 1.0 BY 0.5 ;
  PIN a
    USE SIGNAL ;
    PORT
      LAYER M4 ;
        RECT 0.0 0.0 0.2 0.024 ;
    END
  END a
END toy
"""


def kit(tmp, y):
    k = tmp / "k"
    (k / "macros").mkdir(parents=True)
    (k / "macros" / "toy.lef").write_text(LEF)
    (k / "make_tracks.tcl").write_text("make_tracks M4 -x_offset 0.024 -x_pitch 0.048 -y_offset 0.024 -y_pitch 0.048\n")
    (k / "config.mk").write_text("export DIE_AREA = 0 0 20 20\n")
    (k / "macro_placement.tcl").write_text("foreach {inst master x y orient} {\n  {u_m} toy 1 %s R0\n} {\n}\n" % y)
    return k


def test_resnap_uses_kit_tracks(tmp_path):
    k = kit(tmp_path, "0.96")          # pin centre 0.972: platform track, 12 nm off the kit grid
    subprocess.run([sys.executable, str(HERE / "macro_form.py"), str(k), "--resnap"], check=True)
    mv = json.loads((k / "macro_grid_snap.json").read_text())["moves"]
    assert [(m["dx_nm"], m["dy_nm"]) for m in mv] == [(0, 12)]
    assert "{u_m} toy" in (k / "macro_placement.tcl").read_text()
    subprocess.run([sys.executable, str(HERE / "macro_form.py"), str(k), "--resnap"], check=True)
    assert json.loads((k / "macro_grid_snap.json").read_text())["moves"] == []


def test_placement_form_uses_kit_tracks(tmp_path):
    k = kit(tmp_path, "0.96")
    p = tmp_path / "pl.json"
    p.write_text(json.dumps([["u_m", 1, 0.96, "R0"]]))
    subprocess.run([sys.executable, str(HERE / "macro_form.py"), str(k), str(p)], check=True)
    assert len(json.loads((k / "macro_grid_snap.json").read_text())["moves"]) == 1
    assert (k / "FORM_MACRO64.json").exists()
