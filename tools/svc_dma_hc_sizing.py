#!/usr/bin/env python3
"""HC weight-fetch sizing for the svc DMA stream v2 ([svc] hbm-phys 2026-10-10, owner HBM rule: bandwidth must not be the
bottleneck, no fixed % of peak -> derive the minimum from the designed schedule).

Schedule = the approved DS AR path (tools/hgi_sim/ds_sw_seq_pricing.py approved_path_c2_g22: G22 HC rows, ROW_GATHER
c = 2) on the committed program (results/arch/hgi_programs_20261010/inputs: rank-0 program + 1M run).  HC_MIX_ROWS (G22, 1 row / die) needs one HC
weight row a record: K = 4 x 5120 = 20,480 FP32 = 81,920 B (spec G22 HC weight-set layout; d's striped fetch moves the
same row).  The rows are static (layer weights), so the fetch for record k+1 can start when record k starts (VM double
buffer of 2 rows); the window is the scheduled start-to-start gap.  On demand (no prefetch) the row must arrive inside
the record's own price.  Overlap: the rest of the die's HBM traffic in the same windows is bounded by the IKS stream
(404.5 B/cycle a stack while IDX.INDEX runs, measured 326b960d4) and the record fetch (0.867 B/cycle)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from hgi_sim import timing as T  # noqa: E402
from hgi_sim import ds_native_timing as DT  # noqa: E402
import hgi_sim.ds_sw_seq_pricing as P  # noqa: E402

ROW_B = 20480 * 4
SECTOR = 32
STACK_PEAK = 792.0          # B/cycle a stack (HBM3e PHY at 1.2 GHz, svc DMA v2 gate reference)
IKS_B = 404.5               # B/cycle a stack while IDX.INDEX streams keys (326b960d4)
CPF_B = 0.867               # record fetch, B/cycle a die (budget_audit hbm_ds_cp_fetch)


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
    hc = sorted((s['start'][i], s['end'][i]) for i, (k, *_) in enumerate(ex) if recs[k].unit == 'HC')
    idx = sorted((s['start'][i], s['end'][i]) for i, (k, *_) in enumerate(ex)
                 if recs[k].unit == 'IDX' and recs[k].op == 'INDEX')
    total = s['total_cycles']
    gaps = [b[0] - a[0] for a, b in zip(hc, hc[1:])]
    price = [e - st for st, e in hc]
    # prefetch: row k+1 streams during [start_k, start_k+1); worst window = the smallest gap
    need_prefetch = ROW_B / min(gaps)
    need_mean = ROW_B * len(hc) / total
    need_demand = ROW_B / min(price)
    # overlap: does any prefetch window intersect an IDX.INDEX key stream?  (then IKS takes 404.5 B/cycle a stack)
    olap = sum(1 for a, b in zip(hc, hc[1:]) if any(i0 < b[0] and i1 > a[0] for i0, i1 in idx))
    stripes = 4
    per_stack_prefetch = need_prefetch / stripes
    out = dict(schema='opentallas.svc_dma_hc_sizing.v1', source=dict(program=str(prog.relative_to(ROOT)),
               run=str(run.relative_to(ROOT)), schedule='ds_sw_seq_pricing approved_path_c2_g22 (S2)',
               tool='tools/svc_dma_hc_sizing.py'),
               designed=dict(tok_s=round(1.2e9 / total, 1), token_cycles=round(total, 1), hc_records=len(hc),
                             hc_row_bytes=ROW_B, hc_bytes_per_token=ROW_B * len(hc)),
               hc_schedule=dict(min_start_gap=round(min(gaps), 1), mean_start_gap=round(sum(gaps) / len(gaps), 1),
                                min_record_price=round(min(price), 1), windows_overlapping_idx_index=olap),
               required=dict(
                   prefetch_one_row_ahead_B_per_cycle_die=round(need_prefetch, 2),
                   prefetch_sectors_per_cycle_die=round(need_prefetch / SECTOR, 3),
                   prefetch_B_per_cycle_stack_striped4=round(per_stack_prefetch, 2),
                   mean_B_per_cycle_die=round(need_mean, 2),
                   on_demand_B_per_cycle_die=round(need_demand, 1),
                   on_demand_sectors_per_cycle_die=round(need_demand / SECTOR, 1),
                   vm_staging_bytes=2 * ROW_B),
               overlap=dict(iks_B_per_cycle_stack=IKS_B, cp_fetch_B_per_cycle_die=CPF_B,
                            worst_stack_load_B_per_cycle=round(per_stack_prefetch + IKS_B, 1),
                            stack_peak_B_per_cycle=STACK_PEAK),
               sizing=dict(
                   rule='owner 10-10: bandwidth must not be the bottleneck, no fixed % of peak',
                   decision='prefetch one row ahead into a 2-row VM buffer (163,840 B): the window is the scheduled '
                            'HC start-to-start gap (min 3,440.5 cycles). On demand the row would have to arrive inside '
                            'the G22 row compute (48.3 of the 1,353.8-cycle record: 1,696 B/cycle = 53 sectors/cycle, '
                            'above the loader front and the VM wide write); prefetch removes it from the critical path',
                   lanes_per_stack_min_bandwidth=max(1, -(-int(per_stack_prefetch) // SECTOR)),
                   options=dict(
                       kport_existing=dict(
                           what='the loader native port that already reaches every stack (ot_hfd_loader_kport, bursts + '
                                'multi-outstanding, d8b1b836c): HC rows striped over the 4 stacks, prefetched one row '
                                'ahead by DMA.LOAD into the VM double buffer',
                           measured_B_per_cycle_stack={'NO8_RB16_RTT102': 4.287, 'NO8_RB16_RTT161': 2.888,
                                                       'NO8_RB32_RTT139': 6.461},
                           measured_source='rtl/hbm_accel/loader/service_native/run_kport_bench.sh (KPORT_GATE, '
                                           'loader_hgi c647a68b9 bench track)',
                           die_B_per_cycle_RB32=round(4 * 6.461, 2),
                           margin_RB32=round(4 * 6.461 / need_prefetch, 2),
                           note='RB 64 a stack doubles the in-flight window (rate ~ RB x 32 / RTT): ~2x margin; no svc '
                                'segment change, no new die nets. Needs the DMA mover (kport lane 2) on the native burst '
                                '+ multi-outstanding protocol the CP fetch lane already uses (budget audit hbm_dma_load: '
                                'the mover is one sector a round trip today) -> hgi-1010 DMA owner'),
                       dma_v2_nl8=dict(
                           what='svc DMA stream v2, one lane per svc group (8 a stack, group-local 4:1 merge)',
                           B_per_cycle_stack=256, margin=round(4 * 256 / need_prefetch, 1),
                           cost='all 17 svc segments re-route with --dma; die nets 8 x 270 + 51 + 8 b a stack')),
                   recommendation='HC prefetch needs <= 0.74 sectors/cycle a die; the existing kport path (4 stacks, '
                                  'RB >= 32, better 64) covers it with no svc re-close. DMA v2 is not required for HC.'))
    p = ROOT / 'results/uarch/svc_dma_hc_sizing_20261010.json'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1) + '\n')
    print(json.dumps(out['required']), json.dumps(out['hc_schedule']), json.dumps(out['overlap']))


if __name__ == '__main__':
    main()
