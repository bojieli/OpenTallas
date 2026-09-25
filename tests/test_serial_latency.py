"""Checks for the per-token operator dependency graph (src/opentallas/critical_path.py),
the serial-latency model every roofline point is priced with, and its reporting
tool tools/serial_latency_report.py."""
from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

import serial_latency_report as D  # noqa: E402
from opentallas import critical_path as C  # noqa: E402
from opentallas.roofline import (  # noqa: E402
    Technology,
    Topology,
    ValidationError,
    evaluate,
    rom_device_budget,
    taalas_hc1_anchor,
)
from opentallas.schema import ModelProfile  # noqa: E402

RESULT = ROOT / "results/roofline/critical_path/serial_latency_report.json"
V41 = ROOT / "configs/models/candidates/deepseek-v4.1-flash.json"
QWEN = ROOT / "configs/models/qwen3-8b.json"
MODELS = [
    ROOT / "configs/models/anchors/llama-3.1-8b.json",
    QWEN,
    ROOT / "configs/models/deepseek-v4-flash-0731.json",
    ROOT / "configs/models/deepseek-v4-pro-0813.json",
    V41,
    ROOT / "configs/models/candidates/deepseek-v4.1-flash-engram_hbm.json",
    ROOT / "configs/models/candidates/deepseek-v4.1-flash-engram_host.json",
    ROOT / "configs/models/candidates/kimi-k3-attention_ops.json",
    ROOT / "configs/models/candidates/mimo-v2.6-pro.json",
    ROOT / "configs/models/candidates/mimo-v2.6-flash.json",
    ROOT / "configs/models/candidates/qwen3-8b-context-extended.json",
]
ARRAY = ("rom_package_ucie", "rom_board_serdes", 4, 0)


@pytest.fixture(scope="module")
def tech():
    return Technology.load(ROOT / "configs/hardware/technology.json")


def rom_machine(group=4, mb=1.0, **kw):
    return C.MachineSpec(family="rom", group=group, microbatch=mb, clock_hz=1.0339e9, su_width=256,
                         kv_in_hbm=True, multi_stage=group > 1, **kw)


def graph(tech, path=V41, group=4, links=ARRAY, ctx=200_000, **kw):
    return C.serial_graph(tech, ModelProfile.load(path), context_tokens=ctx, machine=rom_machine(group, **kw),
                          fabric_links=links if group > 1 else None)


# -- the RTL the graph is priced with -----------------------------------------------------------------
def test_select_latency_is_the_campaigns(tech):
    camp = json.loads((ROOT / "results/rtl/hdc_v41_select_campaign.json").read_text())
    extra = C.RomDatapath.from_technology(tech).select_extra
    for cfg in camp["configurations"]:
        asc = cfg["order"] == "ascending index"
        assert D.select_latency(cfg["K"], asc, extra) == cfg["latency_cycles"], cfg["name"]


def test_technology_datapath_is_the_rtl_timing_model(tech):
    # every executed depth in serial_latency.rom_datapath equals tools/hdc_timing.py K, the routed stream
    # lane area and the slowest routed clock among the token path's units.  When an RTL change moves one,
    # the fix is mechanical and named: `python3 tools/sync_serial_latency_constants.py && python3
    # tools/regenerate_roofline.py`, then re-take the prose-figure census and commit the artifacts.
    import sync_serial_latency_constants as sync
    assert sync.drift(tech.raw) == {}, f"stale serial-latency constants: run `{sync.REGEN}`"
    assert D.rtl_constant_check(tech) == {}
    clock, rows = D.routed_clock()
    assert clock == min(r["fmax_hz"] for r in rows)


def test_serial_inputs_follow_the_grading_convention(tech):
    block = tech.raw["serial_latency"]
    for side in ("rom_datapath", "gpu_datapath"):
        for name, node in block[side].items():
            if not isinstance(node, dict):
                continue
            assert node["grade"] in ("executed", "published", "derived", "assumed"), name
            assert node.get("source"), name
            if node["grade"] == "assumed":
                assert "range_low" in node and "range_high" in node, name
    gap = block["gpu_datapath"]["kernel_launch_gap_s"]
    assert gap["grade"] == "published" and gap["range_low"] < gap["value"] < gap["range_high"]


