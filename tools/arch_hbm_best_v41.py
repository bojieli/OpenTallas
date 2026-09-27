#!/usr/bin/env python3
"""The BEST HBM comparator for DeepSeek-V4.1-Flash, fully derived at its own tensor group, and the ROM:HBM rate and
energy ratios against it.  Model work only; the budget model (tools/arch_budget_v41.py) is imported, not edited.

    python3 tools/arch_hbm_best_v41.py [--out results/arch/v41_hbm_best.json]

tools/arch_latency_ladder_v41.py found that a wide tensor group is the HBM machine's best lever and priced it by
scaling the G = 4 graph.  This tool replaces that approximation with a full derivation at each group G:

* GRAPH.  decode_critical_path.v41_graph is BUILT for a machine of tensor group G (heads, experts, index keys,
  vocabulary and every split matrix divided G ways; collectives spanning G dies) with the packed placement of the
  checkpoint over the comparator's dies (layer groups of G consecutive dies, stage hops where a layer crosses a
  group boundary).
* COLLECTIVES.  Every all-reduce / all-gather is priced on the realistic fabric at span G
  (decode_critical_path.ArrayFabric: 2-die packages, UCIe inside, a board mesh of G/2 packages at the 130 ns
  light-FEC hop; hierarchical, best algorithm per collective incl. one-shot), bytes overlapped behind producers.
* HBM STREAMING.  Each die streams its 1/G share of every weight from its own 4 HBM3E stacks at 90% (user
  decision: 4 stacks per die); dense weights prefetched across dependency points (read once per pass); routed
  experts at the UNION of the pass's experts (U(n) = 384 (1 - (1 - 6/384)^n) over users x positions) and fetched
  after the router with the 1 us first-access latency exposed; KV rows and index keys once per user per pass.
* MTP.  The verify pass at 6 positions with the m-way core (weights read once, routed union, MACs x 6), plus the
  DSpark draft priced on the same G graph (3 layer-0 spans at 5 rows + 5 Markov steps of the G-split lm_head).
* ENERGY.  Dynamic (the budget model's per-format MAC, HBM byte and link energies at the point's microbatch, plus the
  gated clock of the die's block area over the die-time the token's stages hold it) + static (every die, all the
  time: logic leakage at the analytical density x the die's logic area -- ASSUMED -- plus 4 stacks x 2.8 W,
  technology.json power.memory_interface_idle_w_per_stack) per emitted token.

The engines on each comparator die are the ROM die's pooled spec at the same rung (the comparator's logic area,
~620 mm2, holds them many times over); the generic levers of the rung (chain, depth, clock, sequencing, link) are
applied to both machines; the ROM-only ones (head-die BF16, the index split into a neighbour group) are not.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import arch_latency_ladder_v41 as LX  # noqa: E402

U, A, D = LX.U, LX.A, LX.D
SCHEMA = "opentallas.v41-hbm-best.v1"
OUT = ROOT / "results/arch/v41_hbm_best.json"
CONTEXTS = LX.CONTEXTS
GROUPS = (4, 8, 16, 24, 32, 48)
LANE_MULTS = (2, 6)
POINTS = (("b1", 1), ("fill28", 28), ("sat1024", 1024))
TAU, GAMMA = U.TAU, U.GAMMA
# communication levers valid at any group; direct_to_next_stage / flat_one_shot assume a group that is one package
# pair (a package pre-reduce and one board flight), so they apply only at G = 4
COMM_ANY = ("replicate_a_proj", "cut_through_hops", "ring_placement_return", "oneshot_128_lanes")
COMM_G4 = ("direct_to_next_stage", "flat_one_shot")
ROM_ONLY = (LX.m_wide_head, LX.m_idx_split)


FABRIC = None      # a callable (G, dies) -> fabric; None = the board mesh (decode_critical_path.ArrayFabric)


def fabric_for(G, dies):
    if FABRIC:
        return FABRIC(G, dies)
    return D.ArrayFabric(A.links_for(A.BASELINE), 2, "mesh", G, dies=dies)


def machine(G, batch, dies):
    E = A._env()
    m1 = D.v41_machine("array", G, 1, E["points"], E["designs"], E["p"], E["clock"], units=dies, placement="packed")
    S = m1.stages
    return replace(m1, batch=batch, microbatch=max(1.0, batch / S), slots=float(min(batch, S)))


def price_g(spec, ctx, G, hbm, batch=1, positions=1, levers=(), muts=(), keep=False):
    """The budget model's price() for the HBM comparator, re-derived at tensor group G (see the module doc)."""
    E = A._env()
    clock, c = E["clock"], E["c"]
    m = machine(G, batch, hbm["dies"])
    users = m.microbatch
    if positions > 1:
        m = replace(m, microbatch=users * positions)
    levers = set(levers)
    b = D.Built(m, E["p"], clock, D.v41_graph, c, ctx)
    fab = fabric_for(G, hbm["dies"])
    D.price_communication(b.g, fab, m.microbatch, clock)
    for nd in b.g.nodes.values():
        if nd["kind"] == "collective":
            nd["stream"] = True                                   # overlapped reductions (the baseline)
    mb = m.microbatch
    NE, KE, FF, D_ = c["num_routed_experts"], c["experts_per_token"], c["moe_intermediate_size"], c["hidden_size"]
    lm = max(1, spec.lane_mult)
    tokens = max(1, round(mb))
    Uexp = A.distinct_experts(tokens, NE, KE)
    cyc = 1.0 / clock
    sd = A.SFU_DEPTH[spec.sfu]
    bw = hbm["bw_Bps"]
    hbm_bytes = 0.0
    for name, nd in b.g.nodes.items():
        k = nd["kind"]
        if k == "matvec":
            sw = nd["sweep"]
            f = A.die_fraction(name, c, G)
            hc = name.endswith("hc.fn")
            if hc:
                nd["depth"] = max(nd["depth"], A.HC_DEPTH_CYC * cyc)
            wide = name.endswith(("wo_a", "cmp.wk", "router", "lm_head"))
            lanes = spec.hc_macs if hc else (spec.bf16_macs if wide else spec.weight_macs)
            macs = sw["macs"] * f
            full_b = sw["bytes"] * f * A._precision_fix(name, c, nd)
            routed_b = full_b if name.endswith("ffn.experts_gu") else (
                KE * D_ * FF * A.FP4 * f if name.endswith("ffn.down") else 0.0)
            by = (full_b - routed_b) + routed_b * Uexp / KE
            if hc:
                by = 0.0                                          # replicated FP32 mixes held on-die (1.97 MB)
            hbm_bytes += by
            t_mem = by / (bw / clock)
            if name.endswith("ffn.experts_gu"):
                nd["depth"] += hbm["lat_s"]
            t_m = macs / (lanes * lm)
            t = max(t_mem, t_m)
            issue = t * cyc
            nd["_work"] = ("hc", macs) if hc else ("bf16" if wide else "weight", macs / lm)
        elif k == "kvscan":
            if name.endswith("idx.score"):
                n_keys = int(nd["desc"].split()[2]) if nd["desc"].startswith("index scores") else 0
                by = n_keys * A.IDX_KEY_B * users
                macs = n_keys * c["index_heads"] * c["index_head_dim"] * mb
                t = max(by / min(spec.idx_bytes, bw / clock), macs / (spec.idx_macs * lm))
                nd["_work"] = ("idx", macs / lm)
            else:
                L = nd["layer"]
                r = c["compress_ratios"][L]
                n_sel = min(c["index_topk"], ctx // r) if r else 0
                R = min(c["window_tokens"], ctx) + n_sel
                hpd = math.ceil(c["num_attention_heads"] / G)
                macs = hpd * R * c["head_dim"] * mb
                by = (min(c["window_tokens"], ctx) * A.WIN_ROW_B + n_sel * A.CKV_ROW_B) * users \
                    if name.endswith("scores") else 0
                t = max(by / min(spec.kv_bytes, bw / clock), macs / (spec.att_macs * lm))
                nd["_work"] = ("att", macs / lm)
            hbm_bytes += by / G if not name.endswith("idx.score") else by
            issue = t * cyc
        elif k in ("vector", "reduce"):
            n_el = round(nd["issue"] * clock * m.su_width / max(1e-9, mb))
            fn = A.SFU_NODE.get(name.split(".")[-1])
            lanes = (spec.sfu_lanes if fn else spec.su_lanes) * lm
            issue = math.ceil(n_el * mb / lanes) * cyc
            nd["_work"] = ("sfu" if fn else "su", n_el * mb / lm)
            if spec.sfu != "as_built" and fn in ("exp", "sigmoid", "silu"):
                key = "sigmoid" if fn in ("sigmoid", "silu") else "exp"
                nd["depth"] = max(0.0, nd["depth"] - (A.SFU_DEPTH["as_built"][key] - sd[key]) * cyc)
        elif k == "op" and name.endswith(".gather"):
            nd["depth"] = spec.kv_gather_s
            continue
        elif k == "select":
            issue, depth, _r, rwork = A._select_price(name, nd, spec, c, ctx, mb / lm, clock, ways=G)
            nd["depth"] = depth
            nd["_work"] = ("sel", rwork * spec.sel_lanes)
        else:
            continue
        ch = A.node_chain(name, nd, c, ctx, spec)
        if ch:
            issue = max(issue, ch * spec.add_lat * cyc)
        nd["issue"] = issue
        if k == "matvec":
            nd["issue_cat"] = "weight_sweep"
    if spec.seq_gap != 5:
        for nd in b.g.nodes.values():
            if nd["ctrl"] > 0:
                nd["ctrl"] += (spec.seq_gap - 5) * cyc
    if "osm" in levers:
        for name, nd in b.g.nodes.items():
            if name.endswith("attn.exp"):
                nd["deps"] = [name[:-len("exp")] + "scores"]
                nd["stream"] = True
    if "chain_all" in levers:
        for name, nd in b.g.nodes.items():
            if nd["kind"] in ("matvec", "kvscan") or (nd["kind"] == "select" and name.endswith("topk_local")):
                nd["stream"] = True
    if "short_stages" in levers:
        for name, nd in b.g.nodes.items():
            if nd["kind"] in ("vector", "reduce"):
                cut = 8 + (7 if nd["kind"] == "reduce" else 0)
                if name.endswith(".rsqrt"):
                    cut += 24
                if name.endswith("softplus_sqrt"):
                    cut += 98
                nd["depth"] = max(0.0, nd["depth"] - cut * cyc)
    b.g.mb = m.microbatch
    for f_ in muts:
        f_(b.g, spec)
    fin = b.g.solve(spec.chaining)
    T = fin[b.sink]
    cats = dict.fromkeys(D.CATS, 0.0)
    for n in b.g.path(b.sink):
        for k_, v in b.g.contrib[n].items():
            cats[k_] += v
    occ = sum(nd["issue"] for nd in b.g.nodes.values() if nd["kind"] not in ("collective", "hop"))
    ob = occ * min(m.slots, batch) / max(1, m.stages)
    period = max(T, ob)
    out = dict(T_s=T, period_s=period, occupancy_bound_s=ob, binding="critical_path" if T >= ob else "occupancy",
               stages=m.stages, microbatch=users, slots=m.slots, distinct_experts=Uexp,
               hbm_bytes_per_die_per_pass=hbm_bytes, breakdown_us={k: v * 1e6 for k, v in cats.items()},
               collectives_on_path=sum(1 for n in b.g.path(b.sink) if b.g.nodes[n]["kind"] == "collective"))
    if keep:
        out["_built"] = b
    return out


def draft_g(spec, ctx, G, hbm, gamma, levers, muts):
    """DSpark draft on the G graph: 3 layer-0 spans at gamma rows + gamma Markov steps (the G-split lm_head row,
    the rank-256 bias, argmax, one group collective at span G)."""
    E = A._env()
    c, clock = E["c"], E["clock"]
    r = price_g(spec, ctx, G, hbm, positions=gamma, levers=levers, muts=muts, keep=True)
    g = r["_built"].g
    l0 = [n for n in g.nodes if g.nodes[n]["layer"] == 0]
    stage = max(g.fin[n] for n in l0) - min(g.fin[n] - g.nodes[n]["issue"] - g.nodes[n]["depth"] for n in l0)
    V, lanes = c["vocab_size"], max(1.0, spec.weight_macs * spec.lane_mult)
    lm = max(V * c["hidden_size"] / G / lanes / clock, V * c["hidden_size"] * 2 / G / hbm["bw_Bps"])
    markov = 2 * V * 256 / G / lanes / clock
    argmax = V / G / max(1, spec.su_lanes) / clock
    coll = fabric_for(G, hbm["dies"]).collective("all_gather", 8 * G, G)
    step = lm + markov + argmax + coll["latency_s"] + 60 / clock
    return 3 * stage + gamma * step


def evaluate_g(spec, ctx, G, hbm, batch, mtp, m, levers, muts, hz, tau=TAU):
    hz_, prm = hz if isinstance(hz, tuple) else (hz, {})
    with LX.clock(hz_), U.params(**prm):
        if not mtp:
            r = price_g(spec, ctx, G, hbm, batch=batch, levers=levers, muts=muts)
            return dict(r, tokens_s_per_user=1 / r["period_s"], aggregate_tokens_s=batch / r["period_s"],
                        draft_s=0.0, cycle_s=r["period_s"])
        sm = replace(spec, lane_mult=m)
        v = price_g(sm, ctx, G, hbm, batch=batch, positions=GAMMA + 1, levers=levers, muts=muts)
        d = draft_g(sm, ctx, G, hbm, GAMMA, levers, muts)
        cyc = v["period_s"] + d
        return dict(v, tokens_s_per_user=tau / cyc, aggregate_tokens_s=tau / cyc * batch, draft_s=d, cycle_s=cyc)


def rung_muts(G, rung_muts_all):
    comm_ok = {id(f) for n in COMM_ANY for f in LX.L[n][0]}
    comm_g4 = {id(f) for n in COMM_G4 for f in LX.L[n][0]}
    out = []
    for f in rung_muts_all:
        if f in ROM_ONLY:
            continue
        if id(f) in comm_g4 and G != 4:
            continue
        out.append(f)
    return out


# -- energy ----------------------------------------------------------------------------------------------------------------
def energy_point(sp, ctx, point, dies, stages, area_mm2, static_w, hbm=None, m=2):
    """J per emitted token: dynamic non-clock (budget model) + gated clock of the dies holding the token + static."""
    E = A._env()
    et = A.energy_terms(E["tech"])
    b, mtp = point["batch"], point["mtp"]
    pos = GAMMA + 1 if mtp else 1
    tau = TAU if mtp else 1.0
    s = replace(sp, lane_mult=m) if mtp else sp
    agg = point["aggregate_tokens_s"]
    e = A.energy_per_token(s, ctx, point["microbatch"], pos, hbm=hbm, rate_tokens_s=agg)
    nonclock = e["total_j"] - e["parts_j"]["clock"]
    if mtp:
        nonclock = nonclock * pos / tau * (1 + 3 / 40)
    period = point["cycle_s"]
    clocked_die_s = dies * period * min(b, stages) / stages / b / tau
    clk = et["clock"] * area_mm2 * E["clock"] * clocked_die_s
    st = static_w / agg
    return dict(dynamic_j=nonclock + clk, static_j=st, total_j=nonclock + clk + st, nonclock_j=nonclock, clock_j=clk)


def build():
    E = A._env()
    c = E["c"]
    areas = A.unit_areas()[0]
    hb = U.hbm_comparator(c)
    hbm = dict(bw_Bps=hb["bw_Bps"], lat_s=hb["lat_s"], dies=hb["dies"])
    stat = E["designs"][D.ARRAY_DESIGN]["static_power"]["detail"]
    stack_w = E["tech"]["power"]["memory_interface_idle_w_per_stack"]["value"]
    ST = U.static_terms(hb)
    dens = ST["logic_density"]
    hbm_die_static = ST["hbm_die_no_serdes"] + ST["serdes"]   # board-mesh comparator: the same 84-lane package
    rom_die_static = ST["layer_die"]
    rs = json.loads((ROOT / "results/arch/v41_utilization.json").read_text())["nonlayer_right_size"]
    rom_nl_static = rom_die_static - rs["static_w_saved"] / U.NONLAYER_DIES
    base = U.unified(U.req_spec())
    # the top rung carries only the ladder's ADOPTED levers (as recorded)
    adopted = {r["key"] for r in json.loads((ROOT / "results/arch/v41_latency_ladder.json").read_text())["ladder"]
               if r["adopted"]}
    LX.LADDER[:] = [(k, lab, kind if k in adopted else "none", pay, f) for k, lab, kind, pay, f in LX.LADDER]
    rec = dict(schema=SCHEMA, tool="tools/arch_hbm_best_v41.py", tau=TAU, gamma=GAMMA,
               comparator=dict(dies=hb["dies"], stacks_per_die=hb["hbm_stacks_per_die"], bw_Bps_per_die=hb["bw_Bps"],
                               logic_mm2_per_die=hb["logic_mm2_per_die"], first_access_s=hb["lat_s"],
                               static_w_per_die=hbm_die_static, logic_leak_w_per_mm2=dens),
               rom_static_w=dict(layer_die=rom_die_static, nonlayer_die_right_sized=rom_nl_static),
               method=__doc__.split("This tool replaces")[1].split("\n\nThe engines")[0].strip())
    rungs = {}
    for tag, upto in (("start", 0), ("top", len(LX.LADDER))):
        sp, muts_all, hz = LX.rung_spec(base, upto)
        rung = dict(rom={}, hbm={}, grid={}, energy={})
        for ctx in CONTEXTS:
            # the HBM comparator's grid at batch 1
            grid = []
            for G in GROUPS:
                mu = rung_muts(G, muts_all)
                ar = evaluate_g(sp, ctx, G, hbm, 1, False, 1, U.CHAIN_L3, mu, hz)
                row = dict(G=G, stages=ar["stages"], ar=ar["tokens_s_per_user"], T_us=ar["T_s"] * 1e6,
                           breakdown_us={k: round(v, 2) for k, v in ar["breakdown_us"].items()},
                           collectives_on_path=ar["collectives_on_path"])
                for m in LANE_MULTS:
                    v = evaluate_g(sp, ctx, G, hbm, 1, True, m, U.CHAIN_L3, mu, hz)
                    row[f"mtp_m{m}"] = v["tokens_s_per_user"]
                    row[f"verify_us_m{m}"] = v["period_s"] * 1e6
                    row[f"draft_us_m{m}"] = v["draft_s"] * 1e6
                    row[f"distinct_experts_m{m}"] = v["distinct_experts"]
                grid.append(row)
            best_ar = max(grid, key=lambda r: r["ar"])
            best_mtp = max(((r, m) for r in grid for m in LANE_MULTS), key=lambda x: x[0][f"mtp_m{x[1]}"])
            Gb, mb_ = best_mtp[0]["G"], best_mtp[1]
            rung["grid"][str(ctx)] = grid
            rung["hbm"][str(ctx)] = dict(ar=best_ar["ar"], ar_G=best_ar["G"], mtp=best_mtp[0][f"mtp_m{mb_}"],
                                         mtp_G=Gb, mtp_m=mb_)
            # ROM at the same rung (ladder evaluator) and the energy at every operating point, both machines
            rom = LX.evaluate(sp, ctx, muts_all, hz=hz)
            rung["rom"][str(ctx)] = dict(ar=rom["ar"], mtp=rom["mtp"])
            en = {}
            Ge = best_ar["G"]
            for ptag, bt in POINTS:
                for mtp in (False, True):
                    Gx, mx = (Gb, mb_) if mtp else (Ge, 1)
                    h = evaluate_g(sp, ctx, Gx, hbm, bt, mtp, mx, U.CHAIN_L3, rung_muts(Gx, muts_all), hz)
                    h.update(batch=bt, mtp=mtp)
                    with LX.clock(hz[0]), U.params(**hz[1]):
                        r_ = U.op_point(sp, ctx, bt, mtp=mtp, levers=U.CHAIN_L3, muts=muts_all, units=U.POOLED_UNITS)
                    r_["cycle_s"] = r_["period_us"] * 1e-6
                    a_rom = LX.area(sp, U.MTP_M if mtp else 1)
                    a_hbm = LX.area(sp, mx if mtp else 1)
                    e_rom = energy_point(sp, ctx, r_, U.LAYER_DIES, 28, a_rom,
                                         rom_die_static * U.LAYER_DIES + rom_nl_static * U.NONLAYER_DIES)
                    e_hbm = energy_point(sp, ctx, h, hb["dies"], h["stages"], a_hbm, hbm_die_static * hb["dies"],
                                         hbm=hbm, m=mx)
                    key = ptag + ("_mtp" if mtp else "")
                    en[key] = dict(
                        rom=dict(tokens_s_per_user=r_["tokens_s_per_user"], aggregate_tokens_s=r_["aggregate_tokens_s"],
                                 **{k: v for k, v in e_rom.items()}),
                        hbm=dict(G=Gx, m=mx if mtp else None, stages=h["stages"], binding=h["binding"],
                                 tokens_s_per_user=h["tokens_s_per_user"], aggregate_tokens_s=h["aggregate_tokens_s"],
                                 **{k: v for k, v in e_hbm.items()}),
                        ratio_rate_per_user=r_["tokens_s_per_user"] / h["tokens_s_per_user"],
                        ratio_aggregate=r_["aggregate_tokens_s"] / h["aggregate_tokens_s"],
                        ratio_energy_with_static=e_hbm["total_j"] / e_rom["total_j"],
                        ratio_energy_dynamic=e_hbm["dynamic_j"] / e_rom["dynamic_j"])
            rung["energy"][str(ctx)] = en
        rungs[tag] = rung
    rec["rungs"] = rungs
    rec["scaled_approximation_was"] = {
        str(ctx): dict(start=json.loads((ROOT / "results/arch/v41_latency_ladder.json").read_text())["ladder"][0][str(ctx)]["hbm"],
                       top=json.loads((ROOT / "results/arch/v41_latency_ladder.json").read_text())["ladder"][-1][str(ctx)]["hbm"])
        for ctx in CONTEXTS}
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rec = build()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1, default=lambda o: None) + "\n")
    for tag, r in rec["rungs"].items():
        for ctx in map(str, CONTEXTS):
            h, ro = r["hbm"][ctx], r["rom"][ctx]
            print(tag, ctx, "ROM", round(ro["ar"]), round(ro["mtp"]), "HBM", round(h["ar"]), f"G{h['ar_G']}",
                  round(h["mtp"]), f"G{h['mtp_G']} m{h['mtp_m']}", f"x{ro['ar'] / h['ar']:.2f} x{ro['mtp'] / h['mtp']:.2f}")
            for g in r["grid"][ctx]:
                print("   G", g["G"], "S", g["stages"], round(g["ar"]), round(g["mtp_m2"]), round(g["mtp_m6"]),
                      g["collectives_on_path"], g["breakdown_us"])
            for k, v in r["energy"][ctx].items():
                print("   E", k, f"rom {v['rom']['total_j'] * 1e3:.1f} mJ hbm {v['hbm']['total_j'] * 1e3:.1f} mJ "
                      f"x{v['ratio_energy_with_static']:.2f} (dyn x{v['ratio_energy_dynamic']:.1f}) "
                      f"rate x{v['ratio_rate_per_user']:.2f} agg x{v['ratio_aggregate']:.2f}")


if __name__ == "__main__":
    main()
