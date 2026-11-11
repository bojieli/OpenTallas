#!/usr/bin/env python3
"""S81 svc provider form A: pin_cycle_deltas v6 (DIE-S81-85 sub-lane, 11-10; S81-SVCRS-3 request 14:05, COORD approved
recipe-4 pin registers on s81svc_irg = ot_s81_svc_idx_hslice_fp).  DO_NOT_COUNT.

v5 (svc_prov_event_1109.py pin_cycles) priced every hard-box face crossing as delta = 1 + relay_stations: ONE pin
stage per crossing.  That is right for SOFT -> box (the box's input pin register) and box -> SOFT (its output
register), but a box -> box hop between two recipe-4 boxes crosses TWO pin stages (the source's output register and
the sink's input register).  v6 prices each crossing from the stages of its two ends:

    delta = out_stages(src) + in_stages(dst) + relay_stations          (relay_stations: v5 geometry, unchanged)

    recipe-4 boxes (pin_regs: +1 on every data input, +1 on every data output; clk / rst_n 0):
        SML SMC SMR SMD H4 TRX  (already in v5)  and  IRG (new, COORD 11-10)
    SOFT (parent soft logic) and TILE (ot_s81c_attn_hcore: faces are its own source flops, placed by face_flops.tcl,
        not recipe pin stages) contribute 0.

Edges that change against v5:
    SML*->SMC, SMC->SMR, SMR->SMD   box -> box: +1 each (the under-priced second pin stage)
    IRG*->IRG*                      NEW: the chunk chain hop slice h -> h + 1 (ql_* / k_key / cs_* / cf_*), 7 hops per
                                    chunk column, adjacent boxes (86.4 pitch, 8.64 seam): 1 + 1 + 0 = 2
    SOFT*->IRG*, IRG*->SOFT*        same numbers as v5 (1 and 1 + relays).  In v5 the IRG had pin_regs disabled
                                    (source-registered: its pin flops are inside the RTL engine latency EL), so v5's
                                    face stage on these two edges was not a cycle the cut added; under recipe-4 it is.

The IRG stages are cycles ADDED to the RTL engine: per chunk column path (key / Q in at slice 0, cs_out of slice 7)
+1 + 7 x 2 + 1 = +16 edges, so dsdv_idx_rg3(_nq) EL 124 -> 140 (the metadata ring read offset mw - (EL + KR - 1) and
the warm count).  See the event note irg_engine for the evidence.

    python3 svc_prov_pcd_v6_1110.py V5_EVENT OUT_JSON
"""
import argparse
import hashlib
import json
from pathlib import Path

# (in_stages, out_stages) per box kind under the v6 model
STAGES_V6 = {k: (1, 1) for k in ("SML", "SMC", "SMR", "SMD", "H4", "TRX", "IRG")}
STAGES_V6.update(SOFT=(0, 0), TILE=(0, 0))
IRG_CHAIN = ("IRG*->IRG*", "hslice chain h -> h+1: ql_* / k_key / cs_* / cf_* (lo)")
HC = 8                       # slices per chunk column (dsdv_idx_rg2_chunk HC)
EL_V5 = 124                  # dsdv_idx_rg3 / _nq EL: chunk 106 + tail 18 edges (dsdv_idx_rg3.sv:34)
ROOT = Path(__file__).resolve().parents[3]


def kind(end):
    return end.rstrip("*")


def edge_delta(edge, relay):
    a, b = edge.split("->")
    src_out = STAGES_V6[kind(a)][1]
    dst_in = STAGES_V6[kind(b)][0]
    return dict(src_out=src_out, dst_in=dst_in, relay_stations=relay, delta=src_out + dst_in + relay)


def irg_chain_ok(boxes):
    """every IRG{c}_{h} -> IRG{c}_{h+1} pair abuts W -> E in one band (0 relay stations)"""
    irg = {b["name"]: b for b in boxes if b["kind"] == "IRG"}
    hops = 0
    for n, b in irg.items():
        c, h = (int(x) for x in n[3:].split("_"))
        nxt = irg.get(f"IRG{c}_{h + 1}")
        if nxt is None:
            continue
        gap = nxt["origin_um"][0] - (b["origin_um"][0] + b["outline_um"][0])
        assert nxt["origin_um"][1] == b["origin_um"][1] and 0 <= gap < 405.0, (n, gap)
        hops += 1
    return hops


