"""Pure source layout replay, no payload, numerical execution or timing credit."""
import gzip,json
from pathlib import Path
from ds_hbm_unconsumed_retirement_r45 import retirement_plan
from ds_hbm_storage_home_binding_r41 import bind_storage
ROOT=Path(__file__).resolve().parents[1]


def replay(native,homes,manifest,*,retire_unconsumed):
    last={r['version']:o['pc'] for o in native['instructions'] for r in o['reads']}
    plan=retirement_plan(native,manifest,homes);live={};retired=[];released=[]
    for op in native['instructions'][:11]:
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            rank=owned['rank']
            for w in op['writes']:
                ix=[i for i in w['home_indices'] if rank in homes[i]['rank_group']]
                if homes[ix[0]]['home']['class']!='RF':continue
                slots={(homes[i]['SM'],s) for i in ix for s in range(homes[i]['home']['slot_first'],homes[i]['home']['slot_first']+homes[i]['home']['vectors'])}
                for (v,r),old in live.items():
                    if r==rank and v!=w['version'] and slots&old:
                        return dict(status='FAIL_SOURCE_RF_RESIDENCE',PC=op['pc'],rank=rank,writer=w['version'],retained=v,listed_last_use=last.get(v),overlap=[list(x) for x in sorted(slots&old)],retired_source_PCs=retired)
                live[w['version'],rank]=slots
        for rd in op['reads']:
            if last[rd['version']]==op['pc']:live={k:v for k,v in live.items() if k[0]!=rd['version']}
        if retire_unconsumed:
            for version in plan[op['pc']]:
                live={k:v for k,v in live.items() if k[0]!=version}
                released.append(dict(PC=op['pc'],version=version))
        retired.append(op['pc'])
    return dict(status='PASS_SOURCE_RF_RESIDENCE_ONLY',retired_source_PCs=retired,unconsumed_releases=released,actual_execution=False,physical_admission=False)


def regenerate():
    def load(path):return json.loads(gzip.decompress(path.read_bytes()))
    native=load(ROOT/'results/uarch/ds_hbm_storage_home_binding_r41_20261002/inputs/actual_native_c65.json.gz')
    D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002/inputs'
    manifest=load(D/'prefix_input_manifest.json.gz')
    native,homes,_,_=bind_storage(native,load(D/'actual_DeepSeek_homes.json.gz')['homes'],manifest)
    return dict(original=replay(native,homes,manifest,retire_unconsumed=False),
                candidate=replay(native,homes,manifest,retire_unconsumed=True))

if __name__=='__main__':print(json.dumps(regenerate(),sort_keys=True,indent=2))
