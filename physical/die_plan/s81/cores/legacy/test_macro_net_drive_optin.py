"""S81-GUNIT-FORM-2 11-08 (COORD 11-07 23:3x (2)): recipe macro_net_drive is opt-in. A kit with the key gets
pre_resize.tcl (drv.tcl + macro_net_drive.tcl) and the OT_MND_* env; a kit without it keeps PRE_RESIZE_TCL = drv.tcl
and no macro_net_drive file.
    python3 -m pytest -q physical/die_plan/s81/cores/legacy/test_macro_net_drive_optin.py"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
GEN = HERE / "gen_core_kit_legacy.py"
sys.path.insert(0, str(HERE))
import gen_core_kit_legacy as G  # noqa: E402


def _gen(out, mod, *extra):
    r = subprocess.run([sys.executable, str(GEN), "--module", mod, "--out", str(out), *extra],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return Path(json.loads(r.stdout.strip().splitlines()[-1])["kit"])


@pytest.mark.skipif(not (G.S81 / "die_plan.json").is_file(), reason="sparse checkout without the S81 plan")
def test_macro_net_drive_opt_in(tmp_path):
    rec = json.loads((HERE / "recipes.json").read_text())
    assert rec["dsdv_gunit_l1f_ba0"]["macro_net_drive"] == {"max_wire_um": 100}
    kd = _gen(tmp_path / "on", "dsdv_gunit_l1f_ba0")
    cfg = (kd / "config.mk").read_text().splitlines()
    assert "export PRE_RESIZE_TCL = /work/pre_resize.tcl" in cfg
    assert "export OT_MND_MAX_WIRE_UM = 100" in cfg and "export OT_MND_FF = DFFHQNx3_ASAP7_75t_R" in cfg
    assert (kd / "pre_resize.tcl").read_text() == "source /work/drv.tcl\nsource /work/macro_net_drive.tcl\n"
    assert (kd / "macro_net_drive.tcl").read_bytes() == (G.S81 / "cores/split_clock/macro_net_drive.tcl").read_bytes()
    assert "MY" in (kd / "macro_place.tcl").read_text()
    off = _gen(tmp_path / "off", "dsdv_gunit_l1f_bf")
    cfg = (off / "config.mk").read_text()
    assert "export PRE_RESIZE_TCL = /work/drv.tcl" in cfg and "OT_MND_" not in cfg
    assert not (off / "pre_resize.tcl").exists() and not (off / "macro_net_drive.tcl").exists()
