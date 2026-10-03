#!/usr/bin/env python3
"""Opt-in parallelism-mapping term for the unified model's V4.1 ROM array (DS4096 S58 basis).

For a weight-stationary ROM, a parallel mapping is (a) where each weight byte physically lives and (b) which
activations move.  This extension re-prices the S58 TP-4 graph of tools/uarch_model.py (`cons_v41_rom`) for one
mapping at a time, on PHYSICAL dies (the NP2048 die of DS4096-TP4-S58-PAR2-NP2048: half of the model's TP-4 rank
die, so 8 physical dies per stage).  Importing this module mutates nothing; `cons_v41_rom_mapping(..., mapping=None)`
is exactly the baseline call, and an explicit mapping wraps `_cons_adjust` only for the duration of the call.

Mapping knobs (all optional; see MAPPINGS in tools/dsrom_parallelism.py):
  field     {node key: policy}.  "tp"         keep the model's balanced per-element share (TP-8 over 8 physical dies on
                                              half the macros = the rank model's words per element; t_ret not credited)
                                 "replicate"/"tp1"  whole matrix on every / one physical die (price_matvec at die share
                                              1 on the physical die's macros)
                                 "ep"         whole routed experts, E[max experts per die] on the busiest die
                                 "kalign"     Megatron row-parallel down / column gu with golden-chunk-aligned shares
                                              (exact only on 256-element chunk boundaries: busiest share 2/9 at TP-8)
                                 float        scale t_read / t_ret by that factor
  coll      {collective suffix: action}.  ("remove",) | ("replace", [(op, payload_B_per_position, span), ...])
                                 | ("board_gather", payload_B, extra_s)  (EP combine into one hub die)
                                 | ("a2a", kmax_key)  (symmetric EP combine: fabric combine_a2a)
  dispatch_s  extra one-way crossing added to experts_gu (EP with a non-replicated x).
  issue_scale {node suffix: factor} on non-field nodes (hub doing 4x the heads, etc.).
  cp        dict(W=, stacks=, layers=None) index-key context parallel: idx.score x 16/(W*stacks), local top-k x 4/W,
            the final select at W ways, merges re-priced at span W.  chase=True streams the local top-k.
  head_ways vocabulary split of lm_head (8 head dies exist; the model splits 4 ways).
Collective pricing: a re-priced collective keeps its graph-calibrated fixed part (graph depth minus the base fabric
cost: the W15-measured collective, SS stages and VM write), and pays the new fabric's latency + bytes in full (no
overlap credit, conservative after the C7 RTL finding, results/arch/v41_collective_exposure.json).
"""
import contextlib
import copy
import math
import statistics

import uarch_model as baseline

MODEL_EXTENSION = "parallelism-mapping"
A = baseline.A
D = A.D
VM_TO_SERDES_STAGES = 45          # uarch_model DIE_SHRUNK_INTERIM coll_stages (W18b): VM/collective -> SerDes
VM_TO_UCIE_STAGES = 34            # W18b: VM -> UCIe PHY (tools/uarch_model_par2_boundary.py)
ID_ORDER_SUM_S = 7 * 3 / 0.9e9 + 80 / 1.2e9   # 7 dependent FP32 adds (LAT-3, 0.9 GHz serial domain) + 5120/64-lane
                                              # stream at 1.2 GHz: the golden's id-order expert sum on the hub
WHOLE_EXPERT_ROWS = {"experts_gu": 2 * 2304, "down": 5120}   # one expert's w1|w3 rows, w2 rows (V4.1-Flash)
KE, NE = 6, 384


def links():
    return A.links_for(A.BASELINE)


def base_fabric():
    return D.ArrayFabric(links(), 2, "mesh", 4)       # arch_budget_v41's fabric for the priced graph


def fabric(group, board="fc4"):
    f = D.ArrayFabric(links(), 2, board, group)
    if f.refused:
        raise ValueError(f.refused)
    return f


def board_one_way_s(clock):
    """VM -> SerDes on both dies + the light-FEC board link (130 ns): uarch_model_par2_boundary owner_board."""
    return 2 * VM_TO_SERDES_STAGES / clock + A.BASELINE["board_hop_s"]


def ucie_one_way_s(clock):
    return 2 * VM_TO_UCIE_STAGES / clock + links()["rom_package_ucie"]["hop"] - 1.5e-9   # 65.2 ns at 1.2 GHz


def kmax(active, bins):
    return baseline.expected_max_load(int(round(active)), bins)


def _fcost(f, op, payload, span):
    r = f.collective(op, payload, span)
    return r["latency_s"] + r["bytes_s"]


def _phys(d):
    p = copy.deepcopy(d)
    p["macros"] = d["macros"] // 2
    if p.get("bf16_stripe_macros"):
        p["bf16_stripe_macros"] = d["bf16_stripe_macros"] // 2
    return p


@contextlib.contextmanager
def _patched(frac=None, expert_rows=None):
    old_f, old_r = A.die_fraction, dict(baseline.EXPERT_ROWS)
    if frac is not None:
        A.die_fraction = lambda name, c, G: frac
    if expert_rows:
        baseline.EXPERT_ROWS.update(expert_rows)
    try:
        yield
    finally:
        A.die_fraction = old_f
        baseline.EXPERT_ROWS.clear()
        baseline.EXPERT_ROWS.update(old_r)


