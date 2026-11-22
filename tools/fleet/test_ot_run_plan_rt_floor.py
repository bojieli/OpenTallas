"""FLOW-FLEET-R2 T1: ot-run --plan-job bind refuses an rt below min_rt unless --rt-floor-exempt WHY."""
import importlib.machinery, importlib.util, json, pathlib
H = pathlib.Path(__file__).parent
l = importlib.machinery.SourceFileLoader("ot_run_rtf", str(H / "ot-run"))
RUN = importlib.util.module_from_spec(importlib.util.spec_from_loader("ot_run_rtf", l)); l.exec_module(RUN)


def _rt(tmp_path, floor="aaaaaaaaaaaa", old="bbbbbbbbbbbb", new="cccccccccccc"):
    root = tmp_path / "claude" / "rt"
    root.mkdir(parents=True)
    for sha, made in ((floor, "2026-11-20T10:00:00"), (old, "2026-11-10T10:00:00"), (new, "2026-11-21T10:00:00")):
        (root / f"{sha}.manifest.json").write_text(json.dumps({"made": made, "sha": sha}))
    (root / "MIN_RT").write_text(floor + "\n")
    return root


def _cmd(root, sha):
    return ["bash", f"{root}/{sha}/tools/die_plan/bind.sh"]


def test_bind_below_floor_is_refused(tmp_path):
    root = _rt(tmp_path)
    v, why = RUN.plan_job_rt_floor("bind", _cmd(root, "bbbbbbbbbbbb"), rt_root=str(root), cfg={})
    assert v == "BELOW" and "RT-FLOOR refused" in why and "--rt-floor-exempt" in why


def test_bind_at_or_above_floor_passes(tmp_path):
    root = _rt(tmp_path)
    assert RUN.plan_job_rt_floor("bind", _cmd(root, "cccccccccccc"), rt_root=str(root), cfg={})[0] == "OK"
    assert RUN.plan_job_rt_floor("bind", _cmd(root, "aaaaaaaaaaaa"), rt_root=str(root), cfg={})[0] == "OK"


def test_exempt_flag_is_logged_not_refused(tmp_path):
    root = _rt(tmp_path)
    v, why = RUN.plan_job_rt_floor("bind", _cmd(root, "bbbbbbbbbbbb"), exempt="sealed J7 tree", rt_root=str(root), cfg={})
    assert v == "EXEMPT" and "sealed J7 tree" in why


def test_other_kinds_and_unknown_rt_are_not_refused(tmp_path):
    root = _rt(tmp_path)
    assert RUN.plan_job_rt_floor("latcheck", _cmd(root, "bbbbbbbbbbbb"), cfg={})[0] == "SKIP"
    assert RUN.plan_job_rt_floor("bind", ["bash", "/srv/x/bind.sh"], real="/srv/x/ot-run", cfg={})[0] == "UNKNOWN"


def test_min_rt_in_kit_wave_json_wins(tmp_path):
    root = _rt(tmp_path)
    v, _ = RUN.plan_job_rt_floor("bind", _cmd(root, "bbbbbbbbbbbb"), rt_root=str(root), cfg={"min_rt": "cccccccccccc"})
    assert v == "BELOW"
