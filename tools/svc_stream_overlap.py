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
    out['ds_mtp'] = ds_mtp(d, recs, rg)
    out['qwen'] = qwen()
    o = ROOT / 'results/arch/svc_stream_overlap_20261010.json'
    o.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['ds_mtp'], indent=1)); print(json.dumps(out['qwen'], indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ('idx_after_prev_layer_att',)}, indent=1))
    print('IDX after prev-layer ATT:', nxt)


def gaps_of(s, recs, ex):
    idx = [(s['start'][i], s['end'][i]) for i, (k, *_) in enumerate(ex) if recs[k].unit == 'IDX' and recs[k].op == 'INDEX']
    att = [(s['start'][i], s['end'][i]) for i, (k, *_) in enumerate(ex) if recs[k].unit == 'ATT' and recs[k].op in ('QK', 'PV')]
    ov = sum(1 for i in idx for a in att if i[0] < a[1] and a[0] < i[1])
    g = min((max(a[0] - i[1], i[0] - a[1]) for i in idx for a in att), default=None)
    return len(idx), len(att), ov, g


def ds_mtp(d, recs, rg):
    """DS MTP (DSpark verify, ds_mtp_kernels.py): every verify column runs SERIAL launches (swapin, one layer body, swapout;
    a launch starts when the previous one's last record ended: t_launch += total_cycles), so a stream of one launch never
    meets a stream of another; the open question is the gap INSIDE one layer launch.  The MTP layer body is the ds_native
    layer lowering made position-generic (hgi-1010/h 86c4a0b84), so each layer of the committed DS program is scheduled
    here as its own launch (S2, the approved cost) at the verify positions; the real kernel image needs the V4.1
    checkpoint (ds_mtp_kernels sim), not run here."""
    import hgi_sim.ds_sw_seq_pricing as P_
    layers = sorted({r.layer for r in recs if r.unit == 'IDX' and r.op == 'INDEX'})
    rows, worst = [], None
    for L in layers:
        body = [r for r in recs if r.layer == L]
        for pos in (1024, 65536, DT.POS):
            cf = P_.SeqCost(d['ops'], body, rg, c=2, hc_g22=True)
            s = T.schedule(body, pos, 'S2', cost_fn=cf)
            ex = T.expand(body, pos)
            ni, na, ov, g = gaps_of(s, body, ex)
            rows.append(dict(layer=L, pos=pos, idx=ni, att=na, overlaps=ov, min_gap=None if g is None else round(g, 1),
                             launch_cycles=round(s['total_cycles'], 1)))
            if g is not None and (worst is None or g < worst):
                worst = g
    return dict(method='per-layer launch (serial launches)', layers_with_idx_index=layers, cases=rows,
                overlapping=sum(r_['overlaps'] for r_ in rows), min_gap_cycles=None if worst is None else round(worst, 1))


def qwen():
    from hgi_sim import qwen_compiler as QC
    from hgi_sim import dflash as D
    cfg = json.loads((ROOT / 'compiler/models/qwen3-8b/config.json').read_text())
    dcfg = json.loads((ROOT / 'compiler/models/qwen3-8b-dflash-b16/config.json').read_text())
    md = QC.qwen_params(cfg)
    res = {}
    recs = QC.program(QC.Geometry(cfg, 8192), md, cfg['num_hidden_layers'])
    from hgi_sim import dflash_timing as DTm
    s = T.schedule(recs, 8191, 'S2', cost_fn=DTm.make_cost('spec', False))
    res['qwen_ar_P8191'] = dict(zip(('idx_index', 'att', 'overlaps', 'min_gap'), gaps_of(s, recs, T.expand(recs, 8191))))
    for B in (16,):
        g = D.DGeom(cfg, dcfg, 8192, B)
        recs = D.step_program(g, md, timing_pos=8192 - B)
        from hgi_sim import dflash_timing as DTm
        s = T.schedule(recs, 8192 - B, 'S2', cost_fn=DTm.make_cost('spec', False))
        res[f'qwen_dflash_b{B}'] = dict(zip(('idx_index', 'att', 'overlaps', 'min_gap'), gaps_of(s, recs, T.expand(recs, 8192 - B))))
    return res


if __name__ == '__main__':
    main()