def _reprice(nd, name, d, clock, frac, expert_rows=None):
    c = A._env()["c"]
    with _patched(frac, expert_rows):
        return baseline.price_matvec(nd, name, d, clock, c)


def _set_u(nd, new, clock):
    old = nd["_uarch"]
    nd["depth"] += (new["depth"] - old["depth"]) / clock
    nd["_uarch"] = new


def pre(g, P, clock, d, cfg, led):
    """Field / non-field re-pricing BEFORE _cons_adjust re-times the graph (it rebuilds issue from _uarch)."""
    dp = _phys(d)
    fpol = cfg.get("field", {})
    for name, nd in g.nodes.items():
        u = nd.get("_uarch")
        if u and nd["layer"] is not None and nd["layer"] >= 0 and u["key"] in fpol:
            pol = fpol[u["key"]]
            if pol == "tp":
                G = cfg.get("tp_group", 4)
                if G != 4:     # per-element words on the physical die (half the rank's macros) at a G-way share
                    c = A._env()["c"]
                    f = 2 * A.die_fraction(name, c, G) / A.die_fraction(name, c, 4)
                    if abs(f - 1) > 1e-9:
                        nd["_uarch"] = dict(u, t_read=u["t_read"] * f)
                        led["field"] += 1
                continue
            if pol in ("replicate", "tp1"):
                _set_u(nd, _reprice(nd, name, dp, clock, 1.0), clock)
            elif pol == "ep":
                one = _reprice(nd, name, dp, clock, 1.0 / KE, WHOLE_EXPERT_ROWS)    # one whole expert, physical die
                act = KE if P == 1 else A.distinct_experts(P, NE, KE)
                k = kmax(act, cfg["ep_dies"]) / P                                  # x P by _cons_adjust
                new = dict(one, t_read=one["t_read"] * k, t_ret=one["t_ret"] * k, t_mac=one["t_mac"] * k,
                           ep_kmax=k * P)
                _set_u(nd, new, clock)
            elif pol == "kalign":
                f = cfg["kalign_factor"]
                nd["_uarch"] = dict(u, t_read=u["t_read"] * f, t_ret=u["t_ret"] * f)
            else:
                nd["_uarch"] = dict(u, t_read=u["t_read"] * pol, t_ret=u["t_ret"] * pol)
            led["field"] += 1
    if cfg.get("head_ways"):
        f = 4 / cfg["head_ways"]
        for name, nd in g.nodes.items():
            if name == "head.lm_head":
                u = nd["_uarch"]
                nd["_uarch"] = dict(u, t_read=u["t_read"] * f, t_ret=u["t_ret"] * f)
    cp = cfg.get("cp")
    for name, nd in g.nodes.items():
        if cfg.get("chase") and name.endswith((".idx.topk_local", ".cand.topk_local")):
            nd["stream"] = True
        for suf, f in cfg.get("issue_scale", {}).items():
            if name.endswith(suf) and not nd.get("_uarch"):
                nd["issue"] *= f
        if cp and (cp.get("layers") is None or nd.get("layer") in cp["layers"]):
            W, s = cp["W"], cp["stacks"]
            if name.endswith(".idx.score"):
                nd["issue"] *= 16 / (W * s)
            elif name.endswith((".idx.topk_local", ".cand.topk_local")):
                nd["issue"] *= 4 / W
            elif name.endswith(".idx.topk_final"):
                nd["depth"] = (math.ceil(W * 512 / 64) + D.tselect_latency(W * 512)) / clock if W > 1 else 0.0
            elif name.endswith(".cand.final"):
                nd["depth"] = (math.ceil(W * 2048 / 64) + D.tselect_latency(W * 2048)) / clock if W > 1 else 0.0
        if name == "head.argmax" and cfg.get("head_ways"):
            nd["issue"] *= 4 / cfg["head_ways"]


