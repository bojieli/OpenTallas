#!/usr/bin/env python3
"""Retiming an emitted native G24 program with measured STORE shapes and an explicit byte inventory.

LOAD bandwidth retains the native model budget. Only the measured current-mover FP32 row-gather
STORE shapes are replaced. Other STOREs retain their estimate and are listed as uncalibrated.
This is composed timing, not a measured production token or a closure claim.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
from hgi_sim import ds_native_timing as DT, timing as T


class MeasuredStoreCost(DT.NativeCost):
    def __init__(self, *args, measurement, **kwargs):
        super().__init__(*args, **kwargs)
        if measurement['verdict'] != 'PASS':
            raise ValueError('STORE exactness evidence must pass')
        cases = {c['name']: c for c in measurement['cases']}
        self.points = {(512, 96, 1024): cases['slot_gather_c2']['record_cycles'][0],
                       (512, 64, 512): cases['selected_chunk']['record_cycles'][0]}

    def store_measurement(self, r):
        if r.unit != 'DMA' or r.op != 'STORE':
            return None
        a, o = r.desc['A'], r.desc['O']
        if not r.tag.startswith('row_gather.') or a.fmt != 'FP32' or o.fmt != 'FP32' or o.stride != 2048:
            return None
        return self.points.get((a.n, a.m, a.stride))

    def __call__(self, r, dyn, L):
        cycles = self.store_measurement(r)
        if cycles is not None:
            return cycles, 'measured_full_shape', 'current DMA mover STORE, real SECDED VM and acknowledged KLAT40 lane'
        return super().__call__(r, dyn, L)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('program', 'run', 'measurement', 'out'):
        ap.add_argument('--'+name, type=Path, required=True)
    a = ap.parse_args()
    m = json.loads(a.measurement.read_text())
    d, recs = DT.load(a.program)
    recs = T.rebuild_waits(recs)
    rg = {x['layer']: s for x in json.loads(a.run.read_text())['results'] for s in x.get('row_gather', [])}
    DT.apply_dyn_counts(recs, rg)
    cf = MeasuredStoreCost(d['ops'], recs, row_gather=rg, measurement=m)
    inventory = []
    for r in recs:
        if r.unit == 'DMA' and r.op == 'STORE':
            src, dst = r.desc['A'], r.desc['O']
            measured = cf.store_measurement(r)
            if r.tag.startswith('row_gather.') and measured is None:
                raise ValueError(f'Unmeasured row gather STORE shape: {r.tag}, {src}')
            inventory.append(dict(layer=r.layer, tag=r.tag, bytes_per_execution=dst.n*dst.m*4,
                                  source_words_per_row=src.n, rows=src.m, source_stride_words=src.stride,
                                  destination_stride_bytes=dst.stride, measured_cycles=measured,
                                  scope='static descriptor; row_gather.store records execute ceil(M/2) times'))
    s = T.schedule(recs, DT.POS, 'S2', cost_fn=cf)
    result = dict(cycles=round(s['total_cycles'],1), tok_s=round(1.2e9/s['total_cycles'],1),
                  records_executed=s['records_executed'], n_races=len(s['races']), races=s['races'][:5], per_unit=s['per_unit'])
    record = dict(schema='opentallas.ds_native_store_timing.v1', generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  method=__doc__, result=result, store_inventory=inventory, row_gather_dynamic_counts=rg,
                  inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.program,a.run,a.measurement)},
                  store_source_commit=m['source_commit'], limitations=['Other STORE shapes retain model estimates',
                  'No source staging or consumer overlap invented beyond emitted waits and measured record service',
                  'LOAD remains full-bandwidth budget, not a STORE qualification',
                  'Production SU/SFU/ATT service and full context physical closure remain separate gates'])
    a.out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(result), flush=True)

if __name__ == '__main__':
    main()
