#!/usr/bin/env python3
"""[svc-ep] N8 proof ([svc] hbm-phys 2026-10-10, lead condition 1): the PS svc sends index keys (IDX.INDEX, kind-2 streams)
and attention KV (ATT.QK / ATT.PV, kind-1 streams) on the SAME group row ports ks<k>, one stream at a time.  This tool
reads the designed DS schedule (approved path, the same one as tools/svc_dma_hc_sizing.py: ds_sw_seq_pricing
approved_path_c2_g22, S2, committed rank-0 program + 1M run) and checks whether any IDX.INDEX window intersects any ATT
window (including IDX.INDEX of layer L+1 against ATT of layer L).  Overlap -> one-stream-at-a-time costs rate and the
ports must be sized separately; no overlap -> the shared ks port is free.  Writes results/arch/svc_stream_overlap_20261010.json."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from hgi_sim import timing as T  # noqa: E402
from hgi_sim import ds_native_timing as DT  # noqa: E402
import hgi_sim.ds_sw_seq_pricing as P  # noqa: E402


def main():
    src = ROOT / 'results/arch/hgi_programs_20261010/inputs'
    prog, run = src / 'ds_rank0_program.json', src / 'ds_native_1M_run.json'
    d, recs = DT.load(prog)
    recs = T.rebuild_waits(recs)
    rg = {}
    for x in json.loads(run.read_text())['results']:
        for s in x.get('row_gather') or []:
            rg[x['layer']] = s
    cf = P.SeqCost(d['ops'], recs, rg, c=2, hc_g22=True)
    s = T.schedule(recs, DT.POS, 'S2', cost_fn=cf)
    ex = T.expand(recs, DT.POS)
    win = lambda pred: sorted((s['start'][i], s['end'][i], recs[k].layer, recs[k].op) for i, (k, *_) in enumerate(ex) if pred(recs[k]))  # noqa: E731
    idx = win(lambda r: r.unit == 'IDX' and r.op == 'INDEX')
    att = win(lambda r: r.unit == 'ATT' and r.op in ('QK', 'PV'))
    pairs = [(i, a) for i in idx for a in att if i[0] < a[1] and a[0] < i[1]]
    # nearest approach: the smallest gap between an IDX.INDEX window and any ATT window (cycles; < 0 = overlap)
    gap = min(max(a[0] - i[1], i[0] - a[1]) for i in idx for a in att)
    nxt = []      # IDX.INDEX of layer L+1 against ATT of layer L
    for i in idx:
        prev = [a for a in att if a[2] == i[2] - 1]
        if prev:
            nxt.append(dict(idx_layer=i[2], idx_start=round(i[0], 1), att_prev_end=round(max(a[1] for a in prev), 1),
                            slack=round(i[0] - max(a[1] for a in prev), 1)))
    out = dict(schema='opentallas.svc_stream_overlap.v1', tool='tools/svc_stream_overlap.py',
               source=dict(program=str(prog.relative_to(ROOT)), run=str(run.relative_to(ROOT)),
                           schedule='ds_sw_seq_pricing approved_path_c2_g22 (S2)'),
               token_cycles=round(s['total_cycles'], 1), idx_index_windows=len(idx), att_windows=len(att),
               overlapping_pairs=len(pairs), min_gap_cycles=round(gap, 1), idx_after_prev_layer_att=nxt,
               examples=[dict(idx=[round(p[0][0], 1), round(p[0][1], 1), p[0][2]], att=[round(p[1][0], 1), round(p[1][1], 1), p[1][2], p[1][3]])
                         for p in pairs[:8]],
               verdict='NO OVERLAP: shared ks (one stream at a time) costs no rate' if not pairs else
                       'OVERLAP: one-stream-at-a-time serialises key and KV streams')
    o = ROOT / 'results/arch/svc_stream_overlap_20261010.json'
    o.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: v for k, v in out.items() if k not in ('idx_after_prev_layer_att',)}, indent=1))
    print('IDX after prev-layer ATT:', nxt)


if __name__ == '__main__':
    main()
