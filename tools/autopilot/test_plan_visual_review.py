"""A repair needs a fresh plan image, and an exact retry reuses its review."""
import base64
import json
from subprocess import CompletedProcess

import pytest

import kit_wave as K
import plan_visual_review as PVR
import launch_gate


@pytest.fixture
def spec(tmp_path):
    plan = tmp_path / "plan.json"
    plan.write_text('{"partition_types":{"t1":{"outline":[10,20]}}}')
    return {"die": "s81", "item": "t1", "kind": "type", "plan": str(plan),
            "gen_host": "localhost", "hub": "localhost", "work": str(tmp_path / "kit"),
            "launch_plan_review_required": True, "src": "/old/tree", "src_manifest_hash": "b" * 64,
            "gen_env": {"OT_FLOW_TAG": "previous", "OT_FENCE_PATH": "/old/tree/fence"}}


def receipt(req, decision, image_sha="a" * 64):
    return "\t".join(("2026-11-26", req["die"], req["item"], req["form_sha256"],
                     decision, "/scratch/layout.png", image_sha, "reviewer", "Measured channels")) + "\n"


def test_exact_retry_reuses_review(spec, tmp_path):
    request = PVR.request(spec)
    accepted = receipt(request, "GOOD")
    copy = tmp_path / "renamed.json"
    copy.write_bytes((tmp_path / "plan.json").read_bytes())
    retry = dict(spec, plan=str(copy), work="/other/attempt_2", src="/new/tree",
                 gen_env={"OT_FLOW_TAG": "next", "OT_FENCE_PATH": "/new/tree/fence"})
    assert K.plan_visual_refusal(retry, tmp_path, "localhost", ledger=accepted) == ""
    assert "BAD fresh plan image" in K.plan_visual_refusal(
        retry, tmp_path, "localhost", ledger=accepted + receipt(request, "BAD"))
    copy.write_text('{"partition_types":{"t1":{"outline":[11,20]}}}')
    assert "missing fresh plan image" in K.plan_visual_refusal(retry, tmp_path, "localhost", ledger=accepted)
    assert "missing fresh plan image" in K.plan_visual_refusal(
        spec, tmp_path, "localhost", ledger=receipt(request, "GOOD", "broken"))


def test_overlay_and_physical_recipe_are_part_of_form(spec, tmp_path):
    request = PVR.request(spec)
    overlay = tmp_path / "overlay.json"
    overlay.write_text('{"x": 12}')
    accepted = receipt(request, "GOOD")
    assert "missing fresh plan image" in K.plan_visual_refusal(
        dict(spec, type_overlay=str(overlay)), tmp_path, "localhost", ledger=accepted)
    assert "missing fresh plan image" in K.plan_visual_refusal(
        dict(spec, leafslew_form={"side": "east"}), tmp_path, "localhost", ledger=accepted)


@pytest.mark.parametrize("goal", ["place", "geom", "route"])
def test_private_fresh_place_uses_live_policy_and_actual_seal(spec, tmp_path, monkeypatch, goal):
    spec_path = tmp_path / "spec.json"
    saved = dict(spec, private={"lane": "review"}, goal=goal, root=str(tmp_path),
                 ot_run="/fake/ot-run", src_manifest="seal", src_manifest_hash="")
    saved.pop("launch_plan_review_required")
    spec_path.write_text(json.dumps(saved))
    monkeypatch.setattr(K, "runitem_bind_landing", lambda _sp: None)
    monkeypatch.setattr(K, "repick_stage_hosts", lambda sp: sp)
    monkeypatch.setattr(K, "private_spec_stale", lambda _sp: "")
    monkeypatch.setattr(K, "private_lbl_refusal", lambda *_a: "")
    monkeypatch.setattr(K, "pre_gen_inputs", lambda *_a: [])
    monkeypatch.setattr(K, "pre_gen_probe_cmd", lambda *_a: "read-only-input-probe")
    monkeypatch.setattr(K, "pre_gen_plan_probe_cmd", lambda *_a: "true")
    monkeypatch.setattr(K, "src_manifest_cmd", lambda _sp: "seal-exact-tree")
    monkeypatch.setattr(K, "private_config_text", lambda *_a, **_kw:
                        '{"dies": {"s81": {"launch_plan_review_required": ["t1"]}}}')
    monkeypatch.setattr(launch_gate, "private_goal", lambda *_a, **_kw: goal)
    monkeypatch.setattr(PVR, "read_ledger", lambda _hub: "")
    probe = []
    actual_source = "c" * 64

    def run(argv, **kwargs):
        if argv[-1] == "read-only-input-probe; true":
            return CompletedProcess(argv, 0, "")
        probe.append(argv[-1])
        if argv[-1].startswith("mkdir"):
            return CompletedProcess(argv, 1, "test stops before generation")
        assert argv[-1] == "seal-exact-tree", "unexpected launch before review"
        return CompletedProcess(argv, 0, "SRC_MANIFEST_SEAL " + json.dumps({
            "manifest_hash": actual_source, "main_sha": "d" * 40
        }))

    monkeypatch.setattr(K.subprocess, "run", run)
    assert K.run_item(spec_path) != 0
    assert probe == ["seal-exact-tree"]
    assert json.loads((tmp_path / "result.json").read_text())["stage"] == "plan_visual"
    candidate = json.loads((tmp_path / "plan_visual_request.json").read_text())
    assert candidate["source_manifest_sha256"] == actual_source
    assert candidate["form_sha256"] == PVR.request(dict(saved, src_manifest_hash=actual_source))["form_sha256"]

    if goal == "place":
        # Recheck the actual source after review, then allow the original place-only path.
        monkeypatch.setattr(PVR, "read_ledger", lambda _hub: receipt(candidate, "GOOD"))
        probe.clear()
        assert K.run_item(spec_path) != 0
        assert len(probe) == 2 and probe[0] == "seal-exact-tree" and probe[1].startswith("mkdir")
        assert json.loads((tmp_path / "result.json").read_text())["stage"] == "mkdir"


