#!/usr/bin/env python3
"""S81 stage programs and their golden program trace (stream ds-control, 2026-10-08).

The golden program trace of one S81 stage is the stage's operator graph from the DS-ROM token-path composition
(results/arch/token_path_20261008/ds_rom.json: tools/dsrom_1m_allmeasured.py's graph of the golden decode step
tools/hdc_golden_v41.py at 1M context, every node with its measured cycles), scheduled ASAP, which is exactly what the
composition does (Graph.solve; every node's start == max(end of its predecessors), checked below).  Per stage group
(S000..S057 layer stages, S058 the head die) this tool emits:

  * the stage PROGRAM: the engine jobs in golden start order, {engine port, arg}, i.e. what ot_s81_stage_seq's
    program memory holds;
  * the golden TRACE: every job's start / end in integer cycles relative to the stage start (the stage input landing),
    with its in-stage predecessors and the arrival time of its cross-stage inputs (SIDE state, the hidden state);
  * the bench image (hex) for rtl/dsrom_sys/s81_ctrl/test/tb_s81_stage_seq.sv.

Integer cycles: every node's cycles are rounded half up (the composition carries 0.1-cycle terms); the integer
makespan is reported against the composition's group cycles.  Zero-cycle nodes (operators fused into a measured
neighbour, e.g. norm.sumsq inside su_norm's attn.quant) are not jobs: their predecessors are bridged to their
successors.  Engine ports (ENG): what drives the job on the S81 die.

    python3 tools/s81_ctrl/stage_programs.py [--out results/rtl/s81_ctrl_20261008/programs]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TP = ROOT / "results/arch/token_path_20261008/ds_rom.json"

# engine ports of the S81 die (ot_s81_ctrl ENG_*): the slab / master that executes the job
ENG = dict(fld=0, su=1, hc=2, coll=3, svc=4, sel=5, col=6, hop=7, head=8, emb=9, eng=10, spare=11)
NPRED = 8


def eng_of(n):
    op, cls, kind = n["op"], n["cls"], n["kind"]
    if cls == "field":
        return "eng" if op.startswith("eng.") else "fld"
    if cls == "su":
        if ".hc" in op or op.startswith("attn.hc") or op.startswith("ffn.hc"):
            return "hc"
        if op.startswith("eng."):
            return "eng"
        return "su"
    if cls == "coll":
        return "coll"
    if cls == "hbm":
        return "svc"
    if cls == "select":
        return "col" if op == "attn.gather" else "sel"
    if cls == "hop":
        return "hop"
    if cls == "head":
        return "head"
    if cls == "embed":
        return "emb"
    raise ValueError(n["id"])


def rnd(x):
    return int(math.floor(x + 0.5))


def build(tp):
    nodes = {n["id"]: n for n in tp["nodes"]}
    pred = defaultdict(set)
    for e in tp["edges"]:
        pred[e["dst"]].add(e["src"])
    # the composition is ASAP: start == max(end of preds)
    asap_bad = [n for n in nodes.values() if pred[n["id"]] and
                abs(max(nodes[p]["end"] for p in pred[n["id"]]) - n["start"]) > 1e-6]
    groups = [g for g in tp["groups"] if g["id"] != "SX"]
    progs = []
    for g in groups:
        ids = [n["id"] for n in tp["nodes"] if n["group"] == g["id"]]
        inset = set(ids)
        dur = {i: rnd(nodes[i]["cycles"]) for i in ids}
        # cross-group inputs: arrival relative to the group start (>= 0)
        ext = {}
        for i in ids:
            xs = [nodes[p]["end"] - g["start"] for p in pred[i] if p not in inset]
            ext[i] = max(0, rnd(max(xs))) if xs else 0
        ipred = {i: {p for p in pred[i] if p in inset} for i in ids}
        # topological order (the record lists nodes in start order; re-derive to be safe)
        order, seen = [], set()

        def visit(i):
            if i in seen:
                return
            seen.add(i)
            for p in sorted(ipred[i]):
                visit(p)
            order.append(i)
        for i in ids:
            visit(i)
        # bridge zero-cycle nodes
        jobs = [i for i in order if dur[i] > 0]
        eff = {}            # node -> (set of job preds, ext)
        for i in order:
            ps, ex = set(), ext[i]
            for p in ipred[i]:
                if dur[p] > 0:
                    ps.add(p)
                else:
                    ps |= eff[p][0]
                    ex = max(ex, eff[p][1])
            eff[i] = (ps, ex)
        # golden ASAP on integers
        st, en = {}, {}
        for i in order:
            ps, ex = eff[i]
            st[i] = max([ex] + [en[p] for p in ps])
            en[i] = st[i] + dur[i]
        makespan = max(en.values()) if en else 0
        crit = [i for i in ids if nodes[i]["critical"]]
        crit_end = max((en[i] for i in crit), default=0)
        jobs.sort(key=lambda i: (st[i], order.index(i)))
        idx = {i: k for k, i in enumerate(jobs)}
        ops = []
        for k, i in enumerate(jobs):
            ps = sorted(idx[p] for p in eff[i][0])
            assert all(p < k for p in ps), (g["id"], i)
            ops.append(dict(op=k, id=i, eng=eng_of(nodes[i]), port=ENG[eng_of(nodes[i])], dur=dur[i],
                            ext=eff[i][1], preds=ps, start=st[i], end=en[i],
                            comp_start=round(nodes[i]["start"] - g["start"], 1),
                            comp_cycles=nodes[i]["cycles"]))
        # per-port starts are monotone in program order (in-order engines)
        last = {}
        for o in ops:
            assert o["start"] >= last.get(o["port"], -1), (g["id"], o["id"])
            last[o["port"]] = o["start"]
        progs.append(dict(stage=g["id"], kind=g["kind"], layers=g.get("layers"), comp_span=round(g["end"] - g["start"], 1),
                          comp_crit_cycles=g["cycles"], max_start_drift=max([abs(o["start"] - o["comp_start"]) for o in ops] + [0]),
                          makespan=makespan, crit_end=crit_end, n_nodes=len(ids), n_jobs=len(ops),
                          max_fanin=max([len(o["preds"]) for o in ops] + [0]),
                          ports=sorted({o["eng"] for o in ops}), ops=ops))
    return progs, len(asap_bad)


def hexline(o):
    ps = o["preds"]
    assert len(ps) <= NPRED
    v = o["port"]
    v = (v << 24) | o["dur"]
    v = (v << 24) | o["ext"]
    v = (v << 4) | len(ps)
    for j in range(NPRED):
        v = (v << 8) | (ps[j] if j < len(ps) else 0)
    v = (v << 24) | o["start"]
    return f"{v:040x}"           # 4+24+24+4+64+24 = 144 bits -> 36 hex digits, padded to 40


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "results/rtl/s81_ctrl_20261008/programs")
    ap.add_argument("--native-registry", type=Path,
                    help="Compile owner-provided native endpoint jobs; missing binding fails closed")
    ap.add_argument("--native-context", type=Path,
                    help="Explicit token/user/epoch/address context JSON for native compilation")
    a = ap.parse_args()
    tp = json.loads(TP.read_text())
    progs, asap_bad = build(tp)
    a.out.mkdir(parents=True, exist_ok=True)
    hexdir = a.out / "hex"
    hexdir.mkdir(exist_ok=True)
    index = []
    for p in progs:
        (a.out / f"{p['stage']}.json").write_text(json.dumps(p, indent=1) + "\n")
        lines = [hexline(o) for o in p["ops"]]
        (hexdir / f"{p['stage']}.hex").write_text("\n".join(lines) + "\n")
        index.append(dict(stage=p["stage"], kind=p["kind"], n_jobs=p["n_jobs"], n_nodes=p["n_nodes"],
                          makespan=p["makespan"], crit_end=p["crit_end"], comp_span=p["comp_span"],
                          delta=round(p["crit_end"] - p["comp_span"], 1), max_start_drift=round(p["max_start_drift"], 1), max_fanin=p["max_fanin"],
                          ports=p["ports"]))
    rec = dict(schema="opentallas.s81-ctrl.stage-programs.v1", tool="tools/s81_ctrl/stage_programs.py",
               source=str(TP.relative_to(ROOT)), source_sha256=hashlib.sha256(TP.read_bytes()).hexdigest(),
               composition_asap_mismatches=asap_bad, engine_ports=ENG, npred=NPRED,
               max_jobs=max(p["n_jobs"] for p in progs), max_fanin=max(p["max_fanin"] for p in progs),
               stages=index)
    (a.out / "index.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"{len(progs)} programs, max jobs {rec['max_jobs']}, max fan-in {rec['max_fanin']}, "
          f"ASAP mismatches {asap_bad}, max |critical end - composition group span| "
          f"{max(abs(x['delta']) for x in index)}, max |start - composition start| {max(x['max_start_drift'] for x in index)}")
    if a.native_registry:
        from native_descriptors import compile_jobs, digest
        context = json.loads(a.native_context.read_text()) if a.native_context else {}
        request = {"context": context,
                   "jobs": [{"id": op["id"], "engine": op["port"]}
                            for program in progs for op in program["ops"]]}
        native = compile_jobs(request, json.loads(a.native_registry.read_text()), ROOT)
        native["registry_sha256"] = digest(a.native_registry)
        native["composition_sha256"] = rec["source_sha256"]
        native["scope"] = "Named native command signals only; execution/stream/VM binding requires its own exact gate"
        (a.out / "native_dispatch.json").write_text(json.dumps(native, indent=2) + "\n")
        if not native["dispatch_eligible"]:
            print(f"Native dispatch BLOCKED: {len(native['rejected'])} unbound/invalid jobs; no dispatch rows emitted")
            raise SystemExit(2)


if __name__ == "__main__":
    main()
