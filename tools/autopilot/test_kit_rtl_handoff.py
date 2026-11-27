import json
import subprocess

import pytest

import kit_rtl_closure as closure
import kit_rtl_handoff as handoff
import kit_wave


def producer(root):
    rtl = root / "producer/rtl"
    rtl.mkdir(parents=True)
    (rtl / "local.sv").write_text("module local; endmodule\n")
    (rtl / "kit_rtl.f").write_text(str(rtl / "local.sv") + "\n")
    closure_meta = {
        "sealed": True, "runtime_directory": str(rtl), "producer_directory": str(rtl),
        "files": {"local.sv": {"sha256": closure.digest(rtl / "local.sv"),
                               "original": str(rtl / "local.sv")}},
    }
    identity = {"item": "top", "wrapper": "2" * 64}
    assets = rtl / "assets"
    assets.mkdir()
    (assets / "sink.json").write_text("{}")
    handoff.write(rtl / "native_sink_censuses.json", {"sink": {
        "path": str(assets / "sink.json"), "sha256": closure.digest(assets / "sink.json"),
    }})
    handoff.write(rtl / "kit_rtl.json", {
        "schema": "opentallas.head_wave_kit_rtl.v1", "plan_type": "top",
        "published_wrapper_sha256": identity["wrapper"], "input_closure": closure_meta,
        "files": [str(rtl / "local.sv")],
    })
    return rtl, identity


def test_imported_stage_uses_origin_receipt_and_is_retryable(tmp_path):
    donor, identity = producer(tmp_path)
    before = (donor / "kit_rtl.json").read_bytes()
    receipt = handoff.publish(donor, identity)
    recipient = tmp_path / "consumer" / "rtl"
    recipient.parent.mkdir()
    installed = handoff.restore(recipient, receipt, donor, "")
    handoff.checked(recipient, installed)
    assert (recipient / "kit_rtl.f").read_text() == str(recipient / "local.sv") + "\n"
    census = handoff.read(recipient / "native_sink_censuses.json")["sink"]
    assert census["path"] == str(recipient / "assets" / "sink.json")
    assert closure.digest(recipient / "assets" / "sink.json") == census["sha256"]
    meta = handoff.read(recipient / "kit_rtl.json")["input_closure"]
    assert meta["producer_directory"] == str(donor)
    assert meta["runtime_directory"] == str(recipient)
    assert (donor / "kit_rtl.json").read_bytes() == before
    assert handoff.restore(recipient, receipt, donor, "") == installed
    with pytest.raises(ValueError, match="existing"):
        handoff.restore(recipient, dict(receipt, identity={"item": "changed"}), donor, "")


def test_changed_or_unsealed_files_are_not_installed(tmp_path):
    donor, identity = producer(tmp_path)
    receipt = handoff.publish(donor, identity)
    recipient = tmp_path / "new" / "rtl"
    recipient.parent.mkdir()
    (donor / "local.sv").write_text("changed")
    with pytest.raises(ValueError, match="differs"):
        handoff.restore(recipient, receipt, donor, "")
    assert not recipient.exists()
    assert list(recipient.parent.iterdir()) == []
    with pytest.raises(ValueError, match="invalid closure path"):
        handoff.restore(recipient, dict(receipt, files={"../escape": ""}), donor, "")


def test_exact_but_nonportable_rtl_is_not_installed(tmp_path):
    donor, identity = producer(tmp_path)
    payload = donor / "local.sv"
    payload.write_text(f'`include "{donor}/irreproducible.svh"\n')
    meta = handoff.read(donor / "kit_rtl.json")
    meta["input_closure"]["files"]["local.sv"]["sha256"] = closure.digest(payload)
    handoff.write(donor / "kit_rtl.json", meta)
    recipient = tmp_path / "new" / "rtl"
    recipient.parent.mkdir()
    with pytest.raises(ValueError, match="embeds the producer work directory"):
        handoff.restore(recipient, handoff.publish(donor, identity), donor, "")
    assert not recipient.exists()


def test_private_pointer_requires_exact_completed_producer(tmp_path):
    old = tmp_path / "old"
    old.mkdir()
    spec = {"die": "s81_head", "item": "top", "work": "/scratch/a",
            "gen_host": "epyc8", "private": {"lane": "head"}}
    handoff.write(old / "spec.json", spec)
    handoff.write(old / handoff.NAME, {"host": "epyc8", "rtl": "/scratch/a/rtl",
                                      "payload": {"schema": handoff.SCHEMA}})
    handoff.write(old / "result.json", dict(spec, verdict="RUNNING"))
    new = dict(spec, work="/scratch/b")
    with pytest.raises(ValueError, match="completed"):
        kit_wave.kit_rtl_predecessor(old, new)
    handoff.write(old / "result.json", dict(spec, verdict="FAIL"))
    pointer = kit_wave.kit_rtl_predecessor(old, new)
    assert pointer == {"attempt": str(old), "sha256": closure.digest(old / handoff.NAME)}
    assert kit_wave.input_hash(new) == kit_wave.input_hash(dict(new, kit_rtl_reuse=pointer))
    with pytest.raises(ValueError, match="distinct"):
        kit_wave.kit_rtl_predecessor(old, spec)


def test_controller_embeds_worker_in_isolated_python(tmp_path):
    donor, identity = producer(tmp_path)
    cmd = kit_wave.kit_rtl_handoff_cmd("publish", {"rtl": str(donor), "identity": identity})
    raw = subprocess.check_output(cmd, shell=True, text=True)
    assert kit_wave.kit_rtl_handoff_result(raw) == handoff.publish(donor, identity)


def test_verified_reuse_is_eligible_for_ordinary_gen_pilot(tmp_path):
    spec_path = tmp_path / "spec.json"
    spec = {"die": "s81_head", "item": "top", "src": "/exact",
            "src_manifest_hash": "a" * 64, "kit_rtl": {"mode": "script", "script": "/script"}}
    handoff.write(spec_path, spec)
    stages = dict.fromkeys(kit_wave.GEN_PILOT_STAGES, 0)
    stages.update(kit_rtl=0, kit_rtl_reuse=0)
    assert kit_wave.publish_gen_pilot_receipt(spec_path, closure.digest(spec_path), stages)
    rec = handoff.read(tmp_path / "gen_pilot.json")
    assert rec["stages"]["kit_rtl_reuse"] == 0
    assert kit_wave.gen_pilot_receipt_pass(tmp_path, "s81_head", "top", spec, spec_path.read_bytes())
