"""Actual intended HN backend directed data edges against measured-clock cut candidate.
This backend is a NEW source candidate, not the current B1-selected top. Clock
coupon excludes actual wrapper FF census; groups are not adopted clock regions.
"""
import collections,hashlib,json,re,sys
from pathlib import Path
PLAN,GRAPH,CLOCK,OUT=map(Path,sys.argv[1:5]);P=json.load(open(PLAN/'die_plan.json'));G=json.load(open(GRAPH));C=json.load(open(CLOCK));OUT.mkdir(parents=True,exist_ok=True);t=P['partition_types']['q_sm3'];hard={h['inst']:h for h in t['hard_cores']};clock={r['instance']:r for r in C['core_taps']}
pat=re.compile(r'g_c\[(\d+)\]\.g_p\[(\d+)\]\.u_pair\.u_h([ns])$')
def inst(path):
 m=pat.fullmatch(path);assert m,path;c,p,d=m.groups();return f'u_sm_t{p}{c}_{d}'
lookup={};mapping=[]
for path,r in G['half_instances'].items():
 n=inst(path);assert hard[n]['module']==r['master'];assert n in clock
 pins=json.load(open(PLAN/hard[n]['pins_file']));lookup[n]={p['name']:p for p in pins};mapping.append({'source_path':path,'plan_instance':n,'master':r['master'],'clock_port':clock[n]['port'],'clock_pin':clock[n]['clock_pin'],'region_candidate':clock[n]['adaptive_clock_node']})
assert len(mapping)==32

def xy(n,port,b):
 ps=lookup[n];p=ps.get(f'{port}[{b}]',ps.get(port)if b==0 else None)
 if not p:return None
 x,y=p['x'],p['y'];h=hard[n];w,z=h['outline_um'];o=h.get('orient','R0')
 if o in ['MY','R180']:x=w-x
 if o in ['MX','R180']:y=z-y
 return [round(x+h['origin_um'][0],6),round(y+h['origin_um'][1],6)]
rows=[];counts=collections.Counter();missing=[];crosspairs=collections.Counter()
for e in G['edges']:
 a,b=inst(e['source']),inst(e['sink']);ar,br=clock[a]['adaptive_clock_node'],clock[b]['adaptive_clock_node'];cross=ar!=br;maxlen=0.;miss=0;over=0
 for bit in e['bit_pairs']:
  aa=xy(a,e['source_port'],bit['source_bit']);bb=xy(b,e['sink_port'],bit['sink_bit'])
  if aa is None or bb is None:
   miss+=1
   if len(missing)<40:missing.append({'source':a,'source_port':e['source_port'],'source_bit':bit['source_bit'],'sink':b,'sink_port':e['sink_port'],'sink_bit':bit['sink_bit'],'source_resolved':aa is not None,'sink_resolved':bb is not None})
   continue
  L=sum(abs(x-y)for x,y in zip(aa,bb));maxlen=max(maxlen,L);over+=L>405+1e-6
 width=len(e['bit_pairs']);counts['edges']+=1;counts['bits']+=width;counts['cross_edges']+=cross;counts['cross_bits']+=width*cross;counts['missing_bits']+=miss;counts['direct_over405_bits']+=over
 if cross:crosspairs[(ar,br)]+=width
 rows.append({'source':a,'source_path':e['source'],'source_port':e['source_port'],'sink':b,'sink_path':e['sink'],'sink_port':e['sink_port'],'width':width,'source_region_candidate':ar,'sink_region_candidate':br,'crossing':cross,'source_clock':clock[a]['port'],'capture_clock':clock[b]['port'],'resolved_bits':width-miss,'missing_bits':miss,'max_direct_manhattan_um':round(maxlen,6)if width>miss else None,'direct_over405_bits':over,'same_n_s_pair':a[:-1]==b[:-1]})
rep={'schema':'hbm.hn.actual-data-clock-region-inventory.v1','status':'NEW HN BACKEND CANDIDATE; not current B1 source or physical region adoption','source_graph_sha256':hashlib.sha256(GRAPH.read_bytes()).hexdigest(),'physical_plan_sha256':hashlib.sha256((PLAN/'die_plan.json').read_bytes()).hexdigest(),'counts':dict(counts),'total_hn_internal_Q_bits':G['total_half_internal_q_bits'],'residual_parent_Q_bits':G['residual_parent_q_bits'],'mapping':mapping,'directed_region_bits':[{'launch':a,'capture':b,'bits':w}for(a,b),w in sorted(crosspairs.items())],'edges':rows,'missing_pin_examples':missing,'holds':['Four groups bound only34entry measured clock coupon; actual source wrapper/FF clock coverage must close.','Actual intended32HNhalves and804768Qbits are INTERNAL to cores; zero parentQ, not804k new frameFF.','Direct source data edges crossing regions require CA source/model/compiler materialization and >=100ps TT/FF margin with canonical clock/AOCV/droop model.','No endpoint matched by nearest name or data inferred from tap pairs. Missing typed pins block exact geometry.','Current selected B1 front/BE/XS/boot/compiler ABI differs; HNsource candidate must be composed and qualified first.']}
(OUT/'inventory.json').write_text(json.dumps(rep,indent=1)+'\n');print(json.dumps({'counts':dict(counts),'region_bits':rep['directed_region_bits'],'cross_n_s_groups':sum(r['crossing']and r['same_n_s_pair']for r in rows)},indent=1))