def post(g, P, clock, cfg, led):
    """Collective / crossing re-pricing AFTER _cons_adjust (whose SS / VM terms are in the calibrated fixed part)."""
    fb = base_fabric()
    fn = cfg.get("_fabric") or fabric(cfg.get("group", 8), cfg.get("board", "fc4"))
    colls = {n: nd for n, nd in g.nodes.items() if nd["kind"] == "collective"}
    fixed = {}
    for n, nd in colls.items():
        fixed.setdefault(nd["op"], []).append(nd["depth"] - _fcost(fb, nd["op"], nd["payload"] * P, nd["span"]))
    ovh = {op: statistics.median(v) for op, v in fixed.items()}
    led["fixed_part_ns"] = {k: round(v * 1e9, 1) for k, v in ovh.items()}
    acts = cfg.get("coll", {})
    for n, nd in colls.items():
        act = next((a for suf, a in acts.items() if n.endswith(suf)), None)
        if act is None:
            continue
        own_fixed = nd["depth"] - _fcost(fb, nd["op"], nd["payload"] * P, nd["span"])
        kind = act[0]
        if kind == "remove":
            new = 0.0
        elif kind == "replace":
            new = 0.0
            for i, (op, pay, span) in enumerate(act[1]):
                fx = own_fixed if (i == 0 and op == nd["op"]) else ovh.get(op, ovh["all_gather"])
                new += fx + _fcost(fn, op, pay * P, span)
        elif kind == "respan":                  # same op and payload (x scale), new span on the new fabric
            new = own_fixed + _fcost(fn, nd["op"], nd["payload"] * act[1] * P, act[2])
        elif kind == "board_gather":            # expert outputs -> one hub die over the board
            pay, extra = act[1], act[2]
            k = cfg["_kmax_P"](P)
            byt = max(KE * pay * P / fn.pkg_bw, k * pay / fn.link_bw)
            new = board_one_way_s(clock) + byt + extra
        elif kind == "a2a":                     # symmetric EP: every die needs every selected expert's output
            k = cfg["_kmax_P"](P)              # busiest die's (expert, position) outputs: union-based, not x P
            p_ = fn.g
            r = fn.combine_a2a(act[1], 1, k, p_)
            bnode = fn._board(math.ceil(p_ / fn.dp)).B_node      # decode_critical_path ArrayFabric.combine_a2a
            byt = max(KE * P * act[1] * (p_ - 1) / p_, k * act[1] * (p_ - 1)) / bnode
            new = ovh["all_gather"] + r["latency_s"] + byt + act[2]
        else:
            raise ValueError(kind)
        nd["_map_s"] = new - nd["depth"]
        nd["depth"] = new
        nd["issue"] = 0.0
        led["collectives"] += 1
    if cfg.get("dispatch_s"):
        for n, nd in g.nodes.items():
            if n.endswith(".ffn.experts_gu"):
                add = cfg["dispatch_s"](P)
                nd["depth"] += add
                nd["_map_s"] = nd.get("_map_s", 0.0) + add
                led["dispatch"] += 1


def path_breakdown(g):
    """Critical-path seconds by class (the solved path's per-node contributions)."""
    sink = [n for n in g.nodes if n.endswith("token.return")][0]
    out = dict(field=0.0, serial_chain=0.0, kv_scan=0.0, tp_collectives=0.0, ep_combine_dispatch=0.0,
               cp_merge=0.0, stage_hops=0.0, other=0.0, par2_crossings=0.0)
    for n in g.path(sink):
        nd = g.nodes[n]
        c = sum(g.contrib[n].values())
        p2 = nd.get("_par2_s", 0.0) if nd.get("_uarch") else 0.0
        ms = nd.get("_map_s", 0.0) if nd.get("_uarch") else 0.0
        out["par2_crossings"] += min(c, p2)
        out["ep_combine_dispatch"] += min(c - p2, ms) if ms > 0 else 0.0
        c -= min(c, p2) + (min(c - p2, ms) if ms > 0 else 0.0)
        k = nd["kind"]
        if nd.get("_uarch"):
            out["field"] += c
        elif k == "collective":
            if n.endswith(("topk_merge", "cand.merge")):
                out["cp_merge"] += c
            elif n.endswith("combine_allreduce") and nd.get("_ep"):
                out["ep_combine_dispatch"] += c
            else:
                out["tp_collectives"] += c
        elif k == "hop":
            out["stage_hops"] += c
        elif k == "kvscan":
            out["kv_scan"] += c
        elif k in ("vector", "reduce", "select", "sinkhorn", "op", "matvec"):
            out["serial_chain"] += c
        else:
            out["other"] += c
    return {k: round(v * 1e6, 3) for k, v in out.items()}


@contextlib.contextmanager
def wrapped(cfg, ledgers):
    """Wrap whatever _cons_adjust is installed (so a PAR2 wrapper may sit inside)."""
    orig = baseline._cons_adjust

    def adj(g, P, clock, *a, **k):
        d = k.get("d") if "d" in k else a[7]
        led = dict(P=P, field=0, collectives=0, dispatch=0)
        pre(g, P, clock, d, cfg, led)
        orig(g, P, clock, *a, **k)
        post(g, P, clock, cfg, led)
        for n, nd in g.nodes.items():
            if cfg.get("ep_combine") and n.endswith(".ffn.combine_allreduce"):
                nd["_ep"] = True
        fin = g.solve(True)
        sink = [n for n in g.nodes if n.endswith("token.return")][0]
        led["path_us"] = path_breakdown(g)
        led["T_us"] = round(fin[sink] * 1e6, 3)
        led["_g"] = g
        ledgers.append(led)
        return fin[sink]
    baseline._cons_adjust = adj
    try:
        yield
    finally:
        baseline._cons_adjust = orig


def cons_v41_rom_mapping(S, *args, mapping=None, ledgers=None, **kw):
    """cons_v41_rom with an opt-in mapping.  mapping=None is the unchanged baseline call."""
    if mapping is None:
        return baseline.cons_v41_rom(S, *args, **kw)
    led = [] if ledgers is None else ledgers
    with wrapped(mapping, led):
        return baseline.cons_v41_rom(S, *args, **kw)