# -- the graph and its solve -----------------------------------------------------------------------------
def test_parallel_branches_take_the_max_and_serial_ones_add():
    g = C.Graph()
    a = g.add("a", [], layer=0, depth=3.0)
    b = g.add("b", [a], layer=0, depth=5.0)
    c = g.add("c", [a], layer=0, depth=2.0)
    d = g.add("d", [b, c], layer=0, depth=1.0)
    fin = g.solve()
    assert fin[d] == pytest.approx(9.0)
    assert g.path(d) == ["a", "b", "d"]


@pytest.mark.parametrize("path", MODELS, ids=lambda p: p.stem)
def test_every_study_model_has_a_graph_and_its_envelope_is_exact(tech, path):
    sg = graph(tech, path, ctx=8192)
    for share in (0.0, C.kv_share_bucket(30e-6, 5e-6), 0.9):
        lines = sg.lines(share)
        for S in (0.0, 1e-6, 35e-6, 2e-3):
            T, _, _ = C.envelope_point(lines, S)
            exact = sg.graph.solve(S * (1 - share), S * share)[sg.sink]
            assert T == pytest.approx(exact, rel=1e-12, abs=1e-15), (path.stem, share, S)


@pytest.mark.parametrize("family", ["rom", "gpu"])
def test_repricing_equals_a_fresh_build(tech, family):
    """The study path builds each structure once and re-prices it per microbatch and lane width;
    that must equal building the graph at those values, collectives and all."""
    prof = ModelProfile.load(V41)
    for mb, su in ((1.0, 16), (7.5, 256), (64.0, 1024)):
        m = C.MachineSpec(family=family, group=4, microbatch=mb, clock_hz=1.0339e9 if family == "rom" else 1.965e9,
                          su_width=su, kv_in_hbm=True, multi_stage=True)
        fresh = C.serial_graph(tech, prof, context_tokens=200_000, machine=m, fabric_links=ARRAY)
        exact = fresh.graph.compile(fresh.sink)
        cheap, _ = C.serial_compiled(tech, prof, context_tokens=200_000, machine=m, fabric_links=ARRAY)
        for W, K in ((0.0, 0.0), (20e-6, 5e-6), (3e-3, 1e-3)):
            assert cheap.solve(W, K) == pytest.approx(exact.solve(W, K), rel=1e-12)
            assert exact.solve(W, K)[0] == pytest.approx(fresh.graph.solve(W, K)[fresh.sink], rel=1e-12)


def test_chaining_is_never_slower(tech):
    sg = graph(tech)
    assert sg.graph.solve(20e-6, 5e-6, chaining=True)[sg.sink] <= sg.graph.solve(20e-6, 5e-6, chaining=False)[sg.sink]


def test_breakdown_sums_to_the_critical_path(tech):
    sg = graph(tech)
    det = sg.detail(20e-6, 5e-6)
    assert sum(det["breakdown_s"].values()) == pytest.approx(det["critical_path_s"], rel=1e-9)


def test_unknown_structure_is_refused(tech):
    prof = ModelProfile.load(QWEN)
    with pytest.raises(ValidationError, match="no entry"):
        C.decode_shape(replace(prof, name="Unlisted-Model"), 8192)
    meta = dict(prof.metadata)
    meta.pop("num_key_value_heads")
    with pytest.raises(ValidationError, match="num_key_value_heads"):
        C.decode_shape(replace(prof, name="Qwen3-8B", metadata=meta, source_revision="stripped"), 8192)


