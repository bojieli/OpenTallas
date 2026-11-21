"""FLEET-WATCH-2000: <claude>/ot-job-failed-logs (FAILLOGS-1630, ot-job prunes it itself after 14 d) must not look like an idle lane dir to autoclean class d."""
import importlib.machinery, importlib.util, pathlib

p = pathlib.Path(__file__).resolve().parent / "ot-autoclean.py"
spec = importlib.util.spec_from_loader("ot_autoclean_fl", importlib.machinery.SourceFileLoader("ot_autoclean_fl", str(p)))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_failed_logs_dir_is_never_a_class_d_lane():
    assert "ot-job-failed-logs" in m.D_SKIP_LANES and "ot-jobs" in m.D_SKIP_LANES