def test_private_plan_review_names_exact_source_and_rejects_unsealed(spec, tmp_path):
    private = dict(spec, private={"lane": "review"})
    request = PVR.request(private)
    accepted = receipt(request, "GOOD")
    assert not K.plan_visual_refusal(private, tmp_path, "localhost", ledger=accepted)
    changed = dict(private, src_manifest_hash="e" * 64)
    assert "missing fresh plan image" in K.plan_visual_refusal(changed, tmp_path, "localhost", ledger=accepted)
    for missing in ("", "f" * 40):
        unsealed = dict(private, src_manifest_hash=missing, src_sha="d" * 40)
        assert "exact sealed or verified source manifest SHA-256" in K.plan_visual_refusal(
            unsealed, tmp_path, "localhost", ledger=accepted)


def test_scope_and_dry_run(spec, tmp_path):
    for other in (dict(spec, die="hbm"), dict(spec, kind="core"), dict(spec, launch_plan_review_required=False)):
        assert K.plan_visual_refusal(other, tmp_path, "localhost", ledger="") == ""
    assert K.plan_visual_refusal(spec, tmp_path, "localhost", ledger="", record=False)
    assert not (tmp_path / "plan_visual_request.json").exists()


def test_cli_records_and_rejects_stale_plan(spec, tmp_path, monkeypatch):
    req = tmp_path / "request.json"
    PVR.write_request(req, PVR.request(spec))
    image = tmp_path / "layout.png"
    image.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aK1sAAAAASUVORK5CYII="))
    ledger = tmp_path / PVR.LEDGER
    ledger.parent.mkdir()
    argv = ["plan_visual_review.py", str(req), "--coord", str(tmp_path), "--image", str(image),
            "--verdict", "GOOD", "--reviewer", "fixture", "--finding", "exact image"]
    monkeypatch.setattr("sys.argv", argv)
    PVR.main()
    assert PVR.verdict(ledger.read_text(), PVR.request(spec)) == "GOOD"
    old = ledger.read_text()
    (tmp_path / "plan.json").write_text("{}")
    with pytest.raises(SystemExit, match="1"):
        PVR.main()
    assert ledger.read_text() == old


def test_legacy_wave_exact_only_and_bad_wins(spec, tmp_path, monkeypatch):
    request = PVR.request(spec)
    record = {"die": spec["die"], "item": spec["item"], "plan_sha": request["plan_sha256"],
              "dir": str(tmp_path), "started": 1}
    (tmp_path / "spec.json").write_text(json.dumps(spec))
    monkeypatch.setattr(K, "exact_kit_visual_verdict", lambda *_a, **_k: "GOOD")
    assert K.plan_visual_refusal(spec, tmp_path, "localhost", ledger="", prior=record) == ""
    assert spec["plan_visual_legacy_form_sha"] == request["form_sha256"]
    assert K.plan_visual_refusal(spec, tmp_path, "localhost", ledger="") == ""
    assert "BAD fresh plan image" in K.plan_visual_refusal(
        spec, tmp_path, "localhost", ledger=receipt(request, "BAD"), prior=record)
    assert "missing fresh plan image" in K.plan_visual_refusal(
        dict(spec, private={"lane": "review"}), tmp_path, "localhost", ledger="", prior=record)
    assert "missing fresh plan image" in K.plan_visual_refusal(
        dict(spec, gen_args=["--different"]), tmp_path, "localhost", ledger="", prior=record)


def test_explicit_rollout_scope():
    assert PVR.enabled(["t1", "near_*"], "s81", "near_one", "type")
    assert not PVR.enabled(["t1", "near_*"], "s81", "t2", "type")
    assert not PVR.enabled(True, "hbm", "t1", "type")
    assert not PVR.enabled(True, "s81", "t1", "core")


def test_receipt_is_committed_once(tmp_path):
    import subprocess
    repo = tmp_path / "coord"
    (repo / "lanes").mkdir(parents=True)
    git = lambda *a: subprocess.run(["git", "-C", str(repo)] + list(a), capture_output=True, text=True, check=True).stdout
    git("init", "-q")
    ledger = repo / PVR.LEDGER
    ledger.write_text(PVR.HEADER + "row\n")
    assert PVR.commit_receipt(ledger, "s81/t1/abc")
    assert git("show", f"HEAD:{PVR.LEDGER}") == ledger.read_text()
    assert "plan visual review receipt s81/t1/abc" in git("log", "-1", "--format=%s")
    n = git("rev-list", "--count", "HEAD")
    assert not PVR.commit_receipt(ledger, "s81/t1/abc")
    assert git("rev-list", "--count", "HEAD") == n
