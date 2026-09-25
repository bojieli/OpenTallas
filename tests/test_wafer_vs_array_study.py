"""Checks for tools/wafer_vs_array_study.py, the iso-area ROM wafer versus ROM array decode study."""
from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import decode_critical_path as D  # noqa: E402
import wafer_vs_array_study as S  # noqa: E402

RESULT = ROOT / "results/roofline/critical_path/wafer_vs_array_iso_area.json"


@pytest.fixture(scope="module")
def env():
    tech = json.loads(D.TECH.read_text())
    clock, _ = D.routed_clock()
    return dict(renv=S._roofline_env(), tech=tech, links=D.link_consts(tech), clock=clock)


@pytest.fixture(scope="module")
def rec():
    return json.loads(RESULT.read_text())


def ctx_for(env, kind, n):
    s, d, pts = S.analytical_design(env["renv"], kind, n)
    return dict(kind=kind, devices=n, name=d["name"], designs={d["name"]: d}, points=pts,
                tensor_group=d["topology"]["tensor_group"])


def test_iso_area_pairs_never_give_the_array_more_silicon(env):
    for pr in S.iso_area_pairs(env["renv"]):
        assert pr["array_dies"] % S.DIES_PER_PACKAGE == 0
        assert pr["array_silicon_mm2"] <= pr["wafer_silicon_mm2"]
        assert 0 <= pr["array_residual_mm2"] < S.DIES_PER_PACKAGE * 815
    assert [p["array_dies"] for p in S.iso_area_pairs(env["renv"])] == [112, 168, 224, 680]


def test_designs_are_the_analytical_models_own(env):
    """The sizing is run_roofline_studies' code: regenerated points equal the published artifact."""
    published = json.loads(D.V41_POINTS.read_text())
    for kind, n in (("wafer", 2), ("wafer", 12), ("array", 188), ("array", 113)):
        _s, d, pts = S.analytical_design(env["renv"], kind, n)
        pub = {p["batch_size"]: p for p in published if p["design"] == d["name"]}
        assert pub, d["name"]
        for q in pts:
            assert q["per_user_tokens_s"] == pytest.approx(pub[q["batch_size"]]["per_user_tokens_s"], rel=1e-9)


def test_a_single_wafer_cannot_hold_the_weights_and_two_can(env):
    s, _d, _p = S.analytical_design(env["renv"], "wafer", 1)
    assert not s["feasible"] and any("stored weights" in r for r in s["reasons"])
    s2, _d, _p = S.analytical_design(env["renv"], "wafer", 2)
    assert s2["feasible"] and s2["weight_capacity_bytes"] >= s2["stored_weight_bytes"]
    assert S.minimum_devices(env["renv"], "wafer") == 2


def test_hbm_is_edge_limited_on_both_sides(env):
    w, _d, _p = S.analytical_design(env["renv"], "wafer", 2)
    a, _d, _p = S.analytical_design(env["renv"], "array", 112)
    assert w["hbm_stacks_per_device"] <= w["hbm_edge_limit_per_device"] == 43
    assert a["hbm_stacks_per_device"] <= a["hbm_edge_limit_per_device"]


def test_sinkhorn_knobs(env):
    c = D.v41_shape()
    ctx = ctx_for(env, "array", 188)

    def sk(**kw):
        p = replace(D.Params(), clock_hz=env["clock"], **kw)
        m = S._machine(ctx, "array", 4, 1, p, env["clock"], "rom_packed")
        return D.Built(m, p, env["clock"], D.v41_graph, c, m.context).g.nodes["L3.attn.hc.sinkhorn"]["depth"]
    base = sk()
    assert base == pytest.approx((2 + D.FADD + D.SU["EXP"] + 40 * (4 * D.FADD + 31)) / env["clock"])
    assert sk(sinkhorn_step_cycles=5) == pytest.approx((2 + D.FADD + D.SU["EXP"] + 40 * 5) / env["clock"])
    assert sk(sinkhorn=False) == 0.0
    sv = S.SINKHORN_VARIANTS[0]
    assert S.sinkhorn_chain_us(sv, env["clock"]) == pytest.approx(80 * base * 1e6)


