import json

import pytest

import pre_submit_review as pre
import reviewed_locality as locality


def test_pick_rejects_host_outside_reviewed_pool(monkeypatch):
    monkeypatch.setattr(locality, "command_output", lambda _: "intel2")
    with pytest.raises(ValueError, match="permitted"):
        locality.strict_pick({"mem_gb": 8})


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
                                    "kit": str(kit), "review_before_route": True}))
    plan_approval = []
    seeded = []
    placed = []
    validated = []
    monkeypatch.setattr(locality, "source_head", lambda _: sha)
    monkeypatch.setattr(locality, "strict_pick", lambda _: "epyc10")
    monkeypatch.setattr(locality, "stage_worker_source", lambda *args: seeded.append(args))
    monkeypatch.setattr(pre, "ledger", lambda: "exact approved fixture")
    monkeypatch.setattr(pre, "hold", lambda *args, **kwargs: plan_approval.append((args, kwargs)) or "")
    monkeypatch.setattr(locality, "run_on_worker", lambda *args: placed.append(args) or 0)
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