# -- collectives ------------------------------------------------------------------------------------------
def test_v41_collectives_are_enumerated_not_assumed(tech):
    sg = graph(tech)
    census = C.collective_census(sg.census, 40)
    for every in ("attn.a_allgather", "attn.rows_allgather", "attn.out_allreduce", "ffn.router_allgather",
                  "ffn.combine_allreduce"):
        assert census[every]["count"] == 40, every
    shape = sg.shape
    assert census["attn.idx.topk_merge"]["layers"] == shape.dsv4["index_source_layer_ids"]
    assert census["head.argmax_merge"]["count"] == 1
    assert "attn.wo_a_group_reduce" not in census          # 4 partitions <= 8 o-groups: group-local
    wide = C.collective_census(graph(tech, group=16).census, 40)
    assert wide["attn.wo_a_group_reduce"]["count"] == 40
    per_layer = sum(1 for e in sg.census if e["op"] != "hop") / 40
    assert per_layer > 5.0                                  # not the 2 per layer the flat model charged


def test_dense_models_keep_two_collectives_per_layer(tech):
    sg = graph(tech, QWEN, ctx=8192)
    per_layer = sum(1 for e in sg.census if e["name"].startswith("L")) / 36
    assert per_layer == pytest.approx(2.0)


def test_payloads_are_real(tech):
    sg = graph(tech)
    out = next(e for e in sg.census if e["name"] == "L3.attn.out_allreduce")
    assert out["payload_bytes"] == 5120 * 4                 # FP32 partials, not BF16 activations
    # a stage boundary carries the four hyper-connection copies and the pending FP32 mix
    assert C.residual_bytes(sg.shape) == 4 * 5120 * 2 + 4 * 4
    mb8 = graph(tech, mb=8.0)
    out8 = next(e for e in mb8.census if e["name"] == "L3.attn.out_allreduce")
    assert out8["payload_bytes"] == 8 * out["payload_bytes"]


def test_sinkhorn_is_a_side_branch_joined_at_hc_post(tech):
    sg = graph(tech)
    n = sg.graph.nodes["L3.attn.hc_post"]
    assert "L3.attn.hc.sinkhorn" in n["deps"]
    assert "L3.attn.hc.sinkhorn" not in sg.graph.nodes["L3.attn.hc_pre"]["deps"]


def test_one_shot_beats_two_step_on_a_small_crossbar(tech):
    fab = C.Fabric(tech, inner="rom_package_ucie", outer="rom_board_serdes", domain=4, partitions=0, group=4)
    lv = fab._level("rom_package_ucie", 4)
    assert lv.price("all_reduce", 20480, "one_shot")[0] < lv.price("all_reduce", 20480, "two_step")[0]
    assert fab.collective("all_reduce", 20480, 4)["algo"] == "one_shot"


def test_centre_mesh_is_1p1_diameter(tech):
    fab = C.Fabric(tech, inner="on_wafer_n5", outer="rom_wafer_serdes", domain=57, partitions=0, group=19)
    lv = fab._level("on_wafer_n5", 19)
    hop = tech.link("on_wafer_n5")[0].value
    r, c = C.mesh_dims(19)
    assert lv.price("all_reduce", 20480, "centre_mesh")[0] == pytest.approx(1.1 * ((r - 1) + (c - 1)) * hop)


def test_spanning_domains_is_hierarchical(tech):
    fab = C.Fabric(tech, inner="rom_package_ucie", outer="rom_board_serdes", domain=4, partitions=0, group=16)
    r = fab.collective("all_reduce", 20480, 16)
    assert r["algo"] == "hierarchical"
    assert r["latency_s"] > fab.collective("all_reduce", 20480, 4)["latency_s"]


def test_a_measured_link_is_charged_its_measured_floor(tech):
    fab = C.Fabric(tech, inner="nvlink5", outer="infiniband_ndr", domain=8, partitions=0, group=8)
    r = fab.collective("all_reduce", 0.0, 8)
    assert r["algo"] == "measured_floor"
    assert r["latency_s"] == pytest.approx(tech.collective_traversals("nvlink5", 8) * tech.link("nvlink5")[0].value)


# -- the GPU side -------------------------------------------------------------------------------------------
def test_gpu_pays_a_published_launch_gap_per_dependent_kernel(tech):
    prof = ModelProfile.load(QWEN)
    m = C.MachineSpec(family="gpu", group=1, microbatch=1.0, clock_hz=1.965e9)
    sg = C.serial_graph(tech, prof, context_tokens=8192, machine=m, fabric_links=None)
    det = sg.detail(0.0, 0.0)
    gap = tech.raw["serial_latency"]["gpu_datapath"]["kernel_launch_gap_s"]["value"]
    kernels = det["breakdown_s"]["kernel_launch"] / gap
    assert kernels == pytest.approx(round(kernels))
    assert 6 * 36 <= kernels <= 14 * 36 + 10       # 6-14 dependent kernels per dense layer