def test_v41_machine_defaults_are_unchanged(env):
    points = json.loads(D.V41_POINTS.read_text())
    designs = {d["name"]: d for d in json.loads(D.V41_ANALYTICAL.read_text())["designs"]
               if d["name"] in (D.ARRAY_DESIGN, D.WAFER_DESIGN)}
    p = replace(D.Params(), clock_hz=env["clock"])
    a = D.v41_machine("wafer", 57, 1, points, designs, p, env["clock"])
    b = D.v41_machine("wafer", 57, 1, points, designs, p, env["clock"], design=D.WAFER_DESIGN, units=684,
                      per_layer=684 / 40, g_ref=57)
    assert a == b


def test_layouts(env):
    f = S.layer_fraction()
    assert 0.57 < f < 0.59
    assert S.per_layer_units("wafer", 12, "rom_packed") == pytest.approx(684 * f / 40)
    assert S.per_layer_units("array", 188, "uniform") == pytest.approx(4.7)


def test_placement_refusal(env):
    ctx = ctx_for(env, "wafer", 12)
    p = replace(D.Params(), clock_hz=env["clock"])
    packed = S.per_layer_units("wafer", 12, "rom_packed")
    m = S._machine(ctx, "wafer", 57, 1, p, env["clock"], "rom_packed")
    assert S.placement_refusal("wafer", 12, m, packed) is None
    # uniform layout, 57-field groups: 40 x 17.1 = 684 fields in 12 groups, the last one partial -> fits
    m = S._machine(ctx, "wafer", 57, 1, p, env["clock"], "uniform")
    assert S.placement_refusal("wafer", 12, m, 684 / 40) is None
    # a group of 28 fields tiles 2 per wafer (56 of 57): the uniform layout needs every field -> refused
    m = S._machine(ctx, "wafer", 28, 1, p, env["clock"], "uniform")
    assert S.placement_refusal("wafer", 12, m, 684 / 40)


def test_a_faster_wafer_fabric_is_never_slower(env):
    ctx = ctx_for(env, "wafer", 2)
    p = replace(D.Params(), clock_hz=env["clock"])
    rates = [S.best_config(ctx, "wafer", p, env["clock"], env["links"], dict(id="x", hop_s=h),
                           batches=(1,))["best_b1"]["tok_s_user_b1"] for h in (250e-9, 125e-9, 25e-9, 5e-9)]
    assert rates == sorted(rates)


def test_wire_limited_hop_is_derived_from_technology(env):
    v = {x["id"]: x for x in S.wafer_fabric_variants(env["tech"], env["clock"])}
    wire = env["tech"]["latency"]["global_wire_delay_s_per_mm"]["value"]
    assert v["express_wire_limited"]["hop_s"] == pytest.approx(math.sqrt(815) * wire + 1 / env["clock"])
    assert v["mesh_125"]["hop_s"] == env["links"]["on_wafer_n5"]["hop"]


def test_committed_result_is_consistent(rec):
    assert rec["schema"] == S.SCHEMA
    assert all(x["equal"] for x in rec["analytical_cross_check"] if x["published_per_user_b1"] is not None)
    for x in rec["comparisons"]:
        if "ratio_b1" in x:
            assert x["ratio_b1"] == pytest.approx(x["wafer_b1"] / x["array_b1"])
    assert len(rec["summary"]["headline"]) == len(S.WAFER_COUNTS)
    ids = {v["id"] for v in rec["axes"]["sinkhorn"]}
    assert ids == {v["id"] for v in S.SINKHORN_VARIANTS}


def test_committed_result_reproduces(env, rec):
    """One cell per side recomputed from source."""
    for key, kind, n, fv in (("wafer_x2", "wafer", 2, S.wafer_fabric_variants(env["tech"], env["clock"])[0]),
                             ("array_x112", "array", 112, S.ARRAY_LINK_VARIANTS[0])):
        row = next(g for g in rec["grid"] if g["point"] == key and g["sinkhorn"] == "fdiv31_built"
                   and g["fabric"] == fv["id"])
        p = replace(S.params_for(S.SINKHORN_VARIANTS[0]), clock_hz=env["clock"])
        r = S.best_config(ctx_for(env, kind, n), kind, p, env["clock"], env["links"], fv)
        assert r["best_b1"]["tok_s_user_b1"] == pytest.approx(row["best_b1"]["tok_s_user_b1"], rel=1e-9)
        assert r["best_aggregate_b4096"]["aggregate_tok_s_b4096"] == pytest.approx(
            row["best_aggregate_b4096"]["aggregate_tok_s_b4096"], rel=1e-9)
