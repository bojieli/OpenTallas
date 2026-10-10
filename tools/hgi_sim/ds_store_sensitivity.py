#!/usr/bin/env python3
"""Retiming sensitivity for full-shape G24 STORE evidence on the earlier native ROW_GATHER DAG.

The earlier program represents ROW_GATHER as one surrogate operation. Replace its old single
full-bandwidth STORE term with every measured c2 group spill plus the K/64 selected-row chunks.
This prices serialized traffic inside that surrogate and preserves its external S2 overlap.
It is an analytical sensitivity, not a native G24 trace or a measured whole-token rate.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
from hgi_sim import ds_native_timing as DT, ds_sw_seq_pricing as S, timing as T


class StoreCost(S.SeqCost):
    def __init__(self, *args, measured, **kwargs):
        super().__init__(*args, c=2, hc_g22=True, **kwargs)
        self.measured = measured

    def base(self, r, dyn, L):
        cycles, grade, how = super().base(r, dyn, L)
        if r.unit == 'COLL' and r.op == 'ROW_GATHER':
            entry = self.log[(r.layer, r.tag)]
            p = entry['parts']
            K, M = entry['K'], p['M']
            if K % 64:
                raise ValueError('Unmeasured selected chunk shape: K must be divisible by64')
            spill = ((M + 1) // 2) * self.measured[0]['transaction_cycles']
            selected = K // 64 * self.measured[1]['transaction_cycles']
            cycles = cycles - p['last_store'] + spill + selected
            entry.update(cycles=round(cycles, 1), store_scope='measured full shapes; serialized inside ROW_GATHER surrogate')
            p.update(previous_last_store=p.pop('last_store'), group_spill_store=spill, selected_order_store=selected)
            return cycles, 'measured-store+surrogate-model', 'G24 current STORE sensitivity'
        return cycles, grade, how


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--program', type=Path, required=True)
    a.add_argument('--run', type=Path, required=True)
    a.add_argument('--measurement', type=Path, required=True)
    a.add_argument('--out', type=Path, required=True)
    args = a.parse_args()
    m = json.loads(args.measurement.read_text())
    if m['verdict'] != 'PASS':
        raise ValueError('STORE exactness gate must pass')
    d, recs = DT.load(args.program)
    recs = T.rebuild_waits(recs)
    rg = {x['layer']: s for x in json.loads(args.run.read_text())['results'] for s in x.get('row_gather', [])}
    out = {}
    for name, cf in [('historical_approved_c2_g22', S.SeqCost(d['ops'], recs, rg, c=2, hc_g22=True)),
                     ('measured_store_serial_surrogate_sensitivity', StoreCost(d['ops'], recs, rg, measured=m['cases']))]:
        schedule = T.schedule(recs, DT.POS, 'S2', cost_fn=cf)
        out[name] = dict(cycles=round(schedule['total_cycles'], 1), tok_s=round(S.CLK/schedule['total_cycles'], 1),
                         n_races=len(schedule['races']), row_gather=[dict(layer=k[0],tag=k[1],**v) for k,v in cf.log.items() if v['op']=='ROW_GATHER'])
        print(name, out[name]['cycles'], out[name]['tok_s'], flush=True)
    record = dict(schema='opentallas.ds_store_sensitivity.v1', generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  method=__doc__, limitations=['Earlier native ROW_GATHER surrogate DAG, not emitted G24 software descriptor DAG',
                  'Serialized STORE costs within surrogate; no double buffering or speculative inter-record overlap',
                  'LOAD remains optimistic full bandwidth; SU/SFU/ATT production service calibration unresolved',
                  'No new hardware closure and no measured full-token rate'],
                  inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.program,args.run,args.measurement)},
                  store_source_commit=m['source_commit'], result=out)
    args.out.write_text(json.dumps(record,indent=2)+'\n')

if __name__ == '__main__':
    main()