def v6_type(t):
    pc = {}
    for e, v in t["pin_cycles"].items():
        pc[e] = dict(note=v["note"], worst_um=v["worst_um"], v5_delta=v["delta"], **edge_delta(e, v["relay_stations"]))
    if any(b["kind"] == "IRG" for b in t["boxes"]):
        hops = irg_chain_ok(t["boxes"])
        assert hops == 4 * (HC - 1), hops
        pc[IRG_CHAIN[0]] = dict(note=IRG_CHAIN[1], worst_um=8.64, v5_delta=None, chain_hops=hops,
                                **edge_delta(IRG_CHAIN[0], 0))
    return pc


def irg_engine(pcd_lo):
    d_in = STAGES_V6["IRG"][0]
    d_out = STAGES_V6["IRG"][1]
    chain = (HC - 1) * pcd_lo[IRG_CHAIN[0]]
    added = d_in + chain + d_out
    return dict(
        added_edges=added, el_v5=EL_V5, el_v6=EL_V5 + added,
        breakdown=f"IRG input stage at slice 0 ({d_in}) + {HC - 1} chain hops x {pcd_lo[IRG_CHAIN[0]]} + IRG output "
                  f"stage at slice 7 ({d_out})",
        where="dsdv_idx_rg3_nq #(.EL(...)) u_irg in the svc_lo bind (bound with .EL(124), KR 0; "
              "tools/die_plan/test_s81_svc_memory_closure.py:80) and dsdv_idx_rg3 / dsdv_idx_rg3_nq_native EL "
              "(metadata ring ra = mw - (EL + KR - 1), warm at EL + KR + 2)",
        relays_not_in_el=("the reader-side relay stations priced on SOFT*->IRG* / IRG*->SOFT* are not in EL either: if "
                          "they are built as flop stages on the slice-0 input / slice-7 cs_out paths, EL grows by "
                          "their count on those two paths too"),
        intra_chunk="unchanged: key, Q and cs hops all grow by the same 2 edges, so the term pad FPL * hid[2:0] "
                    "(cs step - key step = 7) still meets cs_in at its date; no hslice constant changes")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("v5_event")
    ap.add_argument("out")
    a = ap.parse_args()
    raw = Path(a.v5_event).read_bytes()
    src = Path(a.v5_event).resolve()
    src = str(src.relative_to(ROOT)) if src.is_relative_to(ROOT) else str(src)
    ev = json.loads(raw)
    types = {tn: v6_type(t) for tn, t in ev["types"].items()}
    pcd = {tn: {e: v["delta"] for e, v in pc.items()} for tn, pc in types.items()}
    lo = next(tn for tn in pcd if tn.startswith("svc_lo"))
    out = dict(
        schema="opentallas.s81_svc_pin_cycles.v6", tool="physical/die_plan/s81/svc_prov_pcd_v6_1110.py",
        lane="DIE-S81-85 (sub-lane ds85-svc-irg-pcd)", do_not_count=True,
        request="S81-SVCRS-3 11-10 14:05: COORD approved recipe-4 pin registers on s81svc_irg (+1 every data input, "
                "+1 every data output, clk / rst_n 0)",
        supersedes_pin_cycle_deltas_of=dict(event=src, sha256=hashlib.sha256(raw).hexdigest(),
                                            plan_output_sha256=ev.get("plan_output_sha256")),
        plan_change="none: pin registers are box-internal; boxes, outlines, soft regions and the v5 plan are unchanged",
        model=dict(rule="delta = out_stages(src) + in_stages(dst) + relay_stations (v5 geometry)",
                   stages={k: dict(zip(("in", "out"), v)) for k, v in STAGES_V6.items()},
                   v5_rule="delta = 1 + relay_stations (one pin stage per crossing)"),
        pin_cycle_deltas=pcd, pin_cycles=types, irg_engine=irg_engine(pcd[lo]),
        changed_vs_v5={tn: {e: [v["v5_delta"], v["delta"]] for e, v in pc.items() if v["v5_delta"] != v["delta"]}
                       for tn, pc in types.items()})
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(types=len(pcd), changed=out["changed_vs_v5"][lo], irg_engine=out["irg_engine"]["el_v6"])))


if __name__ == "__main__":
    main()
