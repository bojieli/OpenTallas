#!/usr/bin/env python3
"""H-MTP2/idx: IDX.INDEX P-query (P-row) cost spec, derived from the die-bound static INDEX calendar.

The static INDEX frame is the compiled microprogram of tools/hbm_idx_static_calendar.py, issued one instruction an edge
by ot_hbm_idx_calendar_static (measured II 1, start->first 3: rtl/test/hbm_idx_static/evidence/calendar/receipt.json);
the parent never waits, so the frame length IS the RTL frame time.  This tool compiles the calendar, decodes every
instruction into the unit that is busy on that edge (VM query read, query emit to the 2,048 hslices, key beats into the
scorer array, selector radix ops, link emits) and derives, per P-query realisation, the per-extra-query initiation
interval II (edges) as the busy span of the binding unit:

  S   as built: P independent frames (keys re-streamed P times)                    II = frame
  Q1  P frames, query load / head emit of q+1 overlapped (double-buffered query bank), keys re-streamed, ONE selector
  Q1b Q1 + double-buffered selector line memory (ingest of q+1 overlaps the passes of q)
  Q2  the model's form (ONE key stream): every hslice holds P query slots, a key beat is held P edges (one per slot),
      the score stream is interleaved -> P selectors (or P x selector memory with serial passes)

  hbm_idx_index_rows_spec.py OUT.json [P=6]
"""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAL = ROOT / "tools/hbm_idx_static_calendar.py"
P = int(sys.argv[2]) if len(sys.argv) > 2 else 6
DFF_UM2 = 0.2916            # ASAP7 DFFHQNx1_ASAP7_75t_R
HSLICES = 2048
QSLOT_BITS = 4 * 128 + 4 * 8 + 16          # ot_hdc_v41x_idx_hslice query registers qc / qs / qw (NB 4)
QBANK_BITS = 16384 + 1024 + 512             # ot_hbm_idx_query_static codes / scales / weights (one query, 32 heads)
SEL_TILE_MM2 = 317.52 * 1164.24 / 1e6       # idx_sel grant outline (hbm_v15 grants v5)
Q_TILE_MM2 = 449.28 * 449.28 / 1e6          # idx_q grant outline


def main():
    with tempfile.TemporaryDirectory() as td:
        subprocess.run([sys.executable, str(CAL), td], check=True)
        ins = [int(x, 16) for x in (Path(td) / "calendar_instructions.hex").read_text().split()]
    n = len(ins)
    f = lambda w, lo, nb: (w >> lo) & ((1 << nb) - 1)
    edges = dict(weight=[], query=[], head=[], beat=[], sel=[], link=[], flush=[])
    for e, w in enumerate(ins):
        if f(w, 31, 1): edges["weight"].append(e)
        if f(w, 30, 1): edges["query"].append(e)
        if f(w, 29, 1): edges["head"].append(e)
        if f(w, 28, 1): edges["beat"].append(e)
        if f(w, 16, 4) not in (0, 1): edges["sel"].append(e)
        if f(w, 4, 1): edges["link"].append(e)
        if f(w, 5, 1): edges["flush"].append(e)
    span = {k: (v[0], v[-1], v[-1] - v[0] + 1, len(v)) for k, v in edges.items() if v}
    sel0, sel1 = span["sel"][0], span["sel"][1]
    ingest_end = edges["beat"][-1] + 123                      # selector op 2 ingest window ends 123 edges after the last beat
    frame = n
    q_load = span["head"][1] - span["weight"][0] + 1 + 100    # weight/query read, quant, head emit, 100-edge settle
    array = span["head"][2] + 100 + span["beat"][2]           # hslice busy a query: head emit + settle + key beats
    sel_busy = sel1 - sel0 + 1
    sel_pass = sel1 - ingest_end                              # passes after the ingest window
    ii = dict(
        S=frame,
        Q1=max(sel_busy, array, span["query"][3]),
        Q1b=max(sel_pass, array, span["beat"][2]),
        # Q2: a key beat held P edges -> per extra query the array spends its beat edges + its query load / emit
        Q2_P_selectors=span["query"][3] + span["head"][2] + span["beat"][2],
    )
    area = dict(
        Q1=QBANK_BITS * DFF_UM2 / 1e6,
        Q1b=QBANK_BITS * DFF_UM2 / 1e6 + SEL_TILE_MM2 * 0.5,
        Q2_P_selectors=(P - 1) * QSLOT_BITS * HSLICES * DFF_UM2 / 1e6 + (P - 1) * SEL_TILE_MM2,
    )
    rec = dict(
        schema="opentallas.hbm_mtp_1015.idx_index_rows_spec.v1", P=P,
        calendar=dict(source=str(CAL.relative_to(ROOT)), sha256=hashlib.sha256(CAL.read_bytes()).hexdigest(),
                      frame_edges=frame, unit_spans={k: dict(first=a, last=b, span=c, slots=d) for k, (a, b, c, d) in span.items()},
                      selector_busy_edges=sel_busy, selector_after_ingest=sel_pass, query_load_emit_edges=q_load,
                      array_busy_per_query=array),
        ii_edges=ii, ii_over_frame={k: round(v / frame, 4) for k, v in ii.items()},
        p6_edges={k: frame + (P - 1) * v for k, v in ii.items()},
        model=dict(ii_over_c1=round(152.0 / 658.9, 4), basis="ds_mtp_verify.row_ii IDX.INDEX: c1 x 152 / 658.9"),
        added_area_mm2_estimate={k: round(v, 4) for k, v in area.items()},
        area_basis=dict(dff_um2=DFF_UM2, hslices=HSLICES, query_slot_bits_per_hslice=QSLOT_BITS,
                        query_bank_bits=QBANK_BITS, selector_tile_mm2=round(SEL_TILE_MM2, 4),
                        query_tile_mm2=round(Q_TILE_MM2, 4),
                        note="flop-only estimates (no mux/clock); Q1b: half a selector tile for a second line memory"),
    )
    Path(sys.argv[1]).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(frame=frame, ii=ii, ratio=rec["ii_over_frame"], area=rec["added_area_mm2_estimate"],
                          spans=rec["calendar"]["unit_spans"]), indent=1))


if __name__ == "__main__":
    main()
