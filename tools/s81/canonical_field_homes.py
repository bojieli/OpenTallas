#!/usr/bin/env python3
"""Join every literal canonical FIELD allocation to emitted pair/root/CFG homes.

This producer emits actual FIELD identities. It cannot assign SU operations,
select runtime expert IDs, invent native programmes, or qualify changed views.
"""
import argparse,bisect,collections,gzip,hashlib,json,os
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--canonical',type=Path,required=True);ap.add_argument('--matrices',type=Path,required=True);ap.add_argument('--bindings',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--reuse-fragments',type=Path);ap.add_argument('--mapping-verdict',type=Path,help='Exact allocator verdict declaring complete literal matrix count; mandatory for a changed topology');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 canonical=json.load(gzip.open(a.canonical,'rt'));pairs={p['pair_id']:p for p in canonical['pairs']};npairs=canonical['counts']['field_pairs'];nstages=canonical['counts']['stages'];assert set(pairs)==set(range(npairs))
 dies={(r['stage'],r['rank']):r['die_id'] for r in canonical['rank_programme_bindings']}
 assert set(dies)=={(s,r) for s in range(nstages) for r in range(4)} and len(set(dies.values()))==4*nstages
 if a.mapping_verdict:
  verdict=json.loads(a.mapping_verdict.read_text());assert verdict['decoder_matrix_capacity_PASS'] and not verdict['failures']
  expected_fragments=verdict['counts']['declarations'];assert expected_fragments==verdict['counts']['placed']
 else:
  assert (npairs,nstages,canonical['counts']['bf_pairs'])==(2417,81,519), 'changed allocator requires its mapping verdict'
  expected_fragments=46671
 groups=collections.defaultdict(list);phases=collections.Counter();fragments=0;plans=0;by_stage={}
 with gzip.open(a.matrices,'rt') as stream,(gzip.open(a.reuse_fragments,'rt') if a.reuse_fragments else gzip.open(a.out/'field_fragment_homes.jsonl.gz','wt')) as dest:
  for line in stream:
   m=json.loads(line);assert m['compiled_NP']==npairs;s=m['stage'];assert 0<=s<nstages;phase=phases[s];phases[s]+=1;assert phase<1024
   identity=(m['layer'],m.get('original_alias',m['alias']));entry=dict(fragment=fragments,layer=m['layer'],alias=m['alias'],source_stage=s,source_phase=phase,source_matrix_sha256=hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest(),rank_slices=m['rank_slices'],physical_die_ids=[dies[s,r] for r in m.get('physical_owner_ranks',[0,1,2,3])],allocated_pair_ids=[],root_ids=[],actual_engine_refs=[],native_qualified=False)
   used=set();roots=set()
   for run in m['plans']:
    segment,pair,first,n,stride,start,words=run;assert pair in pairs and pair not in used;used.add(pair);p=pairs[pair];root=p['root_id'];roots.add(root)
    assert all((first+j*stride)%128==root for j in range(n))
    names={i['name'] for i in p['actual_children']};assert f'e{pair}' in names and f's{pair}' in names and all(f'c{pair}_{j}' in names for j in range(7));plans+=1
   entry['allocated_pair_ids']=sorted(used);entry['root_ids']=sorted(roots);entry['actual_engine_refs']=[dict(pair_id=p,engine=f'e{p}',sequencer=f's{p}',cfg7=[f'c{p}_{j}' for j in range(7)]) for p in sorted(used)]
   if a.reuse_fragments:assert entry==json.loads(next(dest)), 'stale FIELD fragment checkpoint'
   else:dest.write(json.dumps(entry,separators=(',',':'))+'\n')
   groups[identity].append(dict(fragment=fragments,stage=s,phase=phase,alias=m['alias']));fragments+=1
  if a.reuse_fragments:assert next(dest,None) is None, 'extra FIELD fragment checkpoint'
 if a.reuse_fragments:os.link(a.reuse_fragments,a.out/'field_fragment_homes.jsonl.gz')
 assert fragments==expected_fragments and fragments>0 and set(phases).issubset(set(range(nstages)))
 missing=[];field_nodes=0;home_refs=0
 with gzip.open(a.bindings,'rt') as stream,gzip.open(a.out/'source_field_operation_homes.jsonl.gz','wt') as dest:
  for line in stream:
   b=json.loads(line)
   if not b.get('address_bound'):continue
   field_nodes+=1;choices=[]
   for c in b['phase_choices']:
    key=(b['layer'],c['alias']);allocated=groups.get(key)
    if not allocated:missing.append(dict(node=b['node'],layer=b['layer'],alias=c['alias']));continue
    choices.append(dict(source_alias=c['alias'],expert=c.get('expert'),fragments=allocated));home_refs+=len(allocated)*4
   dest.write(json.dumps(dict(node=b['node'],template_sha256=b['template_word_sha256'],canonical_choices=choices,required_ranks=[0,1,2,3],runtime_selection_bound=False if b.get('selector_slot') is not None else None,native_qualified=False),separators=(',',':'))+'\n')
 report=dict(schema='opentallas.s81.actual-field-homes.v1',status='FIELD_ALLOCATION_JOIN_PASS' if not missing else 'FIELD_ALLOCATION_JOIN_FAIL',qualified=False,source_sha256={str(p):sha(p) for p in (a.canonical,a.matrices,a.bindings,*([a.mapping_verdict] if a.mapping_verdict else []))},fragments=fragments,plans=plans,source_field_nodes=field_nodes,rank_fragment_home_references=home_refs,phase_counts={s:phases[s] for s in range(nstages)},stages_without_FIELD_fragments=[s for s in range(nstages) if not phases[s]],missing=missing,unimplemented=['SU/nonfield operation assignment and actual native leaf hierarchy',f'{4*nstages} native programmes/core epochs/durations','runtime expert selection and producer/consumer calendars','actual pin/clock/TT/FF/DRC/throughput qualification'])
 (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('phase_counts','missing','source_sha256')}));return int(bool(missing))
if __name__=='__main__':raise SystemExit(main())
