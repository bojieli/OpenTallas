#!/usr/bin/env python3
"""HBM-REPRICE3: landed safe-design deltas plus physical controller bandwidth scenarios.

Primary bandwidth is the OLD production master (45.03 B/edge/SM, HBM-BW).
95.19 is an unqualified successor projection; 99 is the historical assumption.
Bank-latency budgets are conservative exposed estimates, not die-STA measurements.
"""
from __future__ import annotations
import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path
from hgi_sim import d4g_reprice_1019 as R
from hgi_sim import timing as T


def main():
    # Python3.14 defaults to forkserver, which drops run-time model patches.
    mp.set_start_method('fork', force=True)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=40)
    ap.add_argument('--bw', type=float, default=45.03)
    ap.add_argument('--only', default='')
    args = ap.parse_args()
    # Scope: preserve measurement grades separately from schedule exposure estimates.
    updates = {
        'hbm_bw': (args.bw, 'priced', 'SM, attention and DMA stream floor at measured per-SM bandwidth; incremental exposure over99', 'HBM-BW9e8fcf77e controller production stream'),
        'pg_cmd': (6, 'measured', '+6 slowest SU command region (+3 inner, +6 outer)', 'HBM-PGLG2 6799b58ee face relay'),
        'pg_operand': (11, 'measured', '+11 SU reduction operand; tree/control relative issue +10 unchanged', 'HBM-PGLG2 6799b58ee'),
        'pg_inject': (1, 'priced', '+1 SU VM read record conservatively exposes split-stream inject edge; only inject users pay physically', 'TW3-PGSTREAM 5ac202325; HBM-PGSTREAM-B unchanged edges'),
        'pg_fault': (0, 'measured', 'fault +2 serial is status only, no successful token latency', 'TW3-PGSTREAM'),
        'att_prog': (0, 'measured', '2048 words: 1019 attention + 152 matvec resident; one-op spans enabled', 'HBM-SMBUDGET main e248c89e7'),
        'att_desc': (0, 'measured', '256 token-resident relative descriptors; no rewrite', 'HBM-SMBUDGET main e248c89e7'),
        'sm_svc': (43 * 388 + 4, 'priced', 'fully exposed partial block granularity, worst layer 388 x43 + head4', 'HBM-SMBUDGET sm_svc_granularity.json'),
        'qwen_int8': (0, 'measured', 'INT8 path within price; opt-in successor, all9984 rows bit-exact', 'SMB-INT8 e592ae5d0; default-off die adoption owed'),
        'pvm_fold': (1, 'priced', '+1 per Qwen PV 128-token block per SM column; DS no fold', 'HBM-PVM-SAFE node0 publication F0+23 vs22; node1 unchanged'),
    }
    R.TERMS.update(updates)
    # PT_RED=80 corresponds to the existing model PT_EDGES=81 (includes output edge).
    # p3 lands reset and tree_cmd: retain 81 pending evidence of changed data completion.
    old = R.TERMS['pt_p2']
    R.TERMS['pt_p2'] = (81, old[1], old[2] + '; p3 PT_RED80 retained', old[3] + '; HBM-SAFE-PRETREE 9d56cae39')
    R.COMPOSED[:] = list(R.TERMS)
    original_rp = R.rp_added
    def rp_added(record, cost, knobs):
        if not hasattr(record, 'layer'):
            record.layer = 0
        extra = original_rp(record, cost, knobs)
        rp = knobs.get('rp', set())
        if 'pg_inject' in rp and R.Q.su_exec(record) and R._reads_vm(record):
            extra += 1
            R._add('pg_inject', 1)
        if 'pvm_fold' in rp and getattr(record, 'orig_op', f'{record.unit}.{record.op}') == 'ATT.PV' and R._att_T(record) is None:
            # Qwen P8192 /16 SMs =512 rows/SM = four128-row blocks.
            extra += 4
            R._add('pvm_fold', 4)
        if 'hbm_bw' in rp and record.unit in ('SM', 'ATT'):
            b = record.desc.get('B')
            if b is not None:
                try:
                    _, n, m, _, _ = T.eff(b, T.Dyn(8191), record.layer if isinstance(record.layer, int) else 0)
                    if record.unit == 'SM':
                        per_sm_bytes = n * (-(-m // 16)) * T.ESZ[b.fmt]
                    else:
                        per_sm_bytes = n * 128 * T.ESZ[b.fmt] / 16
                    stream_new = per_sm_bytes / args.bw
                    stream_old = per_sm_bytes / 99
                    # Maximum with the record's present unit work preserves compute hiding.
                    floor = max(0.0, max(cost + extra, T.first_access() + stream_new) - max(cost + extra, T.first_access() + stream_old))
                    extra += floor
                    R._add('hbm_bw', floor)
                except (KeyError, AttributeError):
                    raise
        if 'hbm_bw' in rp and record.unit == 'DMA' and record.op == 'LOAD':
            b = record.desc.get('A')
            if b is not None and b.space == 'HBM':
                _, n, m, _, _ = T.eff(b, T.Dyn(8191), record.layer if isinstance(record.layer, int) else 0)
                share = 4 if record.param & 1 else 1
                per_sm_bytes = n * m * T.ESZ[b.fmt] * share / 16
                floor = max(0.0, max(cost + extra, T.first_access() + per_sm_bytes / args.bw) -
                            max(cost + extra, T.first_access() + per_sm_bytes / 99))
                extra += floor
                R._add('hbm_bw', floor)
        return extra
    R.rp_added = rp_added
    original_terms = R.with_terms
    def with_terms(base, terms, **extra):
        extra['bigprog'] = True
        return original_terms(base, terms, **extra)
    R.with_terms = with_terms
    original_post = R.post_hoc
    def post_hoc(row, terms):
        ar, qw = original_post(row, terms)
        if 'sm_svc' in terms:
            ar += R.TERMS['sm_svc'][0]
        return ar, qw
    R.post_hoc = post_hoc
    # Measured rate propagates through timing and SM weights, not just attention.
    previous_bw = T.CAL['hbm']['bytes_per_cycle']['value']
    # Native DS costs are immutable snapshots, so explicit hbm_bw floor above is required.
    # Keep baseline calibration unchanged for reproducible attribution.
    # Current declared client budgets, including VM glue g4 +10 bank round trip.
    R.INFO_TERMS['gen2c_xload'] = (dict(SM_X=65/2), 'xload max RD_LAT55 plus g4 roundtrip10, half per stage', 'HBM-BANKLAT-XL + VMGLUE g4')
    R.INFO_TERMS['bl_coll'] = (dict(COLL_VM=84/2), 'COLL VM_RT74 + g4 roundtrip10', 'HBM-BANKLAT-COLL + VMGLUE g4')
    R.INFO_TERMS['bl_dma'] = (dict(VM_HBM=93/2), 'DMA lag83 + g4 roundtrip10', 'HBM-BANKLAT-DMA + VMGLUE g4')
    R.INFO_TERMS['bl_idx'] = (dict(idx=181, argmax=75), 'IDX171/rootctl65 + g4 roundtrip10; fully exposed upper bound', 'HBM-BANKLAT-IDX + VMGLUE g4')
    sys.argv = [sys.argv[0], '--out', str(args.out), '--jobs', str(args.jobs)]
    if args.only:
        sys.argv += ['--only', args.only]
    rc = R.main()
    doc = json.loads(args.out.read_text())
    doc['lane'] = 'HBM-REPRICE3'
    doc['bandwidth'] = dict(bytes_per_cycle_per_sm=args.bw, previous_die_bytes_per_cycle=previous_bw,
        measured_current_master=args.bw == 45.03, successor_not_physically_qualified=args.bw == 95.19,
        source='HBM-BW 9e8fcf77e: baseline45.03; production3seed95.19/95.69/95.25; successor capacity/SAFE closure outstanding; full4layer MR@88 FAIL24/66ops,37/154gos; L14 only PASS')
    doc['qualification'] = 'Provisional model price: current bandwidth measured; successor INT8/relative-service/safe tiles require die binding and physical closure. Bank pads are conservative fully exposed budgets, not measured die latency.'
    doc['record_0kq'] = {'ds_ar_tok_s': 1677.2, 'qwen_tok_s': 803.1}
    doc['banklat_projected'] = doc['table']['info_banklat_all']
    args.out.write_text(json.dumps(doc, indent=1) + '\n')
    return rc

if __name__ == '__main__':
    raise SystemExit(main())
