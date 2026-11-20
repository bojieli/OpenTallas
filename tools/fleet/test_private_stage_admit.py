"""STAGE-PRIVATE-1120 (FLEET-WATCH-1015): private / proof kits are charged by their stage peak in the status view (the gate's arithmetic), not by the class maximum minus their use."""
import contextlib, importlib.machinery, importlib.util, io, json, pathlib
from unittest import mock

P = str(pathlib.Path(__file__).with_name("ot-heavy-reconcile"))
loader = importlib.machinery.SourceFileLoader("ot_heavy_reconcile_ps", P)
R = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_heavy_reconcile_ps", loader))
loader.exec_module(R)


def test_private_kit_classes_are_lane_scripts_never_wave_kit_generators():
    for c in ("kit_w#.sh:#", "chain_n#merge#.sh", "eco_loop.py:residual", "bind_after_t#_t#_same_phase.sh", "chain_sspilot.sh"):
        assert R.private_kit_class(c), c
    for c in ("run_kit.sh:route", "run_kit_hbm.sh:gen", "docker:detail_route.tcl", "ot-job:run", "?", "", None, "openroad", "synth"):
        assert not R.private_kit_class(c), c


def test_measured_gap_skips_the_private_classes_only():
    hist = {"kit_w#.sh:#": [100.0] * 4, "run_kit.sh:route": [96.0] * 4}
    units = [("u1", 128.0, "kit_w#.sh:#", 6.0), ("u2", 128.0, "kit_w#.sh:#", 21.0), ("u3", 96.0, "run_kit.sh:route", 4.0)]
    assert R.measured_gap_gb(units, hist) == (100 - 6) + (100 - 21) + (96 - 4)
    assert R.measured_gap_gb(units, hist, skip=R.private_kit_class) == 96 - 4          # the wave kit keeps its class charge


def view(stage_peak_on, tmp=None):
    conf = dict(SIMPLE_ADMIT=1, PEAK_GAP_FACTOR=0.0, PLAN_GAP_FACTOR=1.0, MEASURED_GAP_CAP=0.5, MEASURED_GAP_FACTOR=1.0, STAGE_PEAK=1 if stage_peak_on else 0, STAGE_LOOKAHEAD=0,
                STAGE_PEAK_FRAC=0.3, INV_HEADROOM_GB=48.0)
    hist = {"kit_w#.sh:#": [100.0] * 4}
    units = [("u%d" % i, 128.0, "kit_w#.sh:#", 10.0) for i in range(3)]          # three private proofs: 3 x 90 GB class gap
    out = io.StringIO()
    with mock.patch.object(R, "conf", lambda k: conf[k]), mock.patch.object(R, "meminfo", lambda: (1000.0, 400.0)), mock.patch.object(R, "sizes", lambda: {}), \
            mock.patch.object(R, "waiters", lambda t: ([], [])), mock.patch.object(R, "peak_gap_gb", lambda: 0.0), mock.patch.object(R, "plan_gap_gb", lambda: 0.0), \
            mock.patch.object(R, "committed_threads", lambda: 0), mock.patch.object(R, "stage_growth", lambda *a, **k: (12.0, 3)), mock.patch.object(R, "load_stage_table", lambda: {}), \
            mock.patch.object(R, "running_units_light", lambda: units), mock.patch.object(R, "peak_history", lambda: hist), contextlib.redirect_stdout(out):
        R.free("/")
    return json.loads(out.getvalue())["admit_gb"]


def test_the_status_view_admits_on_stage_peak_for_private_kits():
    assert view(False) == 400 - 48 - 200          # old arithmetic: 3 x 90 = 270 class gap capped at half of MemAvailable (200)
    assert view(True) == 400 - 48 - 12            # STAGE_PEAK on: only the stage growth of their build processes is charged
