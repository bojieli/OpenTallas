import json
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canary as C
import placement_review as R
import trigger as T


def viewed(doc, delay=0, verdict="OK", reviewer="Human placement viewed", path=None, attempt=1):
    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(time.time() - delay))
    return (f"- {stamp} PST GEOM VERDICT [{reviewer}] {doc['die']}/{doc['item']} attempt_{attempt} "
            f"(note: with (nested) review): {verdict} kit={path or doc['kit_location']} .")


@pytest.fixture
def placement(tmp_path):
    run = tmp_path / "runs/reference"
    kit = run / "gen/t1"
    odb = kit / "run/results/asap7/leaf/base/3_place.odb"
    odb.parent.mkdir(parents=True)
    odb.write_bytes(b"placed bytes")
    runner = kit.parent / "run_kit.sh"
    runner.write_text("# OT_STAGE_RESUME_V1\n")
    (kit / "kit_resume.py").write_text(
        "def auto_write(kit, goal):\n    return {'start': 'cts', 'reused_steps': ['place']}\n"
    )
    receipt = R.receipt_path(run)
    receipt.parent.mkdir()
    for name in R.IMAGES:
        (receipt.parent / name).write_bytes(name.encode())
    doc = dict(die="s81", item="t1", attempt=1, src_commit="123456789012", kit=str(kit),
               kit_location=f"intel2:{kit}", odb=str(odb), odb_sha256=R.digest(odb),
               runner_sha256=R.digest(runner), ready_at=time.time() - 5,
               images={name: R.digest(receipt.parent / name) for name in R.IMAGES})
    R.write_json(receipt, doc)
    approval = run / "approval.json"
    R.write_json(approval, {"placement_sha256": R.digest(receipt), "verdict": "OK"})
    args = SimpleNamespace(kit=str(kit), runner=str(runner), receipt=str(receipt), approval=str(approval))
    return run, args, doc


def test_explicit_view_is_current_and_scope_exact(placement):
    _, _, doc = placement
    records = [
        viewed(doc, delay=120), viewed(doc, reviewer="AUTO-VISUAL-REVIEW viewed"),
        viewed(doc, reviewer="Human submitted"), viewed(doc, path="epyc7:/another/kit"),
        viewed(doc, attempt=2),
    ]
    assert R.latest_viewed(doc, "\n".join(records)) is None
    assert R.latest_viewed(doc, "\n".join(records + [viewed(doc)])) == "OK"
    assert R.latest_viewed(doc, "\n".join(records + [viewed(doc), viewed(doc, verdict="BAD")])) == "BAD"


def test_prepare_fails_closed_when_resume_would_build_another_placement(placement):
    _, a, _ = placement
    R.prepare_route(a)
    module = Path(a.kit) / "kit_resume.py"
    module.write_text("def auto_write(kit, goal):\n    return {'start': 'place', 'reused_steps': ['floorplan']}\n")
    with pytest.raises(ValueError, match="cannot resume directly"):
        R.prepare_route(a)


@pytest.mark.parametrize("mutation", ["odb", "image", "runner"])
def test_guard_rejects_changed_placement_evidence(placement, mutation):
    _, a, doc = placement
    path = {"odb": doc["odb"], "image": Path(a.receipt).parent / "floorplan.png", "runner": a.runner}[mutation]
    Path(path).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        R.prepare_route(a)


def test_has_no_release_without_matching_receipt(placement):
    _, a, _ = placement
    R.write_json(Path(a.approval), {"placement_sha256": "wrong", "verdict": "OK"})
    with pytest.raises(ValueError, match="exact placement receipt"):
        R.prepare_route(a)


