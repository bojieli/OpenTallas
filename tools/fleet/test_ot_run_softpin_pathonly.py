"""SOFTPIN-PATHONLY-1119: a path-only sealed spec with a job-root --dir may be re-placed (INPUT HOLD keeps it on hosts that hold its inputs); kit-local dirs and empty specs stay pinned."""
import importlib.machinery, importlib.util, json, pathlib
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_sp", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_sp", l)); l.exec_module(RUN)
ROOT = "/srv/opentallas-scratch2/claude/ot-jobs"


def spec(tmp, inputs):
    p = tmp / "s.json"; p.write_text(json.dumps({"schema": "opentallas.ot_job.v1", "name": "x", "inputs": inputs})); return str(p)


def test_path_only_job_root_spec_is_soft_pinned(tmp_path):
    assert RUN.soft_pin_ok(spec(tmp_path, [{"path": "/srv/a/b"}, {"path": "/srv/a/c", "at": "/srv/a/c"}]), ROOT)
    assert RUN.soft_pin_ok(spec(tmp_path, [{"host": "epyc7", "path": "/srv/a/b"}]), ROOT)           # fetch spec: as before


def test_kit_local_dir_empty_or_malformed_specs_stay_hard_pinned(tmp_path):
    assert not RUN.soft_pin_ok(spec(tmp_path, [{"path": "/srv/a/b"}]), "/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/x/kit")
    assert not RUN.soft_pin_ok(spec(tmp_path, []), ROOT)
    assert not RUN.soft_pin_ok(spec(tmp_path, [{"at": "/x"}]), ROOT)
    assert not RUN.soft_pin_ok(str(tmp_path / "missing.json"), ROOT)
