#!/usr/bin/env python3
"""Metadata-only R43 RF alias diagnosis; no provider guard change or execution."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import h4_hbm_pc10_r41_lineage as lineage

BASE=Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_r43_rf_lifetime_diagnosis_20261002'
PIN='3679f36acf778538165ddccdd6eddfb05a17c3759e0f1c1ffa9d0bc9c58c8376'
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def inputs():
    raw=(BASE/'input_manifest.json').read_bytes()
    if sha(raw)!=PIN:raise ValueError('manifest pin')
    out={}
    for r in json.loads(raw)['inputs']:
        p=(BASE/r['archive']).resolve()
        if not p.is_relative_to(BASE.resolve()):raise ValueError('archive origin')
        b=p.read_bytes()
        if len(b)!=r['bytes'] or sha(b)!=r['sha256']:raise ValueError('source pin')
        out[p.name]=b
    return out

def refs(x,version,path=()):
    if isinstance(x,dict):
        for k,v in x.items():yield from refs(v,version,path+(k,))
    elif isinstance(x,list):
        for i,v in enumerate(x):yield from refs(v,version,path+(i,))
    elif x==version:yield path

def unused_output(native,version,pc):
    paths=list(refs(native,version))
    return bool(paths) and all(len(p)>=4 and p[:2]==('instructions',pc) and p[2] in ('writes','source_outputs') for p in paths)

def slots(homes,indices):
    return {(homes[i]['SM'],s) for i in indices if homes[i]['home']['class']=='RF'
            for s in range(homes[i]['home']['slot_first'],homes[i]['home']['slot_first']+homes[i]['home']['vectors'])}

def build():
    s=inputs();load=lambda n:json.loads(gzip.decompress(s[n]))
    native=load('bound_native.json.gz');homes=load('bound_homes.json.gz')
    original,expected_homes,expected_native=lineage.regenerate()
    if canonical(homes)!=canonical(expected_homes) or canonical(native)!=canonical(expected_native):
        raise ValueError('exact R41 lineage required before lifetime diagnosis')
    if canonical(homes[:len(original)])!=canonical(original):raise ValueError('original RF prefix changed')
    calls=[e['record'] for e in load('numeric_calls.json.gz')]
    seen=Counter((r['PC'],r['rank'],r['template']) for r in calls)
    expected=Counter()
    for op in native['instructions'][:9]:
        for owned in op['rank_bindings']:
            if owned.get('empty_owned_extent'):continue
            for t in ([b['template'] for b in owned['buffer_programs']] if owned.get('buffer_programs') else [owned['template']]):
                expected[op['pc'],owned['rank'],t]+=1
    if seen!=expected:raise ValueError('all actual PC0..8 native calls required')
    observations=load('observed_outputs.json.gz')
    if any(e.get('byte_exact') is not True for e in observations):raise ValueError('publication comparison incomplete')
    observed={(e['identity']['PC'],e['identity']['rank'],e['identity']['version']) for e in observations}
    required={(op['pc'],owned['rank'],w['version']) for op in native['instructions'][:9]
              for owned in op['rank_bindings'] if not owned.get('empty_owned_extent') for w in op['writes']}
    if observed!=required:raise ValueError('all actual PC0..8 output observations required')
    last={r['version']:op['pc'] for op in native['instructions'] for r in op['reads']}
    live={};released=[]
    for pc in range(9):
        for r in calls:
            if r['PC']==pc:
                for v in r['published_versions']:live[v,r['rank']]=pc
        for r in native['instructions'][pc]['reads']:
            if last[r['version']]==pc:
                for key in list(live):
                    if key[0]==r['version']:del live[key]
                released.append(r['version'])
    by={}
    for i,h in enumerate(homes):
        if h['home']['class']=='RF':
            for rank in h['rank_group']:by.setdefault((h['version'],rank),[]).append(i)
    w=native['instructions'][9]['writes'][0];collisions=[];dead_cache={}
    for rank in range(64):
        proposed=slots(homes,by[w['version'],rank])
        for (v,r),birth in live.items():
            if r!=rank:continue
            old_indices=by.get((v,r),[]);hit=proposed&slots(homes,old_indices)
            if hit:
                if (v,birth) not in dead_cache:dead_cache[v,birth]=unused_output(native,v,birth)
                dead=dead_cache[v,birth]
                home_retire=sorted({homes[i]['retire_pc'] for i in old_indices})
                collisions.append(dict(rank=rank,proposed_version=w['version'],retained_version=v,
                    overlapping_SM_slots=[list(x) for x in sorted(hit)],
                    overlapping_mirror_byte_ranges=[dict(SM=sm,slot=slot,copy=copy,
                        base=(sm*2+copy)*262144+slot*512,bytes=512)
                        for sm,slot in sorted(hit) for copy in (0,1)],birth_pc=birth,
                    full_program_last_read=last.get(v),declared_home_retire_PCs=home_retire,
                    unused_output_proved_from_all_native_references=dead,
                    all_output_comparisons_before_retirement=(birth,rank,v) in observed,
                    release_after_complete_PC= birth if dead and home_retire==[birth] else None))
    if not collisions or any(not c['unused_output_proved_from_all_native_references'] for c in collisions):
        raise ValueError('missing proof of unused output collision')
    driver=s['driver.py'].decode();provider=s['provider.py'].decode();prefix=s['prefix.py'].decode()
    for token in ('for read in op[\'reads\']:',"self.last_use[read['version']]==op['pc']",'self.provider.retire_operation'):
        if token not in driver:raise ValueError('exact existing retire source contract')
    for token in ('if proposed&occupied:raise ValueError',"if self._leased(version):raise ValueError('version still leased')"):
        if token not in provider:raise ValueError('exact alias/lease guard source')
    if 'self.provider.release_views' not in prefix:raise ValueError('actual views release source')
    return dict(schema='HBM_R43_RF_LIFETIME_DIAGNOSIS_V1',failure_reason=json.loads(s['failure_receipt.json'])['reason'],
        exact_original_prefix_and_R41_extension=True,PC9_PC10_homes_changed=False,
        actual_completed_native_calls=len(calls),actual_PC_counts=dict(sorted(Counter(r['PC'] for r in calls).items())),
        output_observations=len(observations),next_publication_PC=9,collisions=collisions,
        retained_collision_versions=sorted({c['retained_version'] for c in collisions}),
        diagnosis='Unused produced RF output has no reads entry; engine retirement iterates reads only, so release_version never called for this dead-on-production version.',
        legal_recycle_prerequisites=['all producer rank calls and exact publication/comparison receipts complete',
            'producer operation retire receipt reports pending_obligations0 and released source consumers',
            'full-program reads/provider/auxiliary references prove output unused',
            'release_version validates generation and no outstanding view lease',
            'actual physical sink/write/ACK and reverse lease obligations drained before physical reuse'],
        recommended_software_change='Add explicit unused-produced-output retirement after successful whole producer-operation retirement, alongside existing last-read retirement. Preserve alias and lease guards; do not delete locations at attempted overwrite.',
        provider_modified=False,alias_guard_weakened=False,numerical_rerun=False,
        actual_failed_runtime_repaired=False,physical_retirement_measured=False,hardware_admitted=False,whole_token_latency=None)

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args()
    raw=canonical(build())+b'\n'
    if a.verify:
        if a.out.read_bytes()!=raw:raise ValueError('exact diagnosis replay')
    else:a.out.write_bytes(raw)
    print('PASS exact metadata diagnosis; preserved alias guard; no execution/rate credit')
if __name__=='__main__':main()