# -- the roofline integration ------------------------------------------------------------------------
def test_hybrid_tensor_group_is_searched_per_point(tech):
    prof = ModelProfile.load(QWEN)
    topo = Topology(kind="array", device_count=16, parallelism="hybrid", link="rom_board_serdes",
                    intra_link="rom_package_ucie", intra_domain_size=4, tensor_group_size=4)
    budget = rom_device_budget(tech, name="probe", node="N5", area_mm2_per_device=815.0, topology=topo,
                               stored_weight_bytes=prof.checkpoint_bytes, resident_kv_bytes=0.0, kv_store="hbm",
                               hbm_stacks=1)
    step = evaluate(budget, prof, context_tokens=8192, batch_size=1, technology=tech)
    search = step.metrics["serial_latency"]["tensor_group_search"]
    groups = [row["tensor_group"] for row in search]
    assert groups[0] == 4 and {2, 8} <= set(groups)
    best = min(search, key=lambda row: row["step_s"])
    assert step.metrics["tensor_group"] == best["tensor_group"]
    assert step.step_time_s == pytest.approx(best["step_s"] * step.thermal_scale)


def test_step_is_never_below_the_sweep_nor_the_serial_terms(tech):
    prof = ModelProfile.load(V41)
    topo = Topology(kind="array", device_count=188, parallelism="hybrid", link="rom_board_serdes",
                    intra_link="rom_package_ucie", intra_domain_size=4, tensor_group_size=4)
    budget = rom_device_budget(tech, name="probe", node="N5", area_mm2_per_device=815.0, topology=topo,
                               stored_weight_bytes=prof.checkpoint_bytes, resident_kv_bytes=0.0, kv_store="hbm",
                               hbm_stacks=1)
    for batch in (1, 64):
        step = evaluate(budget, prof, context_tokens=200_000, batch_size=batch, technology=tech)
        ct, sl = step.component_times_s, step.metrics["serial_latency"]
        assert step.step_time_s >= sl["sweep_s"] - 1e-15
        assert step.step_time_s >= ct["link_latency"] + ct["layer_fixed_latency"] - 1e-15
        assert sl["collectives_per_layer"] > 5.0
        assert ct["layer_fixed_latency"] > 10 * step.metrics["legacy_layer_fixed_latency_s"]


# -- the HC1 gate and the committed result ----------------------------------------------------------------
def test_hc1_gate_is_reported_not_fitted(tech):
    chk = taalas_hc1_anchor(tech, ModelProfile.load(ROOT / "configs/models/anchors/llama-3.1-8b.json"))
    assert chk.tolerance == 2.0
    band = chk.detail["layer_fixed_latency_band"]
    assert band["low"]["modelled_tokens_s"] >= band["stated"]["modelled_tokens_s"] >= band["high"]["modelled_tokens_s"]
    assert band["stated"]["modelled_tokens_s"] == pytest.approx(chk.modelled_value)
    # the serial chain the gate charges is the graph's, an order above the flat floor it replaced
    assert band["stated"]["layer_fixed_latency_s_per_token"] > 5 * band["stated"]["legacy_floor_s_per_token"]


def test_committed_result_reproduces(tech):
    rec = json.loads(RESULT.read_text())
    assert rec["schema"] == D.SCHEMA
    assert rec["rtl_constant_mismatches"] == {}
    fresh = D.build()
    for key in ("hc1_llama31_8b", "qwen3_8b_single_reticle"):
        assert fresh[key]["tokens_s_per_user"] == pytest.approx(rec[key]["tokens_s_per_user"], rel=1e-9)
    for key, row in rec["deepseek_v41_flash"].items():
        f = fresh["deepseek_v41_flash"][key]
        assert f["tokens_s_per_user"] == pytest.approx(row["tokens_s_per_user"], rel=1e-9), key
        # the wrapper's re-attribution of a study row lands on the study's own rate (the KV:weight
        # split of the sweep is quantised to 1/16 decade, so equality is to 1e-6)
        assert row["tokens_s_per_user"] == pytest.approx(row["study_tokens_s_per_user"], rel=1e-6), key
    assert math.isclose(fresh["clock"]["hz"], rec["clock"]["hz"])