def test_unattended_submit_defers_route_and_holds_core(tmp_path, monkeypatch):
    guard = tmp_path / "tools/die_plan/face_guard.py"
    guard.parent.mkdir(parents=True)
    guard.write_text("# fixture\n")
    specs = {
        "s81": dict(die="s81", item="t1", flow="type", top="top", kit="{gen}/{item}",
                    mem_gb=20, gen="true", run=R.TYPE_ROUTE),
        "core": dict(die="core", item="core", flow="kv_core", mem_gb=99, run="finish"),
    }
    monkeypatch.setenv("OT_CANARY_ANY_SOURCE", "1")
    monkeypatch.setattr(C, "load_spec", lambda _: (specs, {}))
    monkeypatch.setattr(C, "git_head", lambda _: "123456789012")
    calls = []
    monkeypatch.setattr(C, "launch_client", lambda *args: calls.append(args) or SimpleNamespace(returncode=0))
    a = SimpleNamespace(spec=None, die=list(specs), src=str(tmp_path), root=str(tmp_path / "runs"),
                        image="orfs", dry=False, review_before_route=True)
    assert C.cmd_submit(a) == 0
    (run,) = list((tmp_path / "runs").iterdir())
    assert len(calls) == 1 and "harness/place.sh" in calls[0][1] and "route_canary.sh" not in calls[0][1]
    place = (run / "harness/place.sh").read_text()
    route = (run / "harness/route_canary.sh").read_text()
    assert " place 20 8" in place and " render " in place
    assert route.index("prepare-route") < route.index(" route 20 8")
    assert "export OT_RESUME=0" in route
    for script in (place, route):
        subprocess.run(["bash", "-n"], input=script, text=True, check=True)


def test_rejected_exact_attempt_stays_visible_without_blocking_new_source(placement, monkeypatch):
    run, _, doc = placement
    R.write_json(run / "canary_meta.json", {"spec": {"die": doc["die"]},
                    "review_before_route": True, "client_unit": "ref-place", "src_commit": doc["src_commit"]})
    monkeypatch.setattr(T, "unit_active", lambda _: False)
    monkeypatch.setattr(T._canary_module, "placement_review", lambda: R)
    monkeypatch.setattr(R, "canonical_review_log", lambda: viewed(doc, verdict="BAD"))
    assert T.live_dies(run.parent, target_sha=doc["src_commit"]) == {"s81"}
    assert T.live_dies(run.parent, target_sha="987654321098") == set()
    assert run.is_dir() and R.receipt_path(run).is_file()
    monkeypatch.setattr(R, "canonical_review_log", lambda: "")
    assert T.live_dies(run.parent, target_sha="987654321098") == {"s81"}


def test_resume_uses_current_human_approval_once_and_rejects_superseded(placement, monkeypatch):
    run, a, doc = placement
    (run / "harness").mkdir()
    meta = dict(spec={"die": doc["die"], "item": doc["item"], "flow": "type", "run": R.TYPE_ROUTE, "mem_gb": 20},
                kit=a.kit, src_commit=doc["src_commit"], review_before_route=True, submitted_at=time.time(),
                client_unit="canary-place-unit", ot_run_args=["--no-spill"])
    R.write_json(run / "canary_meta.json", meta)
    monkeypatch.setattr(C, "placement_review", lambda: R)
    monkeypatch.setattr(C.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=3))
    launches = []
    monkeypatch.setattr(C, "launch_client", lambda *args: launches.append(args) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(R, "canonical_review_log", lambda: viewed(doc, verdict="ISSUES"))
    assert C.cmd_resume(SimpleNamespace(run=run)) == 3
    assert not launches

    monkeypatch.setattr(R, "canonical_review_log", lambda: viewed(doc, verdict="ISSUES-ACCEPT"))
    sibling = run.parent / "new-reference"
    sibling.mkdir()
    R.write_json(sibling / "canary_meta.json", dict(meta, submitted_at=meta["submitted_at"] + 1))
    assert C.cmd_resume(SimpleNamespace(run=run)) == 3
    assert not launches
    (sibling / "canary_meta.json").unlink()

    assert C.cmd_resume(SimpleNamespace(run=run)) == 0
    assert C.cmd_resume(SimpleNamespace(run=run)) == 3
    assert len(launches) == 1 and launches[0][0] == "canary-place-unit-route"
    assert "--no-spill" in launches[0][1] and "harness/route_canary.sh" in launches[0][1]
    approval = json.loads((run / "harness/route_approval.json").read_text())
    assert approval["placement_sha256"] == R.digest(a.receipt)
