#!/usr/bin/env python3
"""Extract actual symbolic owner routes for the shared budget/calendar owner.

These are source/address identities, not an implementation of remote delivery.
No hop latency or whole-token rate is inferred from stage distances.
"""
import argparse, collections, json
from pathlib import Path
import dsrom_full_owner_compiler as C

ROOT=Path(__file__).resolve().parents[1]


def extract(journal,readback,contract,out):
    journal=journal.resolve();readback=readback.resolve();contract=contract.resolve();out=out.resolve()
    verified=json.loads(readback.read_text());ctrl=json.loads(contract.read_text())
    if not verified['all40_all384_placed']:raise ValueError('full owner assignment prerequisite')
    homes={int(k):v for k,v in verified['provider_homes'].items()};layers={}
    for L in range(40):layers[L]={'layer':L,'immutable_HE_CROM_home':homes[L],'dense_matrix_owners':[],
        'expert_stage_IDs':{},'matrix_phase_count_by_owner':collections.Counter()}
    for m in C.readrows(journal/'assignments.jsonl.gz'):
        if m['stage'] is None:raise ValueError('unallocated owner')
        d=layers[m['layer']];s=m['stage'];d['matrix_phase_count_by_owner'][s]+=1
        if m['expert'] is None:
            d['dense_matrix_owners'].append({'alias':m['alias'],'tensor':m['tensor'],'format':m['format'],
                'rows_per_rank':m['rows'],'K_per_rank':m['K'],'rank_slices':m['rank_slices'],
                'matrix_stage':s,'source_key':m['key'],
                'conditional_LAT8_issue_cycle_model':m['issue_cycles_LAT8_condition'],
                'issue_model_not_actual_connected_measurement':True})
        else:
            e=m['expert'];old=d['expert_stage_IDs'].setdefault(e,s)
            if old!=s:raise ValueError('expert triple split across stages')
    for L,d in layers.items():
        if set(d['expert_stage_IDs'])!=set(range(384)):raise ValueError('expert coverage')
        bystage=collections.defaultdict(list)
        for e,s in d['expert_stage_IDs'].items():bystage[s].append(e)
        d['expert_stage_ranges']=[{'stage':s,'first_expert':min(es),'last_expert':max(es),'count':len(es)} for s,es in sorted(bystage.items())]
        d['matrix_stage_IDs']=sorted(d['matrix_phase_count_by_owner'])
        d['one_owner_frontend_VMEM_or_remote_matrix_delivery_selected']=False
    out.mkdir(parents=True,exist_ok=False)
    report={'schema':'opentallas.dsrom.owner.route-handoff.v1','candidate':'DS4096-TP4-S58-PAIR1',
        'same58_stages_TP4_3375_active_compiledNP4096_NBF724':True,
        'capacity':verified['capacity_verdict'],'conservation':verified['conservation'],
        'compiled_field':verified['compiled_field'],'uniform_config':ctrl['uniform_control'],
        'layer_owners':list(layers.values()),'all4778_descriptor_calendar_composition_ready':False,
        'required_joint_budget_inputs':['Source-bound compiledNP/q+BF physical frames and required RNE/WAKE abstract, all unused compiled sites charged.',
            'Fixed services/route/clockPG debits with receipts; do not infer an active-only reticle fit.',
            'Source configuration macro/storage, actual lookup and broadcast fanout; prove original frame inclusion before counting incremental area.',
            'Actual full-program producer/consumer VM lifetimes and request/return paths across these owner homes.',
            'Price selected-expert golden-order request/return crossings, dense/shared chains, and immutable provider traffic separately from stage hops.',
            'Preserve dedicated table/head provider capacities and bind their actual ports.'],
        'no_whole_token_latency_from_stage_distance':True,'no_adoption_or_partition_selection':True,
        'no_RTL_PR_or_payload':True,'compiler_sha256':C.sha(Path(__file__).read_bytes()),
        'input_sha256':{str(p.relative_to(ROOT)):C.sha(p.read_bytes()) for p in [journal/'assignments.jsonl.gz',readback,contract]}}
    (out/'model.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'layer_owners':40,'expert_owners':40*384,'selected_partition':False}),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--journal',type=Path,required=True);p.add_argument('--readback',type=Path,required=True);p.add_argument('--contract',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    extract(a.journal,a.readback,a.contract,a.out)
