"""Pure provenance/coverage check on existing emitted SU records; no RTL simulation."""
import argparse
import copy
import json
from pathlib import Path
from hbm_layer_vehicle import layer_images as LI
from hbm_layer_vehicle import pv_probability_rows_1340 as PV


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--emission', type=Path, required=True)
    p.add_argument('--fixtures', type=Path, required=True)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    a = p.parse_args()
    manifest = json.loads((a.emission/'manifest.json').read_text())
    producer = next(r for r in manifest['records'] if r['tag']=='attend.bf16_p' and 'programme' in r)
    record = json.loads((a.emission/'images'/f"r{producer['i']:03d}_su"/'record.json').read_text())
    raw = next(r for r in json.loads((a.fixtures/'records.json').read_text())['records']['0'] if r['op']=='ATT.PV')
    args = dict(logical_words=LI.desc_addrs(raw['desc']['A']), producer_entry=producer,
                contract=json.loads(a.contract.read_text()), source_root=a.source)
    plan = PV.plan(producer_record=record, **args)
    altered = copy.deepcopy(record)
    for drain in altered['expect']:
        drain['value'] = [(int(v)^0xffffffff) if v is not None else None for v in drain['value']]
    assert PV.plan(producer_record=altered, **args)==plan, 'planner consumed comparison values'
    absent = copy.deepcopy(record)
    first = args['logical_words'][0]
    for drain in absent['expect']:
        for lane, word in enumerate(drain.get('words', [])):
            if word==first:
                drain['mask'] &= ~(1<<lane)
    try:
        PV.plan(producer_record=absent, **args)
    except ValueError as e:
        assert 'producer join open' in str(e)
    else:
        raise AssertionError('missing actual producer drain accepted')
    assert plan['probability_M_events']==0 and not plan['full_ATT_PV_lowered']
    assert all(p['tested_command_interval']==256 for p in plan['pages'])
    print(json.dumps(dict(status='PASS_PURE_ADDRESS_PROVENANCE_ONLY', rows=plan['probability_rows'],
        pages=plan['pages_required'],fixed_input_kernel_stream_edges=plan['fixed_input_kernel_stream_edges'],
        values_ignored=True,missing_drain_rejected=True,hardware_executed=False)))


if __name__=='__main__':
    main()
