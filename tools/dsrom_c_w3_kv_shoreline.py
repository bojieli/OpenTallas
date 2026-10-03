#!/usr/bin/env python3
"""Scenario C W3: provisional allocation, then exact W2 map joins. Model only."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'results/uarch/dsrom_c_w3_kv_shoreline_20261003/inputs'
SCAN = {2,8,14,20,24,28,32,36}
CONTEXTS = ('1048576','200000')


def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def number(v, zero=False):
    if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v < 0 or (not zero and v==0):
        raise ValueError('finite source quantity required')
    return v


def capacity(state, reserve, stacks, usable, batch=216):
    for v in (state,reserve): number(v,zero=True)
    number(usable)
    if type(stacks) is not int or stacks<1: raise ValueError('literal stack count required')
    needed = batch*state+reserve
    return dict(batch=batch, state_bytes_per_user=state, reserve_bytes=reserve,
                required_bytes=needed, usable_bytes=stacks*usable,
                headroom_bytes=stacks*usable-needed, fits=needed<=stacks*usable)


def shoreline(stacks, phy_area, package_edge):
    # Ledger credit remains held until W4 replaces the inherited debit.
    return dict(stacks=stacks, PHY_area_mm2_assumed=stacks*phy_area,
                historical_PHY_frontage_mm=stacks*8.5,
                technology_package_keepout_frontage_mm=stacks*package_edge,
                saved_vs_four_PHY_mm2_assumed=(4-stacks)*phy_area,
                freed_vs_four_historical_PHY_mm=(4-stacks)*8.5,
                freed_vs_four_package_keepout_mm=(4-stacks)*package_edge,
                area_credit_applied=False, placement_qualified=False)


def actual_map(mapping, usable, bandwidth, phy_area, edge):
    if mapping.get('schema')!='DSROM_C_W2_W3_MAP_V1' or mapping.get('kind')!='actual_W2_map':
        raise ValueError('actual source-enrolled W2 map required')
    commit=mapping.get('source_commit','')
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('full frozen W2 source commit required')
    if not mapping.get('source_files'): raise ValueError('W2 state/service source closure required')
    for pin in mapping['source_files']:
        path=Path(pin['path'])
        if not path.is_absolute() or digest(path)!=pin['sha256']:
            raise ValueError('W2 source closure changed')
    stages=mapping['stages']; ranks=mapping['ranks_per_stage']
    if type(stages) is not int or stages<1 or ranks!=4:
        raise ValueError('PAIR1 stage inventory and TP4 required')
    rows=mapping['rank_dies']; heads=mapping['head_dies']
    if len(rows)!=stages*ranks or len(heads)!=8:
        raise ValueError('complete rank/head inventory required')
    allrows=rows+heads
    if len({r['die'] for r in allrows})!=len(allrows): raise ValueError('duplicate die')
    if {(r['stage'],r['rank']) for r in rows}!={(s,r) for s in range(stages) for r in range(4)}:
        raise ValueError('missing/duplicate stage-rank')
    owned=set()
    for row in rows:
        layers=row['layers']
        if len(layers)!=len(set(layers)): raise ValueError('duplicate layer within die')
        for layer in layers:
            if type(layer) is not int or layer<0 or layer>=43 or (layer,row['rank']) in owned:
                raise ValueError('layer/rank ownership ambiguous')
            owned.add((layer,row['rank']))
    if owned!={(layer,rank) for layer in range(43) for rank in range(4)}:
        raise ValueError('complete released Flash layer/rank map required')
    results=[]; stages_us={ctx:{} for ctx in CONTEXTS}; latency_ok=True; capacity_ok=True
    for row in allrows:
        head=row in heads; stacks=4 if head or SCAN.intersection(row.get('layers',[])) else 1
        pcs=row['controller_pseudochannels_per_stack']
        if type(pcs) is not int or pcs<=0: raise ValueError('source per-stack controller inventory required')
        out=dict(die=row['die'],stacks=stacks,controller_pseudochannels=stacks*pcs,
                 shoreline=shoreline(stacks,phy_area,edge),contexts={})
        for ctx in CONTEXTS:
            data=row['contexts'][ctx]
            if data['batch']!=216: raise ValueError('batch216 service inventory required')
            cap=capacity(data['state_bytes_per_user'],data['non_state_reserve_bytes'],stacks,usable)
            capacity_ok &= cap['fits']
            transfers=data['transfers']
            if not transfers: raise ValueError('explicit HBM transfer inventory required')
            kinds={t['kind'] for t in transfers}
            required={'head_state'} if head else {'window_KV','row_gather'}
            if not required.issubset(kinds): raise ValueError('missing window/row/head transfer coverage')
            if not head and stacks==4 and not SCAN.isdisjoint(row['layers']) and 'index_scan' not in kinds:
                raise ValueError('missing scan traffic')
            service=0; transfer_results=[]
            for t in transfers:
                b=number(t['bytes_per_stage_service'],zero=True); fixed=number(t['fixed_latency_us'],zero=True)
                wire_us=b/(stacks*bandwidth)*1e6
                bound=wire_us<=fixed
                if not head and stacks==1: latency_ok &= bound
                # No unproved overlap discount on startup vs transfer time.
                service+=wire_us+fixed
                transfer_results.append(dict(kind=t['kind'],bandwidth_us=wire_us,
                                             fixed_latency_us=fixed,latency_bound=bound))
            stage_us=number(data['non_HBM_stage_us'],zero=True)+number(data['controller_service_us'],zero=True)+service
            out['contexts'][ctx]=dict(capacity=cap,transfers=transfer_results,stage_service_us=stage_us)
            if not head:
                old=stages_us[ctx].get(row['stage'],0)
                stages_us[ctx][row['stage']]=max(old,stage_us)
        results.append(out)
    busiest={}; busiest_ok=True
    for ctx in CONTEXTS:
        head_bound=number(mapping['head_bound_us'][ctx])
        value=max(stages_us[ctx].values()); busiest_ok &= value<=head_bound
        busiest[ctx]=dict(busiest_stage_us=value,head_bound_us=head_bound,fits=value<=head_bound)
    return dict(source_commit=mapping['source_commit'],source_files=mapping['source_files'],
                allocation=results,total_stacks=sum(r['stacks'] for r in results),
                gates=dict(actual_map=True,batch216_capacity=capacity_ok,
                           one_stack_latency_bound=latency_ok,busiest_stage=busiest_ok),
                busiest=busiest,stage_service_model='Rank dies operate in parallel; fixed latency, transfer, controller and non-HBM times serially charged within each die')


def run(root=ROOT, mapping=None):
    paths=[root/BASE/'scenario_c.json',root/BASE/'scenario_c_producer.py.snapshot',
           root/'configs/hardware/technology.json']
    c=json.loads(paths[0].read_text()); tech=json.loads(paths[2].read_text())['hbm']['hbm3e']
    usable=tech['stack_capacity_bytes']['value']*.9
    provisional=[]
    for ctx in CONTEXTS:
        state=c['kv_sizing']['per_context'][ctx]['per_user_on_busiest_rank_die_B']
        provisional.append(dict(context=int(ctx),capacity=capacity(state,0,1,usable),
                                reserve_status='UNKNOWN: zero is arithmetic lower bound only'))
    result=dict(schema='DSROM_C_W3_KV_SHORELINE_V1',status='PROVISIONAL_MODEL_GATES_HELD',
                input_sha256={str(p.relative_to(root)):digest(p) for p in paths},
                scenario_source_commit='3a0c114d853e86999d0b6df894afc64846f6aff7',
                producer_sha256=digest(__file__),stages_provisional=73,
                provisional_allocation=dict(scan_rank_dies=32,other_rank_dies=260,head_dies=8,
                                            stacks_model_only=32*4+260+8*4),
                usable_stack_bytes_model=usable,usable_fraction_assumed=.9,
                provisional_capacity=provisional,
                non_scan_shoreline=shoreline(1,tech['phy_area_mm2_per_stack']['value'],tech['stack_beachfront_mm']['value']),
                PHY_savings_array_mm2_assumed_range=[260*3*x for x in (8,10,15)],
                gates=dict(actual_map=False,batch216_capacity=None,one_stack_latency_bound=None,busiest_stage=None),
                adopted_420_stack_claim=False,physical_launch_allowed=False,
                delta_vs_C_adopted=dict(tok_s=0,mm2=0,kW=0,dies=0),
                W4_credit='Held until explicit rectangle/debit replacement; never subtract from inherited debit here')
    if mapping is not None:
        result['actual_map_model']=actual_map(mapping,usable,tech['stack_bandwidth_bytes_s']['value'],
                                              tech['phy_area_mm2_per_stack']['value'],tech['stack_beachfront_mm']['value'])
        result['gates']=result['actual_map_model']['gates']
        result['status']='ACTUAL_MAP_MODEL_GATES_PASS_NOT_ADOPTED' if all(result['gates'].values()) else 'ACTUAL_MAP_MODEL_GATES_FAIL'
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path,required=True)
    p.add_argument('--w2-map',type=Path); a=p.parse_args()
    r=run(mapping=json.loads(a.w2_map.read_text()) if a.w2_map else None)
    if a.w2_map: r['input_sha256'][str(a.w2_map)]=digest(a.w2_map)
    with a.out.open('x') as f: json.dump(r,f,indent=2,sort_keys=True); f.write('\n')
    return int(r['status']=='ACTUAL_MAP_MODEL_GATES_FAIL')


if __name__=='__main__': raise SystemExit(main())
