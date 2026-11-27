"""Protect the captured bind and physical recipe for named station preparation."""
import hashlib
import json
from pathlib import Path

import pytest

import reviewed_station_prepare as reviewed


TYPE = "col_h9_r0_p2__t1__pv5752c4ff"


def emit(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def test_closed_producer_and_physical_source_are_independently_checked(tmp_path, monkeypatch):
    producer = emit(tmp_path / "producer.json", {})
    plan = emit(tmp_path / "physical.json", {"crop": 112.32})
    manifest = emit(tmp_path / "asbuilt.json", {})
    clock = emit(tmp_path / "physical-landing.json", {})
    proof = emit(tmp_path / "proof.json", {"schema": reviewed.bound_station_source.SCHEMA,
        "type": TYPE, "instance": "fE0_p2_b0", "producer_plan_sha256": producer["sha256"],
        "prepared_plan_sha256": plan["sha256"]})
    bind = tmp_path / "bind"
    native, physical = tmp_path / "native", tmp_path / "physical"
    emit(bind / "provenance_bind.json", {"provenance": {"step": "bind", "plan_sha256": producer["sha256"]}})
    emit(bind / "bind_report.json", {"n_errors": 0})
    emit(bind / "bind_tool.json", {"generators": {"reset_tree.py": "abc"}})
    generator = "tools/die_plan/gen_phys.py"
    gen = emit(physical / generator, {})
    recipe = emit(tmp_path / "recipe.json", {
        "schema": reviewed.SCHEMA, "type": TYPE, "bind_out": str(bind), "native_runtime": str(native),
        "producer_plan": producer, "plan": plan, "asbuilt": manifest, "station_receipt": proof,
        "clock_landing": clock, "physical_generator_files": {generator: gen["sha256"]},
    })
    calls = []
    def stamp(root):
        assert root == native
        return {"reset_tree.py": "abc"}
    def matches(raw, item, directory, asbuilt, plan_path):
        calls.append((directory, item, asbuilt, plan_path))
        return True
    monkeypatch.setattr(reviewed.bind_tool_stamp, "generator_hashes", stamp)
    monkeypatch.setattr(reviewed.kit_topology, "bind_matches", matches)
    scope = {"type_name": TYPE, "plan": plan["path"], "asbuilt": manifest["path"],
             "bind_out": str(bind), "tools": physical}
    assert reviewed.verify(recipe["path"], recipe["sha256"], **scope)["instance"] == "fE0_p2_b0"
    assert calls == [(bind, TYPE, Path(manifest["path"]), Path(producer["path"]))]
    with pytest.raises(ValueError, match="named P2 or H10"):
        reviewed.verify(recipe["path"], recipe["sha256"], **dict(scope, type_name="outside__t1"))
    with pytest.raises(ValueError, match="recipe.json"):
        reviewed.verify(recipe["path"], "0" * 64, **scope)
    emit(physical / generator, {"changed": True})
    with pytest.raises(ValueError, match="gen_phys.py"):
        reviewed.verify(recipe["path"], recipe["sha256"], **scope)
    emit(Path(clock["path"]), {"changed": True})
    with pytest.raises(ValueError, match="physical-landing.json"):
        reviewed.verify(recipe["path"], recipe["sha256"], **scope)


def test_guidance_preserves_stock_frame_and_edge_hook_order(tmp_path, monkeypatch):
    import gen_phys
    import p2_review_guides as guide

    exact = {name: emit(tmp_path / "source" / name, {"input": name}) for name in guide.FILES}
    recipe = emit(tmp_path / "recipe.json", {"type": guide.TYPE, "p2_guides": exact})
    cfg = ["export PRE_DETAIL_PLACE_TCL = /work/stock-before.tcl",
           "export POST_DETAIL_PLACE_TCL = /work/stock-after.tcl"]
    terminal = [[1, 2]]
    monkeypatch.setattr(guide, "TERMINAL_SEATS", hashlib.sha256(b"[[1,2]]").hexdigest())
    plan = {"outline_um": [1442.88, 1166.4], "ft_slots": [{"name": "ft0", "bit_sites_um": [terminal]}]}
    kit = tmp_path / "kit"
    kit.mkdir()
    cfg += guide.install(cfg, kit, guide.TYPE, plan, gen_phys.stage_hook_lines, recipe["path"], recipe["sha256"])
    assert [line for line in cfg if line.startswith("export PRE_DETAIL_PLACE_TCL")] == [
        "export PRE_DETAIL_PLACE_TCL = /work/p2_edge_corridor_setup.tcl"]
    assert [line for line in cfg if line.startswith("export POST_DETAIL_PLACE_TCL")] == [
        "export POST_DETAIL_PLACE_TCL = /work/p2_edge_corridor_check.tcl"]
    assert "source /work/stock-before.tcl\nsource /work/p2_frame_bridge_group.tcl" in (
        kit / "p2_frame_pre_detail.tcl").read_text()
    assert "source /work/p2_frame_pre_detail.tcl\nsource /work/p2_edge_corridor_pre_detail.tcl" in (
        kit / "p2_edge_corridor_setup.tcl").read_text()
    assert "source /work/stock-after.tcl\nsource /work/p2_frame_bridge_gate.tcl" in (
        kit / "p2_frame_post_detail.tcl").read_text()
    assert "source /work/p2_frame_post_detail.tcl\nsource /work/p2_edge_corridor_post_detail.tcl" in (
        kit / "p2_edge_corridor_check.tcl").read_text()
