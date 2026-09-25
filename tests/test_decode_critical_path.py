"""Checks for tools/decode_critical_path.py, the bottom-up per-operator critical-path model."""
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

RESULT = ROOT / "results/roofline/critical_path/decode_critical_path.json"


@pytest.fixture(scope="module")
def env():
    tech = json.loads(D.TECH.read_text())
    links = D.link_consts(tech)
    clock, _ = D.routed_clock()
    p = replace(D.Params(), clock_hz=clock)
    points = json.loads(D.V41_POINTS.read_text())
    designs = {d["name"]: d for d in json.loads(D.V41_ANALYTICAL.read_text())["designs"]
               if d["name"] in (D.ARRAY_DESIGN, D.WAFER_DESIGN)}
    return dict(links=links, clock=clock, p=p, points=points, designs=designs, c=D.v41_shape())


def v41(env, kind="array", g=4, batch=1, **kw):
    p = replace(env["p"], **kw)
    m = D.v41_machine(kind, g, batch, env["points"], env["designs"], p, env["clock"])
    return D.Built(m, p, env["clock"], D.v41_graph, env["c"], m.context)


def test_select_latency_is_the_campaigns():
    camp = json.loads((ROOT / "results/rtl/hdc_v41_select_campaign.json").read_text())
    for cfg in camp["configurations"]:
        asc = cfg["order"] == "ascending index"
        assert D.select_latency(cfg["K"], asc) == cfg["latency_cycles"], cfg["name"]


def test_tselect_latency_is_the_campaigns():
    camp = json.loads((ROOT / "results/rtl/hdc_v41_tselect_campaign.json").read_text())
    assert camp["status"] == "pass"
    for cfg in camp["configurations"]:
        W = cfg["lanes"]
        assert D.tselect_lat0(W) == cfg["lat0"], cfg["name"]
        for run in cfg["runs"].values():
            # the priced worst case bounds every measured segment: 2 x beats + LAT0 (+1)
            assert D.tselect_lat0(W) <= run["lat0_min"] <= run["lat0_max"] <= D.tselect_lat0(W) + 1, cfg["name"]
    assert D.tselect_latency(512 * 4, 64) == 2 * 32 + 47 + 1
    assert all(m["caught"] != bool(m.get("control")) for m in camp["mutations"])
    assert sum(1 for m in camp["mutations"] if m.get("control")) == 1


def test_threshold_select_needs_no_order_pass_and_is_faster(env):
    thr, ins = v41(env), v41(env, select_impl="insertion")
    fab = D.default_fabric("array", env["links"], 4)
    rt, ri = thr.evaluate(fab), ins.evaluate(fab)
    a, b = D.index_select_report(thr, rt), D.index_select_report(ins, ri)
    assert sorted(a, key=int) == [str(L) for L in env["c"]["index_source_layer_ids"]]
    for L in a:
        assert "ascending" not in a[L]["steps"]["topk_final"]["desc"]
        assert "ascending-index pass" in b[L]["steps"]["topk_final"]["desc"]
        assert a[L]["total_us"] < b[L]["total_us"]
    assert rt["period"] < ri["period"]
    # one die: the local select is the whole top-k (no gather, no final pass)
    single = v41(env, g=1)
    assert not any(n.endswith("idx.topk_final") for n in single.g.nodes)


def test_tselect_split_takes_the_best_unit_count(env):
    b = v41(env)
    ops = b.ops
    n, k = 50000, 512
    iss, dep, P = ops._tsel_split(n, k)
    one = ops._tsel(n)
    assert iss + dep <= sum(one)
    assert 1 <= P <= b.p.tselect_units
    assert one == (math.ceil(n / 64), D.tselect_latency(n, 64))


def test_clock_is_the_slowest_routed_block():
    clock, rows = D.routed_clock()
    assert clock == min(r["fmax_hz"] for r in rows)
    assert 0.9e9 < clock < 1.2e9


def test_parallel_branches_take_the_max_and_serial_ones_add():
    g = D.Graph()
    a = g.add("a", [], layer=0, depth=3.0)
    b = g.add("b", [a], layer=0, depth=5.0)
    c = g.add("c", [a], layer=0, depth=2.0)
    d = g.add("d", [b, c], layer=0, depth=1.0)
    fin = g.solve()
    assert fin[d] == pytest.approx(9.0)
    assert g.path(d) == ["a", "b", "d"]


def test_chaining_is_never_slower(env):
    b = v41(env)
    fab = D.default_fabric("array", env["links"], 4)
    assert b.evaluate(fab)["T"] <= b.evaluate(fab, chaining=False)["T"]


def test_breakdown_sums_to_the_critical_path(env):
    b = v41(env)
    r = b.evaluate(D.default_fabric("array", env["links"], 4))
    assert sum(r["cats"].values()) == pytest.approx(r["T"], rel=1e-9)


def test_collectives_are_enumerated_not_assumed(env):
    b = v41(env)
    r = b.evaluate(D.default_fabric("array", env["links"], 4))
    census = D.collective_census(r)
    for every in ("attn.a_allgather", "attn.out_allreduce", "ffn.router_allgather", "ffn.combine_allreduce"):
        assert census[every]["count"] == 40, every
    assert census["attn.idx.topk_merge"]["layers"] == env["c"]["index_source_layer_ids"]
    assert "attn.wo_a_group_reduce" not in census          # 4 dies <= 8 o-groups: group-local
    wide = v41(env, g=16).evaluate(D.default_fabric("array", env["links"], 16))
    assert D.collective_census(wide)["attn.wo_a_group_reduce"]["count"] == 40


