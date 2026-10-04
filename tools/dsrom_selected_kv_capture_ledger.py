#!/usr/bin/env python3
"""Selected S81/RD64 physical obligations; consumes owners, never searches stages."""
import argparse
import hashlib
import json
import math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_selected_kv_capture_ledger_20261004/inputs'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def return_inventory(active_pairs, native):
    if active_pairs!=2417 or native['parameters']['RD']!=64:
        raise ValueError('selected active-pair RD64 contract required; no depth lever')
    roots=128;nodes=2*active_pairs-roots
    node_bits=2*64*65+66;root_bits=128*(65+66)
    storage=(nodes*node_bits+roots*root_bits)*.37908/.5/1e6
    mapped=native['actual_mapping']
    full_nodes=nodes*mapped['FF50_component_reservation_um2']/1e6
    roots_storage=roots*root_bits*.37908/.5/1e6
    return dict(active_pairs=active_pairs,RD=64,ROOTD=128,roots=roots,nodes=nodes,
                storage_bits=nodes*node_bits+roots*root_bits,
                existing_FF50_storage_reservation_mm2=storage,
                complete_node_FF50_projection_mm2=full_nodes,
                root_storage_only_mm2=roots_storage,
                complete_node_plus_root_storage_mm2=full_nodes+roots_storage,
                unmatched_logic_delta_mm2=full_nodes+roots_storage-storage,
                native_node_local_port_bits=mapped['port_bits'],
                source_native_mapping=native['source_commit'],
                qualification='TT_NATIVE_COMPONENT_AREA_ONLY; NO SSFF/PG/CLOCK/ROUTE',
                root_logic_mapped=False,area_delta_applied=False,
                containment='Maxwell must match node storage replacement and residual/fixed rectangle union before any additional debit or credit')


def selected_capacity(rows):
    # Accept only owner's per-die quantities; no uniform per-user state transfer.
    if len(rows)!=324 or len({r['die'] for r in rows})!=324:
        raise ValueError('complete selected324 rank-die capacity inventory required')
    if {(r['stage'],r['rank']) for r in rows}!={(s,r) for s in range(81) for r in range(4)}:
        raise ValueError('exact selected stage/rank identity required')
    out=[]
    for row in rows:
        stacks=row['stacks']
        if stacks not in (1,4) or type(stacks) is not int:raise ValueError('actual selected stack allocation required')
        if row['batch']!=216 or row['context']!=1048576:raise ValueError('batch216/1M owner quantities required')
        quantities=[row[k] for k in ('state_bytes_per_user','other_live_bytes','usable_bytes_per_stack')]
        if any(type(v) is not int or v<0 for v in quantities) or quantities[2]==0:
            raise ValueError('integer actual source byte inventory required')
        need=216*quantities[0]+quantities[1];available=stacks*quantities[2]
        out.append(dict(die=row['die'],stage=row['stage'],rank=row['rank'],stacks=stacks,
                        required_bytes=need,available_bytes=available,
                        headroom_bytes=available-need,fits=need<=available))
    return dict(rows=out,all_fit=all(r['fits'] for r in out),rank_stacks=sum(r['stacks'] for r in out),
                head_stacks='not inferred; owner must supply separate head inventory')


