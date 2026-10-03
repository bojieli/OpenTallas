#!/usr/bin/env python3
"""One recovery-bound correction of the completed channel-aligned feed.
Remove the minimum required assertion-feed stages; reprice every new/raw and
controlled reset pin at SS/FF. No new map, optional topology or timing exception.
"""
import collections
import gzip
import json
import math
from pathlib import Path
import qwen_rom_native_release_audit as K
J=K.J;R=K.R;M=K.M
OUT=Path('results/uarch/qwen_rom_channel_aligned_context_20261002')


def record(name):
    path=R.ROOT/OUT/name
    raw=path.read_bytes() if path.exists() else gzip.decompress(path.with_suffix('.json.gz').read_bytes())
    return json.loads(raw)


def allocation():
    b=K.allocation();g=json.loads(gzip.decompress((R.ROOT/OUT/'allocation-r2.json.gz').read_bytes()))
    b.g=g;b.placements=g['cell_sites']
    for row in g['source_clock_sinks']:b.net['cells'].setdefault(row['instance'],dict(type=row['cell'],connections={}))
    b.bit=1+max(x for c in g['added_primitive_cells'].values() for bs in c['connections'].values() for x in bs if isinstance(x,int))
    return b


def price():
    b=allocation();g=b.g;prior=record('model-r2.json');phase=g['assert_phase_construction']
    rows=prior['timing']['ss']['raw_reset_checks'];upper=phase['cycle']*J.H.PERIOD+791.5025333333334
    excess=max(r['interval_ps'][1] for r in rows)-upper
    minimum=phase['minimum_characterized_stage_delay_ps'];trim=math.ceil(max(0,excess)/minimum)
    if not trim or trim>=phase['derived_stages']:raise ValueError('not the named finite-feed recovery correction')
    removed=[]
    for _ in range(trim):
        #Last phase-buffer feeds the original assertion source isolation BUF.
        edge=next(e for e in g['wire_edges'] if e['driver'].startswith('native_assert_phase_') and e['sink'].startswith('native_assert_source_'))
        name=edge['driver'];incoming=next(e for e in g['wire_edges'] if e['sink']==name)
        outgoing=[e for e in g['wire_edges'] if e['driver']==name]
        if len(outgoing)!=1:raise ValueError('cannot bypass a branching assertion stage')
        g['wire_edges'].remove(edge);g['wire_edges'].remove(incoming)
        b.edge(incoming['driver'],edge['sink'],edge['pin'],edge['length_um'])
        del g['added_primitive_cells'][name];del g['nominal_node_coordinates_um'][name];del g['cell_sites'][name]
        removed.append(name)
    timing=J.checks(b);stages=K.internal_stages(b)
    result=json.loads(json.dumps(prior));result['schema']='QWEN_KV7_CHANNEL_ALIGNED_RELEASE_R3'
    result['timing']=timing;result['stage_and_ACK_audit']=stages
    result['buffer_cells']-=trim;result['complete_reserved_cell_area_um2']-=trim*.10206
    result['field1536_cell_area_mm2']=result['complete_reserved_cell_area_um2']*1536/1e6
    result['source_phase_trim']=dict(SS_recovery_excess_ps=excess,minimum_characterized_stage_delay_ps=minimum,
        required_stage_trim=trim,removed_buffers=removed,remaining_stages=phase['derived_stages']-trim,
        no_raw_sync_FF_exception=True,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25)
    result['channel_parent_model_sha256']=R.sha(Path('results/uarch/qwen_rom_kv_channel_shoreline_20261002/model-r5.json'))
    result['complete_reserved_cell_area_scope']='Allocated mapped subtotal and explicit primitives; ACK receiver data/hold and whole source launch integration remain unpriced. Not a completed physical provider.'
    result['cuts']=prior['cuts']
    #The bypass stays within its source region; prove no new cut crossing.
    coords=g['nominal_node_coordinates_um'];new=g['wire_edges'][-1]
    assert J.G.region(coords[new['driver']])==J.G.region(coords[new['sink']])
    return result,g


if __name__=='__main__':
    root=R.ROOT/OUT
    if (root/'model-r3.json.gz').exists():raise ValueError('preserve verdict')
    result,g=price()
    raw=R.canon(result);(root/'model-r3.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    (root/'allocation-r3.json.gz').write_bytes(gzip.compress(R.canon(g),mtime=0))
    print(dict(stage_trim=result['source_phase_trim'],area=result['complete_reserved_cell_area_um2'],
        corners={c:dict(raw_FF=t['raw_reset_failures'],controlled=t['controlled_reset_failures'],skew=t['nominal_same_source_clock_scenarios'],
            setup=result['stage_and_ACK_audit'][c]['setup_failures'],hold=result['stage_and_ACK_audit'][c]['hold_failures'],ACK_load=result['stage_and_ACK_audit'][c]['ACK_out_of_characterization']) for c,t in result['timing'].items()}),flush=True)
