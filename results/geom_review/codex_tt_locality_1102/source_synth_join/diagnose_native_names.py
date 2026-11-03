"""Finite retained old/new census diagnosis; proposes no accepted aliases or constraints."""
from pathlib import Path
import json,sys,re,collections
P=Path('/work/producer');sys.path.insert(0,str(P/'tools/die_plan/tt_regional_origin'))
from native_inventory import parse_dump,read,L,source_alias_prefix
inputs=json.loads((P/'actual_source_readset.json').read_text())['inputs'];libs=[Path(p) for p in inputs if '.lib' in p];models=L.read_liberty(libs)
def census(path):
 cells,pins,*_=parse_dump(path)
 return {n:c for n,c in cells.items() if models.get(c['master'],{}).get('ff')},pins
new,np=census(P/'actual_synth.tsv');old,op=census(Path('/old/actual_old_reference.tsv'))
intent=read(P/'full_ff_intent_HELD.json.gz');expected={r['model_name']:r for r in intent['targets']};source={n:t for n,t in expected.items() if t['source_identity']};unchanged=set(expected)-set(source)
normalized=collections.defaultdict(list)
for n in new:normalized[n.replace('\\','')].append(n)
source_matches={}
for n,t in source.items():
 prefix=source_alias_prefix(t)
 source_matches[n]=[v for k,vs in normalized.items() if re.fullmatch(re.escape(prefix)+r'(?:\[0\])?\$_[A-Z0-9_]+_',k) for v in vs]
source_native={v for vs in source_matches.values() for v in vs};missing=sorted(unchanged-set(new));extra=sorted(set(new)-unchanged-source_native)
def anon(n):return bool(re.fullmatch(r'_\d+_',n))
def qs(n,pins):return tuple(sorted((pin,q['net']) for pin,q in pins[n].items() if q['direction']=='OUTPUT'))
qindex=collections.defaultdict(list)
for n in new:qindex[qs(n,np)].append(n)
unique_q=[];ambiguous_q=[];no_q=[]
for n in missing:
 if n not in old:no_q.append(n);continue
 candidates=qindex[qs(n,op)]
 if len(candidates)==1:
  nn=candidates[0];unique_q.append(dict(old=n,new=nn,master_same=old[n]['master']==new[nn]['master'],output_nets=qs(n,op),input_nets_literal_same=op[n]==np[nn],old_pins=op[n],new_pins=np[nn]))
 elif candidates:ambiguous_q.append(dict(old=n,new=candidates))
 else:no_q.append(n)
common=unchanged&set(new);footprint_changed=[n for n in common if new[n]['master']!=expected[n]['master'] or abs(new[n]['width_um']-expected[n]['width_um'])>1e-6 or abs(new[n]['height_um']-expected[n]['height_um'])>1e-6]
result=dict(status='DIAGNOSIS_ONLY_NO_ALIAS_AUTHORITY',actual_old_ff=len(old),actual_new_ff=len(new),model_ff=len(expected),missing_count=len(missing),missing_anonymous=sum(map(anon,missing)),missing_named=sum(not anon(n) for n in missing),extra_count=len(extra),extra_anonymous=sum(map(anon,extra)),source_aliases=source_matches,literal_common=len(common),common_master_footprint_changed=footprint_changed,missing=missing,extra=extra,unique_same_output_net_candidates=unique_q,ambiguous_same_output_net_candidates=ambiguous_q,no_same_output_net_candidate=no_q,physical_release=False,source_correspondence_proved=False)
dindex=collections.defaultdict(list)
def ins(n,p):return tuple(sorted((pin,q['net'],q['signal']) for pin,q in p[n].items() if q['direction']=='INPUT'))
for n in new:dindex[ins(n,np)].append(n)
result['same_literal_inputs_candidates']={n:dindex[ins(n,op)] for n in missing if n in old}
result['fresh_master_changes']=[dict(name=n,old_master=expected[n]['master'],fresh_master=new[n]['master'],old_width_um=expected[n]['width_um'],fresh_width_um=new[n]['width_um'],old_height_um=expected[n]['height_um'],fresh_height_um=new[n]['height_um']) for n in footprint_changed]
(P/'native_name_diagnosis.json').write_text(json.dumps(result,indent=1)+'\n')
print('NATIVE_NAME_DIAGNOSIS',json.dumps({k:v for k,v in result.items() if k in ('actual_old_ff','actual_new_ff','model_ff','missing_count','missing_anonymous','missing_named','extra_count','extra_anonymous','literal_common')}), 'uniqueQ',len(unique_q),'noQ',len(no_q),'source18',sum(len(v)==1 for v in source_matches.values()),flush=True)