def test_sinkhorn_is_a_side_branch_joined_at_hc_post(env):
    b = v41(env)
    n = b.g.nodes["L3.attn.hc_post"]
    assert "L3.attn.hc.sinkhorn" in n["deps"]
    assert "L3.attn.hc.sinkhorn" not in b.g.nodes["L3.attn.hc_pre"]["deps"]


def test_sinkhorn_is_priced_from_the_routed_unit(env):
    """The Sinkhorn node is the SFU front plus ot_hdc_sinkhorn's campaign latency in unit clocks, each
    unit clock the routed step period rounded up to core cycles; the earlier pipelined pricing is slower."""
    camp = json.loads(D.SINKHORN_CAMPAIGN.read_text())
    phys = json.loads((D.PHYS / D.SINKHORN_BLOCK / "physical.json").read_text())["design"]
    assert camp["status"] == "pass"
    assert D.SK["clocks"] == camp["latency_cycles"] == 2 * env["c"]["hc_sinkhorn_iters"] + 1
    assert D.SK["step_s"] == pytest.approx(1.0 / phys["fmax_hz"])
    per = math.ceil(D.SK["step_s"] * env["clock"] - 1e-9)
    front = 2 + D.FADD + D.SU["EXP"]
    b = v41(env)
    n = b.g.nodes["L3.attn.hc.sinkhorn"]
    assert n["depth"] == pytest.approx((front + D.SK["clocks"] * per) / env["clock"])
    old = v41(env, sinkhorn_impl="pipelined").g.nodes["L3.attn.hc.sinkhorn"]["depth"]
    nits = env["c"]["hc_sinkhorn_iters"]
    assert old == pytest.approx((front + 2 * nits * (4 * D.FADD + 31)) / env["clock"])
    assert n["depth"] < old
    # users queue for the units in rounds when there are fewer units than users in flight
    few = v41(env, kind="wafer", g=57, batch=64, sinkhorn_impl="unit", sinkhorn_units=1)
    rounds = math.ceil(few.mach.microbatch)
    assert few.g.nodes["L3.attn.hc.sinkhorn"]["depth"] == pytest.approx(
        (front + rounds * D.SK["clocks"] * per) / env["clock"])
    # the default takes the faster datapath at the machine's users in flight
    for batch in (64, 4096):
        depth = {m: v41(env, batch=batch, sinkhorn_impl=m).g.nodes["L3.attn.hc.sinkhorn"]["depth"]
                 for m in ("best", "unit", "pipelined")}
        assert depth["best"] == min(depth["unit"], depth["pipelined"])


def test_weight_sweep_is_the_analytical_one(env):
    b = v41(env)
    # the shares partition the analytical sweep; a matvec whose share is below its lane-walk floor
    # (IL x min(IL, K/32) cycles) is charged the floor instead
    shares = [n["sweep"]["share_s"] for n in b.g.nodes.values() if n["sweep"]]
    assert sum(shares) == pytest.approx(b.mach.weight_sweep_s, rel=1e-9)
    assert all(n["issue"] >= n["sweep"]["share_s"] for n in b.g.nodes.values() if n["sweep"])


def test_one_shot_beats_two_step_on_a_small_crossbar(env):
    fab = D.ArrayFabric(env["links"], 4, "mesh", 4)
    one = fab.collective("all_reduce", 20480, 4, "one_shot")
    two = fab.collective("all_reduce", 20480, 4, "two_step")
    assert one["latency_s"] < two["latency_s"]


def test_centre_mesh_is_1p1_diameter(env):
    fab = D.WaferFabric(env["links"], 19, "square", "centre_mesh")
    r = fab.collective("all_reduce", 20480, 19)
    assert r["latency_s"] == pytest.approx(1.1 * D.mesh_diameter(19) * env["links"]["on_wafer_n5"]["hop"])


def test_iso_area_and_port_refusals(env):
    for dp in (2, 4, 8):
        fab = D.ArrayFabric(env["links"], dp, "mesh", 4)
        assert fab.packages * dp in range(188, 188 + dp)
    assert D.ArrayFabric(env["links"], 2, "switch", 4).refused      # 94 packages > radix 64
    assert not D.ArrayFabric(env["links"], 4, "switch", 4).refused


def test_hc1_is_validated_without_a_fit():
    rec = json.loads(RESULT.read_text())
    h = rec["hc1_llama31_8b"]
    assert h["published_tokens_s_per_user"] == 16960
    assert h["residual_us"] == pytest.approx(h["token_period_s"] * 1e6 - 1e6 / 16960)
    # the sweep is the analytical model's own, untouched
    assert h["breakdown_s"]["weight_sweep"] == pytest.approx(
        h["reference_analytical"]["component_times_s"]["weight_read"], rel=1e-9)


def test_committed_result_reproduces():
    rec = json.loads(RESULT.read_text())
    fresh = D.build(D.Params(), quick=True)
    for key in ("hc1_llama31_8b", "qwen3_8b_single_reticle"):
        assert fresh[key]["tokens_s_per_user"] == pytest.approx(rec[key]["tokens_s_per_user"], rel=1e-9)
    for key in ("array_batch1", "wafer_batch1"):
        assert fresh["deepseek_v41_flash"][key]["tokens_s_per_user"] == pytest.approx(
            rec["deepseek_v41_flash"][key]["tokens_s_per_user"], rel=1e-9)
    assert math.isclose(fresh["clock"]["hz"], rec["clock"]["hz"])
