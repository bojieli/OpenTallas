"""FLOW-MCMM-GRT 2026-10-27: the GRT repair step runs two scenes (tc TT setup + BC FF hold) on two-corner kits.

S81-ECO-2 (CHECKED, ot_s81sl_vq e1): the FF-only GRT step (`make grt CORNER=BC CORNERS=bc`) loads FF libraries only,
'No setup violations found' at FF, TT -64.57 / 88 EP at sign-off.  grt_scenes.sh, kit_modes --scenes, the FF scene
SDC binding and the kit_preflight rule are checked here without OpenROAD (the A/B canary measures the QoR)."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_flow  # noqa: E402
import kit_modes  # noqa: E402
import kit_preflight  # noqa: E402
from test_kit_modes import kit as mk_kit  # noqa: E402

SCENES = HERE / "grt_scenes.sh"


def staged(tmp_path, corners="tc bc", files=True, modes=True):
    kd = mk_kit(tmp_path, corners=corners)
    if files:
        core_flow.install_grt_scenes(kd)
        # the kit copy of the ORFS patcher runs against the real ORFS scripts in the container; stub it here
        (kd / "orfs_hold_mm.py").write_text("import sys\nprint('stub patch', sys.argv[1:])\n")
    if modes:
        kit_modes.copy_kit_tools(kd)
    return kd


def run_scenes(kd, hm="5"):
    """grt_scenes.sh with M = an echo of the make command line (one line per make call)."""
    env = dict(os.environ, OT_KIT_DIR=str(kd), OT_ORFS_SCRIPTS=str(kd), M="echo MAKE")
    for k in ("OT_HOLD_MM", "OT_VCLK_CORNER"):
        env.pop(k, None)
    r = subprocess.run(["bash", str(SCENES), hm], env=env, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def test_two_corner_kit_runs_two_scene_grt(tmp_path):
    kd = staged(tmp_path)
    rc, out = run_scenes(kd)
    assert rc == 0, out
    make = [l for l in out.splitlines() if l.startswith("MAKE")]
    assert make == ["MAKE grt CORNERS=tc BC HOLD_SLACK_MARGIN=5"], out
    assert "KIT_MODES ok" in out and "GRT_SCENES two-scene GRT repair" in out
    assert "stub patch" in (kd / "orfs_hold_mm.log").read_text()
    # the env of the make call: two scenes, no FF vclk binding in mode ss
    s = SCENES.read_text()
    line = next(l for l in s.splitlines() if "OT_HOLD_MM=1" in l and "$M grt" in l)
    assert "OT_MM_SETUP_CORNER=tc" in line and 'OT_MM_FF_SDC="$K/grt_ff_scene.sdc"' in line
    assert "OT_VCLK_CORNER" not in line and "CORNERS=bc" not in line


def test_kit_margin_when_no_margin_given(tmp_path):
    rc, out = run_scenes(staged(tmp_path), hm="")
    assert rc == 0 and "MAKE grt CORNERS=tc BC\n" in out + "\n", out


def test_one_corner_kit_keeps_ff_only_step(tmp_path):
    rc, out = run_scenes(staged(tmp_path, corners="bc"))
    assert rc == 0, out
    assert [l for l in out.splitlines() if l.startswith("MAKE")] == ["MAKE grt CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=5"]


def test_missing_scene_helper_fails_closed(tmp_path):
    kd = staged(tmp_path)
    (kd / "grt_ff_scene.sdc").unlink()
    rc, out = run_scenes(kd)
    assert rc == 9 and "GRT_SCENES FAIL kit lacks grt_ff_scene.sdc" in out and "MAKE" not in out


def test_binding_mismatch_stops_before_make(tmp_path):
    kd = staged(tmp_path)
    (kd / "sdc_lint.json").write_text(json.dumps(dict(time_unit_ps=1.0, insertion_ps=250.0, insertion_ff_ps=210.0)))
    rc, out = run_scenes(kd)
    assert rc == 9 and "KIT_MODES FAIL FF binding" in out and "MAKE" not in out


def test_kit_modes_scenes_session(tmp_path):
    kd = staged(tmp_path, modes=False)
    r = kit_modes.check(kd, "grt", session="tc bc", hold_repair=True, scenes=True)
    assert r["mm"] is True and r["session"] == ["tc", "bc"]
    with pytest.raises(kit_modes.Fail, match="FF latency would land in mode ss"):
        kit_modes.check(kd, "grt", session="tc bc", vclk_corner="ff", hold_repair=True, scenes=True)
    with pytest.raises(kit_modes.Fail, match="GRT-step session only"):
        kit_modes.check(kd, "eco", session="tc bc", hold_repair=True, scenes=True)
    # without --scenes the same session is the single-mode bug
    with pytest.raises(kit_modes.Fail, match="single-mode tc\\+bc hold repair"):
        kit_modes.check(kd, "grt", session="tc bc", hold_repair=True)
    (kd / "orfs_hold_mm.tcl").unlink()
    with pytest.raises(kit_modes.Fail, match="kit lacks"):
        kit_modes.check(kd, "grt", session="tc bc", hold_repair=True, scenes=True)


def test_ff_scene_sdc_binds_bound_or_measured_ff_vclk():
    sdc = (HERE / "grt_ff_scene.sdc").read_text()
    assert "ot_vmh_scene_bind" in sdc and "vclk_corner.tcl" in sdc and "vclk_measured_hold.tcl" in sdc
    t = (HERE / "vclk_measured_hold.tcl").read_text()
    body = t[t.index("proc ot_vmh_scene_bind"):t.index("proc ot_vclk_measured_hold")]
    assert body.index("ot_vclk_bind ff") < body.index("ot_vmh_reference") < body.index("ot_vmh_measured")
    assert "repair_timing" not in body          # the stage repair does TT setup + FF hold together
    # one measurement / band check for both the scene binding and the FF-only step
    assert t.count("proc ot_vmh_measured ") == 1 and t.count("[ot_vmh_measured $ffb $tol]") == 2


def test_runners_use_the_scene_step():
    import gen_phys
    assert "export M; bash /work/grt_scenes.sh \\$HM" in gen_phys.RUN_KIT
    assert core_flow.GRT_SCENES_CALL in core_flow.FF_GRT_STEP
    hbm = (HERE.parents[1] / "physical/die_plan/hbm_arch_cores/run_kit_hbm.sh").read_text()
    for text in (gen_phys.RUN_KIT, core_flow.FF_GRT_STEP, hbm):
        assert not kit_preflight.FF_ONLY_GRT.search(text)


def test_apply_installs_scene_helpers(tmp_path):
    kd = tmp_path / "k"
    kd.mkdir()
    core_flow.apply(kd, core_flow.binding(250, 202.5), "dut", rc_cal=False)
    for f in core_flow.GRT_SCENE_FILES + core_flow.GRT_SCENE_TOOLS:
        assert (kd / f).is_file(), f
    assert os.access(kd / "grt_scenes.sh", os.X_OK)


def runner(kd, line):
    (kd / "run_kit.sh").write_text("#!/bin/bash\nM=make\nrc=0\n" + line + "\n")


def test_preflight_rejects_ff_only_grt_on_two_corner_kit(tmp_path):
    kd = staged(tmp_path)
    runner(kd, "if [ $rc = 0 ]; then OT_VCLK_CORNER=ff $M grt CORNER=BC CORNERS=bc; rc=$?; fi")
    errs = kit_preflight.grt_scenes_errors(kd)
    assert len(errs) == 1 and "run_kit.sh:4: FF-only GRT repair step on a tc+bc kit" in errs[0]
    runner(kd, "if [ $rc = 0 ]; then export M; bash /work/grt_scenes.sh $HM; rc=$?; fi")
    assert kit_preflight.grt_scenes_errors(kd) == []
    (kd / "grt_ff_scene.sdc").unlink()
    assert kit_preflight.grt_scenes_errors(kd) == ["run_kit.sh runs grt_scenes.sh but the kit lacks grt_ff_scene.sdc"]


def test_preflight_ignores_one_corner_and_unbound_kits(tmp_path):
    (tmp_path / "a").mkdir()
    kd = staged(tmp_path / "a", corners="bc")
    runner(kd, "OT_VCLK_CORNER=ff $M grt CORNER=BC CORNERS=bc")
    assert kit_preflight.grt_scenes_errors(kd) == []
    kd2 = tmp_path / "b"
    kd2.mkdir()
    (kd2 / "config.mk").write_text("export CORNERS = tc bc\n")
    runner(kd2, "$M grt CORNER=BC CORNERS=bc")
    assert kit_preflight.grt_scenes_errors(kd2) == []


def test_declared_signoff_frame_overrides_derived_ref(tmp_path):
    import vclk_ref
    kd = mk_kit(tmp_path)
    assert vclk_ref.ff_reference(kd)["ref"] == "rebind"            # per-corner binding, no hard-core contract
    with (kd / "config.mk").open("a") as f:
        f.write("export OT_FF_VCLK_REF = bound-ff\n")
    r = vclk_ref.ff_reference(kd)
    assert (r["ref"], r["ff_bound"]) == ("bound-ff", 202.5)
    with (kd / "config.mk").open("a") as f:
        f.write("export OT_FF_VCLK_REF = measured\n")
    with pytest.raises(vclk_ref.RefError, match="OT_FF_VCLK_REF"):
        vclk_ref.ff_reference(kd)
