#!/usr/bin/env python3
"""DS-ROM recovery, SU chains: per-chain latency anatomy of the serial vector-unit (SU) chains on the measured AR token
at position 1,048,575 (1M context), from the committed full-shape RTL runs (no new simulation).

Inputs (all committed):
  results/rtl/dsrom_1m_allmeasured_20261004/su_runs/su_N1024_M256_b22r15m5a4_dpi_beh{,_su_cases_rw}.json
      the WIRED runs (ot_hdc_v41x_vec N 1,024 / M 256, MLAT 5 / ALAT 4, BCAST 22 / RET 15 hub stages on every op,
      0.9 GHz serial domain) whose node increments the composition uses (tools/dsrom_1m_allmeasured_adapters.su_rows)
  results/rtl/dsrom_1m_allmeasured_20261004/su_qdq_wired.json   quantisers (ot_hdc_actquant, one instance, + 37 stages)
  results/rtl/dsrom_recovery_20261004/composition.json          the recovery AR token's critical path (per node us,
                                                                 measured CDC per node in patches)
  the SU case set (su_cases.pkl, 20 MB, not committed; its sha256 is the su run's cases_sha256) for the op fields
      (which FP units each op uses); --cases PATH

Method.  Each chain's timeline (first_emit / last_emit / last_write / last_result of every op, wired run) is cut
along its critical sequence: op k's window runs from the completion of the latest earlier op that completes before
op k's last write (its anchor) to op k's own completion.  The window splits into
  setup          controller accept + set-up before the chain's first emit
  issue_barrier  anchor -> first emit of a dependent op (credit / result-port waits, the checkpoint ordering rule)
  stream         vectors after the first (lane width; the scalar side pipe; one quantiser instance: a beat a block)
  depth          the op's emit -> last write pipeline, itself split into
                   wire          BCAST 22 + RET 15 hub stages (the part not hidden under the anchor)
                   vm_round_trip broadcast register + fetch 3 + PRE 1 + OUT 1: the write -> VM -> re-read of
                                 every dependent op
                   arith         FP units the op USES (M1 / M2 / AD / S / E1 / E2 at MLAT 5 / ALAT 4; divide 19)
                   passthrough   fixed lane stages the op passes but does not use (every lane stage is fixed depth)
  reduction      the reducer after the last write: IN/OUT 2, square MLAT, 7-add chunk chain, log2 tree, time levels
and per node, measured CDC (su_cdc.json values as patched into the composition) and serial select (top-6).
Node windows are the composition's node increments (completion of the node minus completion of the previous node
of its chain), so every node's categories sum to its su.json wired cycles (checked).

The FLOOR of each chain (documented, the iteration target): the same exact arithmetic (golden rounding and reduction
order unchanged) in one fused 1.2 GHz pipeline: only the FP units on the dependency chain (f12 units: mul 5, add 4;
the SFU function depths at LM 5 / LA 4), the chunk-8 chain + tree levels the R-ARITH order needs, the stream at the
fused unit's width, ONE hub traverse in and ONE out at 1.2 GHz, no CDC, no issue barrier, no VM round trip.

    python3 tools/dsrom_su_anatomy.py --cases /path/su_cases.pkl --cases-rw /path/su_cases_rw.pkl \
        --out results/rtl/dsrom_recovery_20261004/su_chains/anatomy.json
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pickle
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_1m_allmeasured_adapters as AD  # noqa: E402

REC = ROOT / "results/rtl/dsrom_1m_allmeasured_20261004"
RUNS = REC / "su_runs"
COMP = ROOT / "results/rtl/dsrom_recovery_20261004/composition.json"
WIRED = "su_N1024_M256_b22r15m5a4_dpi_beh"
SLOW, FAST = 0.9e9, 1.2e9
MLAT, ALAT, DIV = 5, 4, 19
BCAST, RET = 22, 15
VM_RT = 6                                   # broadcast reg 1 + fetch 3 + PRE 1 + OUT 1
SFU_D = {1: 7 * MLAT + 8 * ALAT + 4}        # exp 71
SFU_D[4] = SFU_D[5] = SFU_D[1] + ALAT + 19  # sigmoid / silu 94
SFU_D[2] = 1 + 9 * MLAT + 3 * ALAT          # rsqrt 58
SFU_D[3] = 31                               # sqrt
SFU_D[6] = SFU_D[1] + 11 * MLAT + 10 * ALAT + 50   # sqrt(softplus) 216
SFU_D[7] = 33 + SFU_D[4]                    # Engram gate
SFU_NAME = {1: "exp", 2: "rsqrt", 3: "sqrt", 4: "sigmoid", 5: "silu", 6: "sqrt(softplus)", 7: "egate"}
CATS = ("setup", "issue_barrier", "stream", "wire", "vm_round_trip", "arith", "passthrough", "reduction", "cdc",
        "serial_select")
# 1.2 GHz hub traverse for the floor: the 22 / 15 stages are at 0.9 GHz reach; at 1.2 GHz the reach per stage is
# 504 um (SS wire reach record) vs 748 um at 0.9 GHz, so a traverse of the same distance takes x 748/504 stages.
REACH_09, REACH_12 = 748.0, 504.0


# FLOORS (1.2 GHz cycles): the documented iteration target of each fused chain -- the longest dependence path of the
# golden's per-element op DAG on dedicated f12 units (mul 5, add/compare 4; SFU functions at LM 5 / LA 4: exp 71,
# sigmoid/silu 94, rsqrt 58, sqrt(softplus) 216, divide 19), the R-ARITH chunk-8 chain (7 adds) + log2 tree levels,
# the reducer's cross-lane result wire (6 slow stages -> 9 fast), the stream at 1,024 lanes, the quantiser block
# latency (13), and one hub traverse in (22 slow stages -> 33 fast) and out (15 -> 23).  `covers` are the graph node
# suffixes the fused chain replaces (its total sits on the last one).  Refined by each lever's own record.
HUB_IN, HUB_OUT, RED_WIRE = 33, 23, 9
FLOORS = {
    "norm": dict(covers=["hc_pre", "norm.sumsq", "norm.rsqrt", "norm.scale", "quant"], terms=dict(
        hub_in=HUB_IN, hc_mix_mul_3add_rnd=5 + 12 + 1, square=5, chunk_chain=28, tree_640_chunks=40, red_wire=RED_WIRE,
        div_n=19, add_eps=4, rsqrt=58, scale_mul_mul_rnd=11, quant=13, stream_5_vectors=4, hub_out=HUB_OUT)),
    "q_norm": dict(covers=["q_norm.sumsq", "q_norm.rsqrt", "q_norm.scale", "q_quant"], terms=dict(
        hub_in=HUB_IN, square=5, chunk_chain=28, tree_160_chunks=32, red_wire=RED_WIRE, div_n=19, add_eps=4, rsqrt=58,
        scale_mul_mul_rnd=11, quant=13, stream_2_vectors=1, hub_out=HUB_OUT)),
    "kv_norm": dict(covers=["kv_norm.sumsq", "kv_norm.rsqrt", "kv_norm.scale", "kv_rope_qdq"], terms=dict(
        hub_in=HUB_IN, square=5, chunk_chain=28, tree_64_chunks=24, red_wire=RED_WIRE, div_n=19, add_eps=4, rsqrt=58,
        scale_mul_mul_rnd=11, rope_mul_add_rnd=10, qdq=13, hub_out=HUB_OUT)),
    "softmax_T640": dict(covers=["max", "exp", "den", "sink", "normalize"], terms=dict(
        hub_in=HUB_IN, scale_mul=5, max_chain=28, max_tree_80_chunks=28, red_wire=RED_WIRE, sub=4, exp=71,
        sum_chain=28, sum_tree=28, red_wire2=RED_WIRE, den_add=4, divide=19, inv_rope=10, stream_10_vectors=9,
        hub_out=HUB_OUT)),
    "hc_post": dict(covers=["hc_post"], terms=dict(hub_in=HUB_IN, mul=5, add_chain_4=16, rnd=1, stream_20_vectors=19,
                                                  hub_out=HUB_OUT)),
    "router_act": dict(covers=["softplus_sqrt"], terms=dict(field_root_in=2, sqrt_softplus=216, stream_96_lanes=0,
                                                            out_reg=1)),
    "bias": dict(covers=["bias"], terms=dict(add_in_select_front=4)),
    "swiglu": dict(covers=["swiglu", "route_w", "quant2"], terms=dict(
        hub_in=HUB_IN, clip=1, silu=94, mul_u=5, mul_w=5, rnd=1, quant=13, stream_4_vectors=3, hub_out=HUB_OUT)),
    "z_quant": dict(covers=["z_quant"], terms=dict(field_root_in=2, quant_32_instances=13, stream_2_beats=1,
                                                   hub_out=HUB_OUT)),
}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return str(Path(p).resolve().relative_to(ROOT))


def op_arith(o):
    """(used, passthrough) cycles of the lane's fixed stages for op fields o (dshbm Chain op dict)."""
    m1 = DIV if o["m1"] in (4, 5) else MLAT
    used = 0
    used += m1 if o["m1"] != 0 else 0
    used += MLAT if (o["m2"] != 0 or o["qm"] != 0) else 0
    used += ALAT if o["ad"] != 0 else 0
    used += SFU_D.get(o["sfu"], 0)
    used += MLAT if o["e1"] != 0 else 0
    used += MLAT if o["e2"] != 0 else 0
    total = m1 + MLAT + ALAT + SFU_D.get(o["sfu"], 0) + MLAT + MLAT
    return used, total - used


