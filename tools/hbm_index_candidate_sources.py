#!/usr/bin/env python3
"""Bind actual HBM scored streams/held identity to the native candidate boundary.

This is a source/program adapter, not a score generator or replacement oracle.
It refuses the unimplemented TP96 rank-major final-gather ordering conversion.
"""
import argparse
import hashlib
import json
from pathlib import Path
from hbm_index_candidate_model import final_source

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['rtl/hbm_accel/index/ot_hbm_accel_index_candidate.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_sel_cand.sv', 'rtl/hdc/v41x/ot_hdc_v41x_sel.sv',
    'rtl/hdc/v41x/ot_hdc_v41x_sel_slice.sv', 'rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv']


def bind_candidate(frame, quarters, *, k=2048):
    for name, width in [('job',32), ('gen',4), ('position',20), ('rank',7)]:
        if not isinstance(frame.get(name), int) or not 0 <= frame[name] < 1 << width:
            raise ValueError('actual held native tuple required: ' + name)
    if frame['rank'] >= 96 or not frame.get('held_valid') or len(quarters) != 4 or not 1 <= k <= 2048:
        raise ValueError('held TP96 frame / four quarters / runtime candidate count required')
    previous = -1
    count = 0
    for q, beats in enumerate(quarters):
        if not beats or any(bool(b['last']) != (t == len(beats)-1) for t,b in enumerate(beats)):
            raise ValueError('each actual quarter must close exactly once, including empty quarter')
        for beat in beats:
            ids, vals, lv = beat['global_ids'], beat['scores_bf16'], beat['lane_valid']
            if any(len(v) != 16 for v in (ids,vals,lv)):
                raise ValueError('actual SL16 scored beat required')
            for b in range(2):
                base = b*8
                valid = [j for j in range(8) if lv[base+j]]
                if valid != list(range(len(valid))):
                    raise ValueError('each block has a valid prefix, never sparse arbitrary lane grouping')
                if valid:
                    idx = ids[base]
                    if idx % 8 or idx // 8 % 96 != frame['rank']:
                        raise ValueError('literal globally owned block boundary required')
                    if len(valid)<8 and not beat['last']:
                        raise ValueError('only final quarter beat may have a partial block')
                    for j in valid:
                        gid = ids[base+j]
                        if gid != idx+j or not previous < gid <= frame['position']:
                            raise ValueError('global ID order/extent; no local ordinal relabel')
                        value = vals[base+j]
                        if not 0 <= value < 65536 or value & 0x7f80 == 0x7f80 and value & 0x7f:
                            raise ValueError('BF16 non-NaN actual score required')
                        previous = gid
                        count += 1
    return dict(module='ot_hbm_accel_index_candidate', parameters=dict(ENABLE=1,Q=4,SL=16,IWP=20,K=2048,AW=10),
                held_frame=dict(frame), candidate_k=k, actual_keys=count,
                newest_global_block=frame['position']//8, newest_owner=(frame['position']//8)%96,
                input_quarters=quarters, source_order_preserved=True,
                release='parent holds native frame through actual output-last and SRAM/replay drain',
                memory='four real synchronous 1024x68 line stores, one read and one write per quarter',
                fault_on_overflow='rep_req/ovf propagate; parent may replay actual retained scores',
                reference_activation_operands=False, physical_qualified=False)


def bind_final(rows, *, producer_source):
    if not producer_source:
        raise ValueError('actual hardware canonical gather producer required')
    contract = final_source(rows)
    # Validation never creates sorted/relabelled data. Existing selector needs
    # an architecture-owned producer of this actual order before execution.
    contract.update(producer_source=producer_source,
        consumer_source='rtl/chip/ot_coll_topk_merge.sv', source_order_preserved=True,
        borrowed_clock_credit=False, native_execution_qualified=False)
    return contract


def source_pins():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args=parser.parse_args()
    if args.output.exists():
        raise SystemExit('preserve existing evidence')
    operands=json.loads(args.input.read_text())
    record=bind_candidate(operands['held_frame'], operands['quarters'], k=operands.get('candidate_k',2048))
    record['source_pins']=source_pins()
    args.output.write_text(json.dumps(record,indent=2)+'\n')
