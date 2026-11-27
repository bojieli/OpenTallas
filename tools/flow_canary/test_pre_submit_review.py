"""The timer requires an exact source-plan image before a new type canary."""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest

import canary as C
import pre_submit_review as R


TYPE = {
    "die": "s81_head", "item": "hd_turn_a", "top": "s81p_hd_turn_a", "flow": "type",
    "kit": "{gen}/{item}", "run": R.TYPE_ROUTE, "mem_gb": 16,
    "gen": "python3 -I tools/die_plan/gen.py phys physical/die_plan/s81_head/die_plan.json "
           "--out {gen} --types {item} --rtl-root {src} --hold-ff-margin 0",
}


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def mark(request, verdict):
    return "\t".join(("2026-11-26", request["die"], request["item"], request["form_sha256"],
                      verdict, "/scratch/image.png", "a"*64, "VIS", "Exact layout")) + "\n"


@pytest.fixture
def source(tmp_path):
    src = tmp_path / "flow-canary/sources/reference"
    src.mkdir(parents=True)
    git(src, "init", "-q")
    git(src, "config", "user.name", "Fixture")
    git(src, "config", "user.email", "fixture@invalid")
    path = src / "physical/die_plan/s81_head/die_plan.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"partition_types":{"hd_turn_a":{"outline":[10,20]}}}')
    git(src, "add", str(path))
    git(src, "commit", "-qm", "original")
    return src, path, tmp_path / "flow-canary/runs"


def request_file(root):
    return root.parent / "plan_visual_requests/s81_head/plan_visual_request.json"


def test_exact_plan_and_recipe_reuse_without_full_source_checkout(source):
    src, path, root = source
    rev = git(src, "rev-parse", "HEAD")
    assert "missing" in R.hold(TYPE, src, rev, root, "img", "")
    base = json.loads(request_file(root).read_text())
    assert Path(base["plan"]).read_bytes() == path.read_bytes()
    assert base["source_revision"] == rev
    review = mark(base, "GOOD")
    assert R.hold(TYPE, src, rev, root, "img", review) == ""
    assert R.hold(TYPE, src, rev, root, "img", review, staged=True) == ""

    git(src, "commit", "--allow-empty", "-qm", "different revision, same plan and recipe")
    other_rev = git(src, "rev-parse", "HEAD")
    assert R.hold(TYPE, src, other_rev, root, "img", review) == ""
    changed_recipe = dict(TYPE, gen=TYPE["gen"] + " --max-wire-um 100")
    assert "missing" in R.hold(changed_recipe, src, other_rev, root, "img", review)
    assert "missing" in R.hold(TYPE, src, other_rev, root, "different_image", review)

    path.write_text('{"partition_types":{"hd_turn_a":{"outline":[11,20]}}}')
    git(src, "commit", "-qam", "changed shape")
    revision = git(src, "rev-parse", "HEAD")
    assert "missing" in R.hold(TYPE, src, revision, root, "img", review)
    revised = json.loads(request_file(root).read_text())
    assert "missing" in R.hold(TYPE, src, revision, root, "img", review, staged=True)
    approval = review + mark(revised, "GOOD")
    assert R.hold(TYPE, src, revision, root, "img", approval, staged=True) == ""
    assert "BAD" in R.hold(TYPE, src, revision, root, "img", approval + mark(revised, "BAD"), staged=True)
    assert not root.exists()


@pytest.mark.parametrize("changes", [
    {"flow": "kv_core"}, {"die": "s81_head_cl"}, {"vars": {"inputs": "/inputs"}},
    {"gen": TYPE["gen"] + " --clock-landing /input"}, {"prep": ["mkdir -p /tmp/prepare"]},
])
def test_unsupported_sources_do_not_issue_a_launch_request(source, changes):
    src, _, root = source
    assert "unsupported" in R.hold(dict(TYPE, **changes), src, "HEAD", root, "img", "")
    assert not root.parent.joinpath("plan_visual_requests").exists()


def test_staged_submit_denies_missing_review_before_job_creation(source, monkeypatch):
    src, _, root = source
    status = src.parent.parent / "status.json"
    monkeypatch.setattr(C, "pre_submit_review", lambda: R)
    monkeypatch.setattr(R, "ledger", lambda: "")
    monkeypatch.setattr(C, "load_spec", lambda _: ({"s81_head": TYPE}, {}))
    monkeypatch.setattr(C, "launch_client", lambda *_: pytest.fail("unreviewed canary reached systemd"))
    args = SimpleNamespace(spec=None, die=["s81_head"], src=str(src), root=str(root),
                           image="img", dry=False, require_plan_review=True, plan_review_status=status)
    assert C.cmd_submit(args) == 0
    assert json.loads(status.read_text()) == {"deferred": ["s81_head"]}
    assert not root.exists()


def test_approved_submit_defers_when_no_exact_worker_admits(source, monkeypatch):
    src, _, root = source
    status = root.parent / "status.json"
    monkeypatch.setattr(C, "pre_submit_review", lambda:
                        SimpleNamespace(ledger=lambda: "reviewed", hold=lambda *a, **k: ""))
    monkeypatch.setattr(C, "reviewed_locality", lambda:
                        SimpleNamespace(source_head=lambda _: "a" * 40, hub_runtime_ready=lambda _: True,
                                        pick_ready_worker=lambda *_: None))
    monkeypatch.setattr(C, "load_spec", lambda _: ({"s81_head": TYPE}, {}))
    monkeypatch.setattr(C, "launch_client", lambda *_: pytest.fail("no eligible worker"))
    args = SimpleNamespace(spec=None, die=["s81_head"], src=str(src), root=str(root),
                           image="img", dry=False, require_plan_review=True, plan_review_status=status)
    assert C.cmd_submit(args) == 0
    assert json.loads(status.read_text()) == {"deferred": ["s81_head"]}
    assert not root.exists()