def depth_parts(o, depth, wired=True):
    """The op's emit -> last write depth (the run's depth_model): hub stages, the FP units used / passed, and the
    rest (broadcast register, fetch 3 or 5 with a gather, PRE, OUT) as the VM round trip."""
    used, pas = op_arith(o)
    w = (BCAST + RET) if wired else 0
    vm = depth - w - used - pas
    assert vm in (VM_RT, VM_RT + 2), (o, depth, vm)
    return dict(wire=w, vm_round_trip=vm, arith=used, passthrough=pas)


def red_parts(o, po):
    """Reducer latency after the last write: IN/OUT 2, square MLAT (arith if red_sq else passthrough), chain 7 ALAT,
    tree + time levels ALAT each (the remainder)."""
    tot = po["last_result"] - po["last_write"]
    sq = MLAT
    chain = 7 * ALAT
    rest = tot - 2 - sq - chain
    return dict(vm_round_trip=2, arith=sq if o["redsq"] else 0, passthrough=0 if o["redsq"] else sq,
                reduction=chain + rest), dict(levels=rest // ALAT, total=tot)


def chain_timeline(ch, ops):
    """[(t0, t1, cat, op)] along the chain's critical sequence; completion time per op."""
    po = ch["per_op"]
    comp = []
    for k, p in enumerate(po):
        comp.append(p["last_result"] if p["last_result"] is not None else p["last_write"])
    segs = []
    for k, p in enumerate(po):
        o = ops[k]
        anc = 0
        for j in range(k):
            for c in (po[j]["last_write"], po[j]["last_result"]):
                if c is not None and c <= p["last_write"] and c > anc:
                    anc = c
        if k == 0:
            anc = 0
        e0 = max(p["first_emit"], anc)
        if p["first_emit"] > anc:
            segs.append((anc, p["first_emit"], "setup" if k == 0 else "issue_barrier", k))
        if p["last_emit"] > e0:
            segs.append((e0, p["last_emit"], "stream", k))
        dp = depth_parts(o, p["depth_model"])
        start = p["last_emit"]
        hidden = max(0, anc - p["last_emit"])
        for cat in ("wire", "vm_round_trip", "passthrough", "arith"):      # hidden part comes off the front
            n = dp[cat]
            cut = min(n, hidden)
            hidden -= cut
            if n - cut > 0:
                s0 = max(start, anc)
                segs.append((s0, s0 + n - cut, cat, k))
                start = s0 + n - cut
            else:
                start = max(start, anc)
        assert start == p["last_write"], (ch["chain"], k, start, p)
        if p["last_result"] is not None:
            rp, _ = red_parts(o, p)
            t = p["last_write"]
            for cat, n in rp.items():
                if n:
                    segs.append((t, t + n, cat, k))
                    t += n
            assert t == p["last_result"]
    return segs, comp


def attribute(segs, t0, t1):
    out = collections.Counter()
    # the critical sequence may hold overlapping segments of parallel ops; take, per cycle, the segment of the op
    # that completes last among those covering it (the binding op)
    for t in range(t0, t1):
        cov = [s for s in segs if s[0] <= t < s[1]]
        if not cov:
            out["issue_barrier"] += 1
            continue
        s = max(cov, key=lambda s: (s[3], s[1]))
        out[s[2]] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--cases-rw", required=True)
    ap.add_argument("--out", default=str(ROOT / "results/rtl/dsrom_recovery_20261004/su_chains/anatomy.json"))
    a = ap.parse_args()
    runs = [RUNS / f"{WIRED}.json", RUNS / f"{WIRED}_su_cases_rw.json"]
    cases = {}
    for p, r in zip((a.cases, a.cases_rw), runs):
        d = pickle.loads(Path(p).read_bytes())
        h = sha(p)
        want = json.loads(r.read_text())["cases_sha256"]
        assert h == want, (p, h, want)
        for c in d["cases"]:
            cases[c["name"]] = c
    su = json.loads((REC / "su.json").read_text())
    qd = json.loads((REC / "su_qdq_wired.json").read_text())["nodes"]
    comp = json.loads(COMP.read_text())
    # ---- per chain, per node categories (slow cycles)
    node_cat = {}
    chains_out = []
    for rp in runs:
        for ch in json.loads(rp.read_text())["chains"]:
            if ch.get("exact") is None:
                continue
            ops = cases[ch["chain"]]["ops"]
            segs, compk = chain_timeline(ch, ops)
            prev = 0
            L = ch["layer"]
            nodes = []
            for nd in ch["nodes"]:
                po = ch["per_op"][nd["op"]]
                c = po["last_result"] if nd["event"] == "result" else (po["last_write"] if po["last_write"] is not None
                                                                         else po["last_result"])
                cats = attribute(segs, prev, c)
                base = nd["node"].partition(":")[0]
                g = base if base.startswith("head.") else f"{L}.{base}"
                want = su["nodes"].get(g, {}).get("wired_measured_cycles")
                if want is not None and nd["node"].partition(":")[2] == "":
                    assert sum(cats.values()) == want, (g, dict(cats), want)
                node_cat[g] = dict(cycles=c - prev, cats=dict(cats), chain=ch["chain"], part=nd["node"].partition(":")[2]
                                   or "whole")
                nodes.append(dict(node=g, cycles=c - prev, **{k: cats.get(k, 0) for k in CATS if cats.get(k)}))
                prev = c
            tot = collections.Counter()
            for s in attribute(segs, 0, prev).items():
                tot[s[0]] += s[1]
            chains_out.append(dict(
                chain=ch["chain"], fn=ch["fn"], layer=L, total_cycles=prev, total_us=round(prev / SLOW * 1e6, 5),
                categories={k: tot.get(k, 0) for k in CATS if tot.get(k)}, nodes=nodes,
                ops=[dict(op=k, vectors=p["vectors"], nout=p["nout"], nin=p["nin"], depth=p["depth_model"],
                          sfu=SFU_NAME.get(ops[k]["sfu"]), m1=ops[k]["m1"], red=ops[k]["red"], redsq=ops[k]["redsq"],
                          arith_used=op_arith(ops[k])[0], passthrough=op_arith(ops[k])[1],
                          reducer=(red_parts(ops[k], p)[1] if p["last_result"] is not None else None))
                     for k, p in enumerate(ch["per_op"])]))
    # ---- quantisers (one ot_hdc_actquant / fp4qdq instance + 37 simulated hub stages)
    for g, r in qd.items():
        lat = r["unit_cycles"] - r["blocks"]
        cats = dict(stream=r["blocks"] - 1, arith=lat + 1, wire=r["qdq_wired_cycles"] - r["unit_cycles"])
        assert sum(cats.values()) == r["qdq_wired_cycles"]
        key = g if r["part"] == "whole" else g + ":qdq"
        node_cat[key] = dict(cycles=r["qdq_wired_cycles"], cats=cats, chain=f"quant.{r['kind']}", part=r["part"])
    # ---- the recovery AR critical path
    patches = {p["node"]: p for p in comp["patches"]}
    lever_nodes = {p["node"] for p in comp["patches"] if str(p.get("source", "")).split(":")[0] in
                   {x["lever"] for x in comp["info"]["levers"]["applied"]} and
                   not p["node"].endswith(("ffn.top6", "ffn.top6_order"))}
    path_tot = collections.Counter()
    by_fam = collections.defaultdict(collections.Counter)
    fam_us = collections.Counter()
    fam_n = collections.Counter()
    unmapped = []
    su_path_us = 0.0
    rows = []
    for e in comp["critical_path"]:
        n = e["node"]
        head, _, suf = n.partition(".")
        if head.startswith("L") and head[1:].isdigit():
            rep = AD.rep_layer(int(head[1:]), None)
            key = f"{rep}.{suf}"
            if key not in node_cat and f"L20.{suf}" in node_cat:
                key = f"L20.{suf}"
        elif head == "head":
            key, rep = n, "head"
        else:
            continue
        us = e["us"]
        cdc_us = patches.get(n, {}).get("cdc_measured_us", 0.0) or 0.0
        cat = None
        if suf in ("ffn.top6", "ffn.top6_order"):
            cat = {"serial_select": (us - cdc_us) * SLOW / 1e6}
        elif n in lever_nodes:
            continue                                      # re-measured by an adopted lever (not the SU any more)
        elif key in node_cat:
            x = node_cat[key]
            cat = dict(x["cats"])
            if x["part"] == "rope":                       # RoPE part + its QDQ (wired), as the adapter composes
                q = node_cat.get(key + ":qdq")
                if q:
                    for k, v in q["cats"].items():
                        cat[k] = cat.get(k, 0) + v
        if cat is None:
            continue
        cyc = sum(cat.values())
        meas_us = cyc / SLOW * 1e6
        if abs(meas_us + cdc_us - us) > 2e-4 and not (suf in ("ffn.top6", "ffn.top6_order")):
            unmapped.append(dict(node=n, path_us=us, anatomy_us=round(meas_us + cdc_us, 5)))
            continue
        su_path_us += us
        fam = suf.split(".", 1)[1] if "." in suf else suf
        fam = suf
        fam_us[fam] += us
        fam_n[fam] += 1
        for k, v in cat.items():
            u = v / SLOW * 1e6
            path_tot[k] += u
            by_fam[fam][k] += u
        if cdc_us:
            path_tot["cdc"] += cdc_us
            by_fam[fam]["cdc"] += cdc_us
        rows.append(n)
    fam_rows = []
    for fam, us in sorted(fam_us.items(), key=lambda x: -x[1]):
        fam_rows.append(dict(node=fam, on_path=fam_n[fam], us_on_path=round(us, 3),
                             categories_us={k: round(by_fam[fam].get(k, 0.0), 3) for k in CATS if by_fam[fam].get(k)}))
    floors = {}
    for k, f in FLOORS.items():
        cyc = sum(f["terms"].values())
        floors[k] = dict(covers=f["covers"], floor_cycles_1p2GHz=cyc, floor_us=round(cyc / FAST * 1e6, 5),
                         terms=f["terms"],
                         now_us_on_path_per_occurrence={c: round(fam_us[f"{pre}.{c}"] / fam_n[f"{pre}.{c}"], 5)
                                                        for c in f["covers"] for pre in ("attn", "ffn")
                                                        if fam_n.get(f"{pre}.{c}")})
    res = dict(
        schema="opentallas.dsrom-recovery.su-anatomy.v1",
        scope=("Latency anatomy of the SU chains on the recovery AR token's critical path at position 1,048,575 (1M), "
               "from the committed wired full-shape RTL runs (ot_hdc_v41x_vec N 1,024 / M 256, MLAT 5 / ALAT 4, "
               "BCAST 22 / RET 15, 0.9 GHz) and the quantiser wired record; no new simulation."),
        method=__doc__.split("Method.")[1].split("The FLOOR")[0].strip(),
        clock_hz=SLOW,
        token=dict(AR_us=comp["AR_us"], AR_tok_s=comp["AR_tok_s"], cdc_on_path_us=comp.get("cdc_on_path_us")),
        su_on_path_us=round(su_path_us, 3), su_on_path_nodes=len(rows),
        su_on_path_share=round(su_path_us / comp["AR_us"], 4),
        categories_on_path_us={k: round(path_tot.get(k, 0.0), 3) for k in CATS},
        by_node_family=fam_rows,
        unmatched_path_nodes=unmapped,
        floors=floors,
        floors_note=("documented iteration targets, not measurements: the FLOOR of each fused chain is the same exact "
                     "arithmetic in one 1.2 GHz pipeline (see FLOORS in the tool); each lever record refines its own"),
        chains=chains_out,
        constants=dict(MLAT=MLAT, ALAT=ALAT, divide=DIV, BCAST=BCAST, RET=RET, vm_round_trip=VM_RT,
                       sfu_depth={SFU_NAME[k]: v for k, v in SFU_D.items()}),
        inputs={rel(p): sha(p) for p in (*runs, REC / "su.json", REC / "su_qdq_wired.json", COMP)},
        cases_sha256={Path(a.cases).name: sha(a.cases), Path(a.cases_rw).name: sha(a.cases_rw)},
        tool_sha256=sha(__file__))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(dict(su_on_path_us=res["su_on_path_us"], share=res["su_on_path_share"],
                          cats=res["categories_on_path_us"], unmatched=len(unmapped)), indent=1))
    for r in fam_rows[:30]:
        print(f"{r['node']:28s} {r['on_path']:3d} {r['us_on_path']:8.3f} {r['categories_us']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