# -- the wafer express network ---------------------------------------------------------------------------
def test_express_link_is_derived_from_the_wire_delay_and_the_field_pitch(tech):
    e = tech.raw["links"]["rom_wafer_express"]
    wire = tech.raw["latency"]["global_wire_delay_s_per_mm"]
    pitch_mm = math.sqrt(tech.raw["reticle"]["area_mm2"]["value"])
    for key in ("value", "range_low", "range_high"):
        assert e["hop_latency_s"][key] == pytest.approx(pitch_mm * wire[key] + e["router_latency_s"][key], rel=1e-12)
    wires = pitch_mm * 1000 / e["wire_track_pitch_um"]["value"] * e["wire_layers"]["value"] * e["wire_track_share"]["value"]
    assert e["bytes_s"]["value"] == pytest.approx(wires * e["wire_clock_hz"]["value"] / 8, rel=1e-12)
    # the Cerebras-style core mesh stays as it was: the conservative case
    assert tech.raw["links"]["on_wafer_n5"]["hop_latency_s"]["value"] == pytest.approx(125e-9)
    assert set(e["alternative_to"]) == {"on_wafer", "on_wafer_n5"}


def test_a_wafer_point_chooses_between_the_mesh_and_the_express_network(tech):
    prof = ModelProfile.load(V41)
    topo = Topology(kind="wafer", device_count=12, parallelism="hybrid", link="rom_wafer_serdes",
                    on_wafer_regions=684, intra_link="on_wafer_n5", intra_domain_size=57, tensor_group_size=57)
    budget = rom_device_budget(tech, name="probe", node="N5", area_mm2_per_device=46225.0, topology=topo,
                               stored_weight_bytes=prof.checkpoint_bytes, resident_kv_bytes=0.0, kv_store="hbm",
                               hbm_stacks=1)
    step = evaluate(budget, prof, context_tokens=200_000, batch_size=1, technology=tech)
    search = step.metrics["serial_latency"]["tensor_group_search"]
    assert {row["intra_link"] for row in search} == {"on_wafer_n5", "rom_wafer_express"}
    best = min(search, key=lambda row: row["step_s"])
    assert step.metrics["intra_link"] == best["intra_link"]
    mesh_only = min(row["step_s"] for row in search if row["intra_link"] == "on_wafer_n5")
    assert best["step_s"] <= mesh_only
    # a field crossing on the express network is ~17x shorter than on the core mesh, so at batch 1 it wins
    assert step.metrics["intra_link"] == "rom_wafer_express"


def test_sinkhorn_agrees_with_the_standalone_study(tech):
    """The roofline graph and tools/decode_critical_path.py price the Sinkhorn by one rule: the faster of
    the routed ot_hdc_sinkhorn unit and the pipelined fadd/fdiv chain, from the same artifacts."""
    import decode_critical_path as DCP
    rom = C.RomDatapath.from_technology(tech)
    assert rom.sinkhorn_clocks == DCP.SK["clocks"]
    assert rom.sinkhorn_step_s == pytest.approx(DCP.SK["step_s"], rel=1e-12)
    for mb in (1.0, 8.0, 64.0):
        sg = graph(tech, mb=mb)
        node = sg.graph.nodes["L3.attn.hc.sinkhorn"]
        ops = type("O", (), {})()
        ops.clock, ops.mb = rom.clock_hz, mb
        ops.p = replace(DCP.Params(), clock_hz=rom.clock_hz)
        cycles, _ = DCP.sinkhorn_cycles(ops, 20, 2 + rom.fadd + rom.su_exp)
        assert node["depth"] == pytest.approx(cycles / rom.clock_hz, rel=1e-12), mb
