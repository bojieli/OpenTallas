import json
import subprocess
import sys

import pytest

import pre_submit_review as pre
import reviewed_locality as locality


def test_pick_rejects_host_outside_reviewed_pool(monkeypatch):
    monkeypatch.setattr(locality.subprocess, "run", lambda *_a, **_k:
                        subprocess.CompletedProcess([], 0, "intel2", ""))
    with pytest.raises(ValueError, match="permitted"):
        locality.strict_pick({"mem_gb": 8}, ["intel1", "epyc7"])


def test_first_eligible_ready_worker_does_not_wait_for_remaining_workers(monkeypatch):
    admitted = []
    checked = []
    sha = "b" * 40

    def pick(_, hosts):
        admitted.append(tuple(hosts))
        return hosts[0]

    def probe(host, revision):
        assert revision == sha
        checked.append(host)
        return host == "epyc7"

    monkeypatch.setattr(locality, "strict_pick", pick)
    monkeypatch.setattr(locality, "worker_runtime_ready", probe)
    readiness = {}
    assert locality.pick_ready_worker({"mem_gb": 8}, sha, readiness) == "epyc7"
    assert checked == ["intel1", "epyc7"]
    assert admitted[1] == admitted[0][1:]
    assert locality.pick_ready_worker({"mem_gb": 16}, sha, readiness) == "epyc7"
    assert checked == ["intel1", "epyc7"]


def test_runtime_uses_full_sealed_revision_and_ignores_remote_current(tmp_path, monkeypatch):
    sha = "a" * 40
    other = sha[:12] + "b" * 28
    version = tmp_path / sha[:12]
    setup = version / locality.WORKER_SETUP
    setup.parent.mkdir(parents=True)
    setup.write_text("# fixture")
    manifest = tmp_path / f"{sha[:12]}.manifest.json"
    manifest.write_text(json.dumps({"sha": sha, "files": {str(locality.WORKER_SETUP): "verified"}}))
    current = tmp_path / "current"
    current.symlink_to("c" * 12)
    monkeypatch.setattr(locality, "RUNTIME_ROOT", tmp_path)
    assert not locality.hub_runtime_ready(sha)
    current.unlink()
    current.symlink_to(version)
    assert locality.hub_runtime_ready(sha)
    assert not locality.hub_runtime_ready(other)
    current.unlink()
    current.symlink_to("d" * 12)
    probe = [sys.executable, "-I", "-B", "-c", locality.RUNTIME_PROBE, str(tmp_path)]
    assert subprocess.run([*probe, sha, str(locality.WORKER_SETUP)]).returncode == 0
    assert subprocess.run([*probe, other, str(locality.WORKER_SETUP)]).returncode != 0


def test_place_prepares_one_worker_and_checks_returned_exact_receipt(tmp_path, monkeypatch):
    sha = "a" * 40
    source = tmp_path / "sources" / sha[:12]
    run = tmp_path / "runs" / "qwen_compute_a"
    run.mkdir(parents=True)
    kit = run / "gen" / "coll_ftm"
    spec = {"die": "qwen_compute", "item": "coll_ftm", "flow": "type",
            "run": locality.review.TYPE_ROUTE, "mem_gb": 8}
    meta_path = run / "canary_meta.json"
    meta_path.write_text(json.dumps({"spec": spec, "src": str(source), "src_commit": sha[:12],
                                    "kit": str(kit), "review_before_route": True,
                                    "placement_host": "epyc10", "worker_runtime_sha": sha}))
    plan_approval = []
    seeded = []
    placed = []
    validated = []
    monkeypatch.setattr(locality, "source_head", lambda _: sha)
    monkeypatch.setattr(locality, "stage_worker_source", lambda *args: seeded.append(args))
    monkeypatch.setattr(pre, "ledger", lambda: "exact approved fixture")
    monkeypatch.setattr(pre, "hold", lambda *args, **kwargs: plan_approval.append((args, kwargs)) or "")
    def worker(*args, verify_copyback):
        placed.append(args)
        verify_copyback(0)
        return 0

    monkeypatch.setattr(locality, "run_on_worker", worker)
    monkeypatch.setattr(locality.review, "read_receipt", lambda _: {"checkpoint": "exact"})
    monkeypatch.setattr(locality.review, "validate_placement", lambda *args: validated.append(args))

    assert locality.run_stage(run, "place") == 0
    assert seeded == [("epyc10", run, sha)]
    assert plan_approval[0][0][1:3] == (source, sha)
    assert plan_approval[0][1] == {"staged": True}
    assert placed[0][:3] == (run, "epyc10", spec)
    assert "./job.sh" in placed[0][3][-1] and "./harness/place.sh" in placed[0][3][-1]
    assert "route" not in placed[0][3][-1]
    assert validated == [(kit, locality.review.receipt_path(run), {"checkpoint": "exact"})]
    assert json.loads(meta_path.read_text())["placement_host"] == "epyc10"

    with pytest.raises(ValueError, match="route approval is absent"):
        locality.run_stage(run, "route")
    assert len(placed) == 1
    meta = json.loads(meta_path.read_text())
    meta["worker_runtime_sha"] = "f" * 40
    meta_path.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match="pinned runtime"):
        locality.run_stage(run, "place")
    assert len(seeded) == 1


def test_worker_source_runs_immutable_helper_path(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(locality.subprocess, "run", lambda args, **_: calls.append(args)
                        or subprocess.CompletedProcess(args, 0))
    sha = "c" * 40
    locality.stage_worker_source("epyc7", tmp_path, sha)
    assert str(locality.RUNTIME_ROOT / sha[:12] / locality.WORKER_SETUP) in calls[0]
    assert "/rt/current/" not in " ".join(calls[0])


def test_corrupted_returned_receipt_keeps_worker_stage(tmp_path, monkeypatch):
    monkeypatch.setattr(locality.review, "read_receipt",
                        lambda _: (_ for _ in ()).throw(ValueError("changed checkpoint")))
    with pytest.raises(locality.PlacementReceiptError, match="changed checkpoint"):
        locality.check_placement_copyback(tmp_path, tmp_path / "kit", 0)
