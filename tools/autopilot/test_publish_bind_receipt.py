"""Focused publication reuse tests over sealed producer and replica artifacts."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import types

import pytest

import publish_apply as PA
import publish_bind_receipt as R


def dump(path, doc):
    path.write_bytes(R.canonical(doc))


@pytest.fixture
def completed_bind(tmp_path):
    tree = tmp_path / "source"
    (tree / "rtl").mkdir(parents=True)
    source_leaf = tree / "rtl/leaf.sv"
    source_leaf.write_text("module leaf; endmodule\n")
    plan, asbuilt = tree / "plan.json", tree / "asbuilt.json"
    dump(plan, {"partition_types": {"A": {}, "B": {}}})
    dump(asbuilt, {"kit_source_station_pricing": True})
    source = "a" * 64
    dump(tree / ".src-manifest.json", {"manifest_hash": source, "files": {
        str(p.relative_to(tree)): R.digest(p) for p in (plan, asbuilt, source_leaf)}})
    (tree / ".src-manifest.sha256").write_text(source + "\n")
    alias = tmp_path / "old_elab" / "rtl/leaf.sv"
    alias.parent.mkdir(parents=True)
    os.link(source_leaf, alias)
    for p in (plan, asbuilt, source_leaf):
        p.chmod(0o444)
    copy = tmp_path / "source_postbind_1"
    work = copy / PA.POSTBIND_DIR
    bind = work / "out"
    (bind / "rtl").mkdir(parents=True)
    (copy / ".link-base").write_text(str(tree) + "\n")
    for p in (plan, asbuilt):
        os.link(p, copy / p.name)
    rtl = bind / "rtl/A.sv"
    rtl.write_text("module A; leaf u_leaf(); endmodule\n")
    (bind / "bind.f").write_text(f"{alias}\n{rtl}\n")
    pin = "0123456789ab"
    marker = dict(die="qc", tree=str(tree), plan=str(plan), manifest_hash=source, plan_sha256=R.digest(plan),
                  config={"gen_hosts": ["h1"], "gen_tools_pin": pin,
                          "kit_rtl": {"mode": "bind", "bind_out": str(bind), "asbuilt": str(asbuilt)}})
    obj = {"marker": marker}
    inputs = PA.postbind_spec(obj, "t")["receipt_inputs"]
    dump(work / R.INPUT, inputs)
    dump(work / R.RESULT, {"elab": 0, "bind": 0, "latcheck": 0})
    keys = dict(A={}, B={})
    dump(bind / "bind_report.json", dict(plan_sha256=R.digest(plan), n_errors=0, unmapped=0, errors=[],
                                         types=keys, files=[str(rtl)]))
    dump(bind / "native_topology.json", dict(asbuilt_sha256=R.digest(asbuilt), types=keys))
    dump(bind / "bind_errors_all.json", dict(verdict="PASS", n_errors=0, errors=[]))
    dump(bind / "bind_tool.json", dict(tools_sha=pin))
    dump(bind / "provenance_bind.json", {})
    dump(bind / "bind_emit_par.json", dict(jobs=4))
    lane = dict(lane="L1", src="A0", dst="B0", bus_out="o", bus_in="i")
    dump(bind / "bind_latency.json", {"buses": [lane]})
    summary = dict(scope="die", pricing="as-bound", bound_pricing=True, verdict="PASS", failed=0,
                   unobserved=0, lanes=1, passed=1, bind_dir=str(bind), plan=str(copy / plan.name))
    dump(work / "latcheck.json", dict(summary=summary, lanes=[dict(lane, verdict="PASS", delta=0)]))
    return obj, inputs, bind, source_leaf, alias


def enroll(bind):
    sha = R.seal(bind)
    for p in bind.rglob("*"):
        p.chmod(0o555 if p.is_dir() else 0o444)
    bind.chmod(0o555)
    R.enroll(bind, sha)
    return sha


def test_exact_receipt_stat_only_reuse_and_legacy_alias(completed_bind, monkeypatch):
    _obj, inputs, bind, source_leaf, alias = completed_bind
    sha = enroll(bind)
    alias.unlink()
    assert str(source_leaf) in (bind / "bind.f").read_text()
    monkeypatch.setattr(R, "digest", lambda *_: pytest.fail("apply rehashed the bound RTL"))
    assert R.verify(bind, inputs, sha) == {"types": 2, "lanes": 1}
    with pytest.raises(ValueError, match="source/plan/asbuilt/runtime/environment"):
        R.verify(bind, dict(inputs, env={"OT_DIFFERENT": "1"}), sha)
    changed = bind / "rtl/A.sv"
    changed.chmod(0o644)
    changed.write_text("module wrong; endmodule\n")
    changed.chmod(0o444)
    with pytest.raises(ValueError, match="filesystem identity"):
        R.verify(bind, inputs, sha)


@pytest.mark.parametrize("mutation,match", [
    ("partial", "whole-die type set"), ("duplicate", "duplicate"), ("failed", "did not complete"),
    ("asbuilt", "asbuilt identity"), ("wrong_producer", "different bind"), ("foreign", "unproved external"),
])
def test_producer_refuses_partial_stale_and_foreign_evidence(completed_bind, mutation, match):
    _, _, bind, _, alias = completed_bind
    work = bind.parent
    if mutation in {"partial", "asbuilt"}:
        f = bind / "native_topology.json"
        top = R.read(f)
        if mutation == "partial":
            del top["types"]["B"]
        else:
            top["asbuilt_sha256"] = "wrong"
        dump(f, top)
    elif mutation in {"duplicate", "wrong_producer"}:
        f = work / "latcheck.json"
        lat = R.read(f)
        if mutation == "duplicate":
            lat["lanes"].extend(lat["lanes"])
            lat["summary"].update(lanes=2, passed=2)
        else:
            lat["summary"]["bind_dir"] = str(bind / "other")
        dump(f, lat)
    elif mutation == "failed":
        dump(work / R.RESULT, {"elab": 0, "bind": 0, "latcheck": 4})
    else:
        alias.unlink()
        alias.write_text("module different; endmodule\n")
    with pytest.raises(ValueError, match=match):
        R.seal(bind)
    assert not (bind / R.RECEIPT).exists()


def test_apply_consumes_valid_receipt_and_refuses_missing_replica(completed_bind, tmp_path, monkeypatch):
    obj, _, bind, _, _ = completed_bind
    sha = enroll(bind)
    candidate = tmp_path / "candidate.json"
    dump(candidate, obj)
    args = argparse.Namespace(coord=str(tmp_path), candidate=str(candidate), expect_source="old", expect_event="E0",
                              lane="S81", pilot_item=None, no_gate=True, no_precheck=True, reuse_post_bind=sha,
                              bind_check_fn=lambda *a, **k: (True, "matching", []),
                              postbind_fn=lambda *a, **k: pytest.fail("duplicate whole-die bind was started"))
    switched = []

    def ssh(argv, **kwargs):
        if argv[0] == "ssh":
            if argv[-2] == "missing-host":
                return types.SimpleNamespace(returncode=255, stdout="", stderr="unreachable")
            return subprocess.run(["bash", "-c", argv[-1]], **kwargs)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    def apply(_coord, candidate, *_args, verify_retained_bind, check_bind_config, **_kwargs):
        verify_retained_bind(["h1"] + extra_hosts)
        check_bind_config(config_at_cas)
        switched.append(candidate)
        return dict(applied="qc", receipt=str(tmp_path / "apply_receipt"), event="E1")

    monkeypatch.setattr(PA.A, "apply_marker", apply)
    extra_hosts = []
    config_at_cas = {"bind_env": {"OT_CHANGED_DURING_PUBLISH": "1"}}
    assert PA.cmd_apply(args, run=ssh, commit_fn=lambda *a: pytest.fail("changed config committed")) == 6
    assert not switched
    config_at_cas.clear()
    extra_hosts.append("missing-host")
    assert PA.cmd_apply(args, run=ssh, commit_fn=lambda *a: pytest.fail("invalid receipt committed")) == 6
    assert not switched
    extra_hosts.clear()
    committed = []
    assert PA.cmd_apply(args, run=ssh, commit_fn=lambda _c, res: committed.append(res) or "ok") == 0
    assert len(switched) == len(committed) == 1
    assert committed[0]["post_bind_reused"]["sha256"] == sha
    assert switched[0]["marker"]["config"]["bind_copy_of_record"] == [str(bind.parent.parent)]
