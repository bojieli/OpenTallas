"""Stream actual canonical FIELD declarations into native storage/root inventory.

No checkpoint reads, tensor computation, placement substitutes, phase-ID
truncation or runtime schedule estimates are admitted by this census.
"""
from pathlib import Path
import gzip,hashlib,json,argparse,bisect,collections
PINS={'matrix_map.jsonl.gz':'985a9ee7ea26d2a7bb1aebadc5151252836eacf8181e8794b1ef6d7819db0326','stage_map.json':'47ea9eb0ba0b404f629a4bc758d28d8ac1fe28dcb31de3e5816517fa1d097815','inventory.json':'0b8d8f6fddf7a427941b7a235aeb80e0ee370c51cafddba6427fa61d3ff99480'}


def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
 return h.hexdigest()


def inventory(base,out):
 base=Path(base);out=Path(out)
 for name,pin in PINS.items():
  if file_sha(base/name)!=pin:raise ValueError('actual released allocation changed:'+name)
 sm=json.loads((base/'stage_map.json').read_text());inv=json.loads((base/'inventory.json').read_text())
 if (inv['pairs_per_rank_die'],inv['BF_dual_pairs'],inv['TP'],len(sm['PHW_required_by_stage']))!=(2417,519,4,81):raise ValueError('full canonical source shape required')
 bounds=sm['region_bounds'];bf=set(sm['BF_site_IDs'])
 if bounds!=[r*2417//128 for r in range(129)] or len(bf)!=519:raise ValueError('real root/pair assignment changed')
 stages=[dict(stage=s,phase_records=0,max_rows=0,max_K=0,formats=collections.Counter(),layers=set(),pairs=set(),intervals=collections.defaultdict(list),source_digest=hashlib.sha256())for s in range(81)]
 declarations=0;plans=0
 with gzip.open(base/'matrix_map.jsonl.gz','rt')as f:
  for line in f:
   m=json.loads(line);s=m['stage'];r=stages[s]
   if m['compiled_NP']!=2417:raise ValueError('partial FIELD source')
   r['source_digest'].update(line.encode());r['phase_records']+=1;r['max_rows']=max(r['max_rows'],m['rows']);r['max_K']=max(r['max_K'],m['K']);r['formats'][m['format']]+=1;r['layers'].add(m['layer'])
   for segment,pair,first,n,stride,start,words in m['plans']:
    if not 0<=pair<2417 or not 0<=start<start+n*words<=8192:raise ValueError('native pair ROM capacity')
    if m['format']=='bf16' and pair not in bf:raise ValueError('BF source allocated onto q-only pair')
    r['pairs'].add(pair);r['intervals'][pair].append((start,start+n*words));plans+=1
   declarations+=1
 if declarations!=46671:raise ValueError('incomplete actual canonical matrix scope')
 summary=[]
 for r in stages:
  occupied=0;max_word=0;collisions=0
  for pair,spans in r['intervals'].items():
   spans.sort();last_end=-1
   for start,end in spans:
    if start<last_end:collisions+=1
    occupied+=end-start;max_word=max(max_word,end);last_end=max(last_end,end)
  if collisions:raise ValueError('actual source physical pair intervals overlap')
  summary.append(dict(stage=r['stage'],phase_records=r['phase_records'],PHW=sm['PHW_required_by_stage'][r['stage']],SAW_REQUIRED=None,layers=sorted(r['layers']),formats=dict(r['formats']),active_weight_pairs=len(r['pairs']),max_phase_rows=r['max_rows'],max_K=r['max_K'],occupied_superwords_per_leaf_bank=occupied,max_word_end=max_word,weight_interval_collisions=collisions,matrix_declaration_sha256=r['source_digest'].hexdigest(),physical_rank_dies=[d['die_id']for d in sm['rank_dies']if d['stage']==r['stage']]))
 result=dict(source_pins=PINS,stage_count=81,rank_count=4,physical_die_count=324,pairs_per_die=2417,BF_pairs_per_die=519,roots_per_die=128,BF_site_IDs=sorted(bf),region_bounds=bounds,pair_to_root=[bisect.bisect_right(bounds,p)-1 for p in range(2417)],matrix_declarations=declarations,plan_spans=plans,stages=summary,weight_macro_interface=dict(per_pair_macro_count=4,macro_rows=4096,macro_bits=274,total_macros_per_die=9668),native_global_calendar_qualified=False,physical_flight_edges=None,missing=['actual canonical fullshape die routing/phase profile','source-bound native phase/stream/CFG masks','native FIELD root/capture/VM slot/calendar integration'])
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=inventory(a.base,a.out);print(json.dumps({k:r[k]for k in ('stage_count','physical_die_count','matrix_declarations','plan_spans','native_global_calendar_qualified')}))