def model(base=BASE,capacity=None):
    def load(n):return json.loads((base/n).read_text())
    origins=load('origins.json')
    for n,pin in origins.items():
        if sha(base/n)!=pin['sha256']:raise ValueError('source pin changed: '+n)
    selected=load('selected.json');area=selected['decision']['area']
    if area['stages']!=81 or area['pairs']!=2417 or 'ragged RD64' not in selected['decision']['build']:
        raise ValueError('Claude selected S81/raggedRD64 required')
    capture=load('capture.json'); stages={}
    for name,s in capture['stages'].items():
        if sum(s['bank_depths'])!=s['exact_FF_seats'] or s['write_ports']!=len(s['bank_depths']):
            raise ValueError('Nash finite bank capacity mismatch')
        if s['exact_FF_record_bits']!=s['exact_FF_seats']*s['maximum_record_write_width_per_bank']:
            raise ValueError('finite capture payload dimensions mismatch')
        stages[name]=dict(exact_seats=s['exact_FF_seats'],record_bits=s['exact_FF_record_bits'],
                         control_bits=s['candidate_control_bits'],bank_depths=s['bank_depths'],
                         independent_write_ports=s['write_ports'],write_bits_per_edge=s['raw_write_bits_per_edge'],
                         record_write_width_bits=s['maximum_record_write_width_per_bank'],
                         scalar_read_records_per_edge=1,scalar_drain_edges=s['exact_FF_seats'],
                         historical_stage_identity_bits=s['control_allocation']['stage'],
                         required_selected_stage_identity_bits=math.ceil(math.log2(81)),
                         stage_identity_join='7 bits if this field identifies array stage0..80; otherwise Nash must bind the local namespace explicitly, not silently truncate',
                         scalar_drain_ports_are_not128_read_ports=True,
                         area_proxy_FF50_all_reset_upper_storage_mm2=s['physical_cell_count_lower_bound_FF']*.37908/.5/1e6,
                         area_proxy_excludes=['mutable protection','mux/decode','PG','clock','routing'],
                         selected_phase_count_bound=False,replication_count=None)
    r=dict(schema='DSROM_SELECTED_KV_CAPTURE_LEDGER_V1',status='SELECTED_SOURCE_LEDGER_CAPACITY_JOIN_PENDING',
           input_sha256={n:sha(base/n) for n in origins},source_origins=origins,
           selected=dict(stages=81,rank_dies=324,total_dies=368,pairs_per_rank_die=2417,
                         BF_pairs=519,selected_screen_mm2=area['die_mm2'],indexer_projection_copies='EVERY rank; no canonical-owner multicast',
                         indexer_extra_area_credit_mm2=0,screen_is_not_actual_die_fit=True),
           return_inventory=return_inventory(2417,load('return_native.json')),
           finite_capture=stages,source_capture_ports=capture['source_ports'],
           selected_capture_occupancy_and_consumer_deadlines=None,
           selected_KV_capacity=None,KV_stack_count_adopted=None,
           matched_area_delta_applied_mm2=0,physical_launch_allowed=False,
           missing=['Claude/Arendt S81 exact service-home/state/reserve inventory with all-rank indexer projections',
                    'Nash selected ragged2417 phase-to-bank writer occupancy and accepted drain deadlines',
                    'Maxwell root logic and once-only native-node/storage/residual/fixed containment'],
           original_files_edited=False)
    if capacity is not None:
        if capacity['selected_commit']!=origins['selected.json']['source_commit'] or capacity['selected_record_sha256']!=origins['selected.json']['sha256']:
            raise ValueError('capacity bound to another partition')
        if not capacity.get('source_files'):raise ValueError('actual capacity source closure required')
        for p in capacity['source_files']:
            path=Path(p['path'])
            if not path.is_absolute() or sha(path)!=p['sha256']:raise ValueError('capacity source changed')
        r['selected_KV_capacity']=selected_capacity(capacity['rank_dies'])
        r['capacity_source_files']=capacity['source_files']
        r['status']='SELECTED_KV_CAPACITY_MODEL_PASS_OTHER_GATES_HELD' if r['selected_KV_capacity']['all_fit'] else 'FAIL_SELECTED_KV_CAPACITY'
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--actual-capacity',type=Path);a=p.parse_args()
    r=model(capacity=json.loads(a.actual_capacity.read_text()) if a.actual_capacity else None)
    if a.actual_capacity:r['actual_capacity_manifest_sha256']=sha(a.actual_capacity)
    with a.out.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    raise SystemExit(r['status']=='FAIL_SELECTED_KV_CAPACITY')
