"""Unselected vector-provider stimulus/calendar from actual independent LOADs.

Within ONE owned window read bundle, date packets greedily with unique source
leaf/PC and destination(quad,bank), at most8 packets/date. All source anchors,
window fills/releases, descriptor resolution and ownership ordering stay fixed.
This assumes a NEW8path vector provider, count8 producer and perleafcommandports;
it is not current RTL, an installed calendar or a claimed optimal schedule.
"""
import argparse,collections,json
from pathlib import Path
from window_programme import compile_programme,validate


def packets(runs):
 queues=collections.defaultdict(lambda:collections.defaultdict(collections.deque))
 count=0;pc_counts=collections.Counter();bank_counts=collections.Counter();leaf_counts=collections.Counter();quads=set()
 for r in runs:
  s=r['route']['source_sector_start'];w=r['destination_word']
  for j in range(r['n']//8):
   sec=s+j;dst=w+8*j;pc=((sec>>2)^(sec>>7)^(sec>>12))&31;leaf=pc&7;dest=(dst>>16,(dst>>3)&7);quads.add(dest[0])
   queues[leaf][dest].append((r,sec,dst,pc));pc_counts[pc]+=1;bank_counts[dest]+=1;leaf_counts[leaf]+=1;count+=1
 return queues,count,pc_counts,bank_counts,leaf_counts,quads


def schedule(runs,output=None):
 qs,count,pcs,banks,leaves,quads=packets(runs);date=0;remaining=count;sample=[];maxwidth=0;checks=0;sample_quads=set()
 while remaining:
  used=set();vector=[]
  # Rotate priority to avoid a permanent leaf-order preference. This is a
  # concrete valid calendar, not a claim of minimum edge-coloring depth.
  for offset in range(8):
   leaf=(date+offset)&7
   if leaf not in qs:continue
   choices=[d for d,q in qs[leaf].items()if q and d not in used]
   if not choices:continue
   dest=max(choices,key=lambda d:(len(qs[leaf][d]),d));r,sec,dst,pc=qs[leaf][dest].popleft();used.add(dest);remaining-=1
   vector.append(dict(source_leaf=leaf,source_PC=pc,source_group=(pc>>3)&1,source_slot=(((sec>>7)&1)<<5)|(((sec>>12)&7)<<2)|(sec&3),destination_quad=dst>>16,destination_bank=(dst>>3)&7,destination_sector=dst>>3,first_VMword=dst,source_sector=sec,source_byte=sec*32,format=5,count=8,buffer=r['buffer'],epoch=r['epoch'],stack=r['stack'],half=r['half'],row=r['row'],col=r['col'],source_stream_record=r['source_record']))
  assert vector,'scheduler made no progress'
  assert len({p['source_leaf']for p in vector})==len(vector)
  assert len({p['source_PC']for p in vector})==len(vector)
  assert len({(p['destination_quad'],p['destination_bank'])for p in vector})==len(vector)
  assert len(vector)<=8
  checks+=len(vector);maxwidth=max(maxwidth,len(vector))
  item=dict(window_bundle=runs[0]['window_bundle'],relative_issue_date=date,packets=vector)
  if output:output.write(json.dumps(item,separators=(',',':'))+'\n')
  newquads={p['destination_quad']for p in vector}-sample_quads
  if date<8 or newquads:sample.append(item);sample_quads.update(p['destination_quad']for p in vector)
  date+=1
 assert checks==count
 lower=max(max(leaves.values(),default=0),max(banks.values(),default=0),(count+7)//8)
 return dict(window_bundle=runs[0]['window_bundle'],sector_packets=count,issue_dates=date,resource_degree_lower_bound=lower,max_vector_width=maxwidth,destination_quads=sorted(quads),source_PC_histogram=dict(pcs),source_leaf_histogram=dict(leaves),destination_bank_histogram={f'{q}:{b}':n for(q,b),n in banks.items()},first_dates=sample)


def run(events,output=None):
 groups=[];pending=[]
 for e in events:
  if e['kind']=='load227':
   if pending and e['window_bundle']!=pending[0]['window_bundle']:groups.append(pending);pending=[]
   pending.append(e)
  elif pending:groups.append(pending);pending=[]
 if pending:groups.append(pending)
 total_dates=total_packets=lower=0;max_dates=0;width=collections.Counter();samples=[];covered=set();max_PC_conflict=None
 for group in groups:
  r=schedule(group,output);total_dates+=r['issue_dates'];total_packets+=r['sector_packets'];lower+=r['resource_degree_lower_bound'];max_dates=max(max_dates,r['issue_dates']);width[r['max_vector_width']]+=1
  if set(r['destination_quads'])-covered:
   samples.append(r);covered.update(r['destination_quads'])
  if max_PC_conflict is None or max(map(int,r['source_PC_histogram'].values()))>max(map(int,max_PC_conflict['source_PC_histogram'].values())):max_PC_conflict=r
 assert total_packets==5389626
 return dict(status='UNSELECTED8PATH_VECTOR_PROVIDER_STATIC_SOURCE_STIMULUS_NO_PHYSICAL_DATES',window_read_bundles=len(groups),sector_packets=total_packets,relative_issue_dates=total_dates,degree_lower_bound_sum=lower,max_dates_one_bundle=max_dates,max_vector_width_histogram=dict(width),relative_issue_only_ms_at833ps=total_dates*833e-9,quad_coverage=sorted(covered),genuine_samples=samples,max_PC_conflict_sample=max_PC_conflict,qualification=['assumes NEW8path parallel vector provider + proved count8 coalescing, not installed RTL','unique sourceleaf/PC and unique destinationquad/bank per relative date; oneownedwindowbundle atatime','no reorder acrossbody/drain/STORE/windowownership events','relative dates omit fill/drain/release, descriptor setup/counter generation, physical commit and allsourcearithmetic','greedy valid scheduling; no claim that this is minimum date count','current source stack3/scratch/namespace and numericG5 remain open'])


def check_sample_vector(v):
 from window_map import encode
 assert len({p['source_leaf']for p in v})==len(v),'sourceleaf collision'
 assert len({(p['destination_quad'],p['destination_bank'])for p in v})==len(v),'destinationbank collision'
 for p in v:
  assert encode(p['row'],p['col'],p['source_PC'],p['source_slot'])==p['source_sector'],'wrong PC/slot source'
  assert p['source_leaf']==(p['source_PC']&7)
  assert p['destination_quad']==p['first_VMword']>>16 and p['destination_bank']==(p['first_VMword']>>3)&7
  assert p['destination_sector']==p['first_VMword']>>3
  assert p['count']==8 and p['format']==5
 return len(v)


if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--calendar-out',type=Path);a=ap.parse_args();root=Path(__file__).parents[1];packet=json.loads((root/'canonical_resident_cached/stream.json').read_text());ev,_=compile_programme(packet);validate(ev,packet)
 if a.calendar_out:
  with a.calendar_out.open('w')as f:report=run(ev,f)
 else:report=run(ev)
 checks=0;vectors=[date['packets']for g in report['genuine_samples']for date in g['first_dates']]
 for v in vectors:checks+=check_sample_vector(v)
 sample=next(v for v in vectors if len(v)>1);controls=[]
 for name in('wrong_source_PC','duplicate_source_leaf','duplicate_destination_bank'):
  bad=[dict(x)for x in sample]
  if name=='wrong_source_PC':bad[0]['source_PC']^=1
  elif name=='duplicate_source_leaf':bad[1]['source_leaf']=bad[0]['source_leaf']
  else:bad[1]['destination_quad']=bad[0]['destination_quad'];bad[1]['destination_bank']=bad[0]['destination_bank']
  try:check_sample_vector(bad)
  except AssertionError:controls.append(name)
  else:raise AssertionError('vector mutant escaped:'+name)
 report['sample_inverse_route_checks']=checks;report['controls_caught']=controls
 Path(__file__).with_suffix('.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in('genuine_samples','max_PC_conflict_sample')}))
