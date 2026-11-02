"""Exact native DATA-cone classification; no placements/DB changes or prefix-based ownership."""
from pathlib import Path
import json,gzip,re,collections,fnmatch
R=Path(__file__).parent;P=R/'inputs';cells=[json.loads(x)for x in gzip.open(P/'cells.jsonl.gz','rt')];ci={c[0]:i for i,c in enumerate(cells)};names=[c[0]for c in cells];masters=json.load(open(P/'native_masters.json'));FF={i for i,c in enumerate(cells)if c[1].startswith('DFF')};comb={i for i,c in enumerate(cells)if i not in FF and not c[1].startswith('TAPCELL')};buf={i for i in comb if cells[i][1].startswith(('BUF','INV','HB'))};T=json.load(open(P/'FF_targets.json'));local={ci[n]for n,t in T.items()if t['family']=='ft2_ring_band_FFs'};stage0={ci[n]for n,t in T.items()if t['family']=='ft2_stage0'}
# Roles come from the exact used Liberty ff semantics, checked against native MTerm inventory.
lib=(P/'SEQ_RVT_TT.lib').read_text();roles={};unknown=[]
for master in sorted({cells[i][1]for i in FF}):
 hit=re.search(r'\bcell\s*\(\s*'+re.escape(master)+r'\s*\)\s*\{',lib)
 if not hit:unknown.append(master);continue
 end=lib.find('\n  cell (',hit.end());blk=lib[hit.start():end if end>=0 else len(lib)];func={k:re.findall(r'\b'+k+r'\s*:\s*"([^"]+)"',blk)for k in('clocked_on','next_state','clear','preset')};tokens=lambda key:{p for s in func[key]for p in re.findall(r'[A-Za-z_][A-Za-z0-9_]*',s)};roles[master]=dict(clock=tokens('clocked_on'),data=tokens('next_state'),reset=tokens('clear')|tokens('preset'),native_inputs={p[0]for p in masters[master]['pins']if p[1]=='INPUT'})
 if roles[master]['clock']|roles[master]['data']|roles[master]['reset']!=roles[master]['native_inputs']:unknown.append(master)
assert not unknown,unknown
nets=[];ins=collections.defaultdict(list);outs=collections.defaultdict(list);port_in={};port_out={};reason=collections.defaultdict(set);clock_seed=[];reset_seed=[];multidriver=set()
for line in gzip.open(P/'nonPG_connectivity.jsonl.gz','rt'):
 nname,sig,dnt,its,bts=json.loads(line);dr=[];sk=[];ni=len(nets)
 for name,pin,io,psig,xy,valid in its:
  i=ci[name]
  if io=='OUTPUT':dr.append(('c',i,pin));outs[i].append(ni)
  elif io=='INPUT':
   sk.append(('c',i,pin));ins[i].append((ni,pin))
   if i in FF:
    if pin in roles[cells[i][1]]['clock']:clock_seed.append(ni)
    if pin in roles[cells[i][1]]['reset']:reset_seed.append(ni)
  else:
   if i in comb:reason[i].add('unknown_inout_signal_pin')
  if i in comb and(dnt or sig=='CLOCK' or psig=='CLOCK'):reason[i].add('native_clock_or_DNT_net'if sig=='CLOCK'or psig=='CLOCK'else'native_DNT_net')
 for name,io,psig in bts:
  if io=='INPUT':dr.append(('p',name,''));port_in[name]=ni
  elif io=='OUTPUT':sk.append(('p',name,''));port_out[name]=ni
  if io=='OUTPUT'and(psig=='CLOCK'or name.startswith('fclk_out_')):clock_seed.append(ni)
  if io=='OUTPUT'and re.fullmatch(r'(?:rst_o_[0-9]+|start_o_[0-9]+)',name):reset_seed.append(ni)
 if len(dr)!=1:
  for e in dr+sk:
   if e[0]=='c'and e[1]in comb:reason[e[1]].add('native_multi_or_missing_driver')
  multidriver.add(ni)
 nets.append((nname,sig,dnt,dr,sk))
# Native typed reset FFs are selected by the actual generated reset-tree binding patterns.
patterns=re.findall(r'^rtr_place(?:_opt)?\s+\S+\s+\{([^}]+)\}',(P/'reset_tree.tcl').read_text(),re.M)
assert len(patterns)==264,('source binding pattern inventory changed',len(patterns))
parts=[re.fullmatch(r'\*([A-Za-z0-9_]+)\[\./\]\*',p)for p in patterns]
assert all(parts),'only the proven *literal[./]* grammar may use this equivalent implementation'
literals=[p.group(1)for p in parts];assert len(set(literals))==264
literal_re=re.compile('(?:'+'|'.join(re.escape(p)for p in literals)+')[./]')
positives={i for i in FF if literal_re.search(names[i])}
negatives=sorted(FF-positives,key=lambda i:names[i]);sample_neg={negatives[min(len(negatives)-1,len(negatives)*k//128)]for k in range(128)}
for master in roles:
 sample_neg.update(next((i for i in negatives if cells[i][1]==master),None)for _ in range(1))
sample_neg.discard(None)
for i in positives|sample_neg:
 old_pred=any(fnmatch.fnmatchcase(names[i],pat)for pat in patterns);new_pred=bool(literal_re.search(names[i]));assert old_pred==new_pred,('predicate mismatch',names[i])
validation=dict(patterns=264,grammar='all source patterns exactly *ASCII_literal[./]*; glob membership equals literal[./] regex search',native_positive_count=len(positives),all_native_positives_compared=True,native_negative_samples_compared=len(sample_neg),source_FF=len(FF),policy_changed=False)
(R/'predicate_equivalence.json').write_text(json.dumps(validation,indent=2));print('EXACT_PREDICATE_EQUIVALENCE',validation,flush=True)
typed_reset=positives
for i in typed_reset:
 for ni,pin in ins[i]:
  if pin in roles[cells[i][1]]['data']:reset_seed.append(ni)
def backwards(seed,label):
 todo=list(seed);seen=set()
 while todo:
  ni=todo.pop()
  if ni in seen:continue
  seen.add(ni)
  for typ,i,pin in nets[ni][3]:
   if typ=='c'and i in comb:
    reason[i].add(label);todo.extend(n for n,p in ins[i])
 return seen
clock_back=backwards(clock_seed,'clock_infrastructure');reset_back=backwards(reset_seed,'async_or_typed_reset_START_infrastructure')
# Shared reset/START buffer distribution is immutable even when its terminal FF has ordinary D pin semantics.
control_sources=[ni for p,ni in port_in.items()if re.fullmatch(r'(?:arst_n|start_i)',p)]+[ni for i in typed_reset for ni in outs[i]]
todo=list(control_sources);seen=set()
while todo:
 ni=todo.pop()
 if ni in seen:continue
 seen.add(ni)
 for typ,i,pin in nets[ni][4]:
  if typ=='c'and i in buf:reason[i].add('reset_START_distribution');todo.extend(outs[i])
for i in comb:
 if cells[i][5]in('FIRM','LOCKED','COVER'):reason[i].add('immutable_native_status')
 if cells[i][6]:reason[i].add('native_instance_DNT')
# First-sequential/public frontier masks are propagated over the actual native combinational DAG.
LOCAL,STAGE,OTHER,PIO,CLOCK,RESET,UNKNOWN=1,2,4,8,16,32,64
succ=collections.defaultdict(set);pred=collections.defaultdict(set);mask=collections.Counter();witness=collections.defaultdict(dict)
for ni,(nname,sig,dnt,dr,sk)in enumerate(nets):
 for typ,i,dp in dr:
  if typ!='c'or i not in comb:continue
  if sig=='CLOCK':mask[i]|=CLOCK;witness[i].setdefault(CLOCK,nname)
  if ni in multidriver:mask[i]|=UNKNOWN;witness[i].setdefault(UNKNOWN,nname)
  for typ,j,pin in sk:
   if typ=='p':bit=CLOCK if j.startswith('fclk_out_')else RESET if re.fullmatch(r'(?:rst_o_[0-9]+|start_o_[0-9]+)',j)else PIO;mask[i]|=bit;witness[i].setdefault(bit,j)
   elif j in FF:
    rr=roles[cells[j][1]];bit=CLOCK if pin in rr['clock']else RESET if pin in rr['reset']else(LOCAL if j in local else STAGE if j in stage0 else OTHER)if pin in rr['data']else UNKNOWN;mask[i]|=bit;witness[i].setdefault(bit,names[j]+'.'+pin)
   elif j in comb:succ[i].add(j);pred[j].add(i)
left={i:len(succ[i])for i in comb};q=collections.deque(i for i in comb if left[i]==0);rev=[]
while q:
 i=q.popleft();rev.append(i)
 for p in pred[i]:
  mask[p]|=mask[i]
  for bit,w in witness[i].items():witness[p].setdefault(bit,w)
  left[p]-=1
  if left[p]==0:q.append(p)
cycles={i for i in comb if left[i]};
for i in cycles:reason[i].add('combinational_cycle_or_unresolved_frontier')
# Reachability is functional ownership evidence: declared ft2 data inputs and the selected existing ring FFs.
data_ports={p for p in port_in if re.fullmatch(r'ft2_i\[[0-9]+\]',p)};todo=[port_in[p]for p in data_ports]+[ni for i in local for ni in outs[i]];seen=set();reached=set()
while todo:
 ni=todo.pop()
 if ni in seen:continue
 seen.add(ni)
 if nets[ni][1]=='CLOCK':continue
 for typ,i,pin in nets[ni][4]:
  if typ=='c'and i in comb:reached.add(i);todo.extend(outs[i])
eligible=[];held=collections.Counter();examples=collections.defaultdict(list)
for i in sorted(reached):
 rs=set(reason[i]);bad=mask[i]&~(LOCAL|STAGE)
 if bad:rs.add('shared_or_clock_reset_public_frontier')
 if not mask[i]&(LOCAL|STAGE):rs.add('no_owned_first_capture')
 if rs:
  for label in sorted(rs):
   held[label]+=1
   if len(examples[label])<5:examples[label].append(dict(name=names[i],master=cells[i][1],mask=mask[i],witnesses=witness[i]))
 else:eligible.append(i)
area=lambda i:(cells[i][2][2]-cells[i][2][0])*(cells[i][2][3]-cells[i][2][1])/1e6
serial_roles={m:{k:sorted(v)for k,v in d.items()}for m,d in roles.items()};report=dict(scope='DISABLED exact native DATA-cone classification, no placement/DB/GEN/CAD. Names are report labels only, never ownership proof.',native_nonPG_nets=len(nets),native_cells=len(cells),native_FF=len(FF),data_source_ports=len(data_ports),local_ring_FF=len(local),stage0_capture_FF=len(stage0),typed_reset_FF=len(typed_reset),Liberty_FF_roles=serial_roles,combinational_nodes=len(comb),resolved_reverse_topology=len(rev),cycles=len(cycles),reachable_data_cone=len(reached),eligible_owned_DATA_cells=len(eligible),eligible_area_um2=sum(area(i)for i in eligible),eligible_actual_ft2_namespace=sum(names[i].startswith('u_bound.u_cland_ft2_i/')for i in eligible),held_reason_counts=dict(held),held_examples=dict(examples),clock_infrastructure_cells=sum('clock_infrastructure'in reason[i]for i in comb),reset_START_infrastructure_cells=sum(any('reset'in x.lower()or'START'in x for x in reason[i])for i in comb),ownership_rule='reachable from exact declared ft2 data ports or selected ring FF outputs; exclusively local-ring/stage0 first-D-pin capture frontier; no clock/reset/START/FIRM/DNT/multidriver/unknown/shared node eligible',holds=['all52044FFposes and stages/cycles/source/pins remain fixed in subsequentcombPREP','native95696bufferPGnull/sourcephase/actualGRT/partialface/fill holds unchanged','any shared/clock/reset/START infrastructure remains held; no name-prefix sweep'])
(R/'classification.json').write_text(json.dumps(report,indent=2));(R/'eligible.json').write_text(json.dumps([dict(name=names[i],master=cells[i][1],bbox_dbu=cells[i][2],orient=cells[i][4],frontier_mask=mask[i])for i in eligible],indent=2));gzip.open(R/'classification_graph.json.gz','wt').write(json.dumps(dict(names=names,eligible=eligible,local=list(local),stage0=list(stage0),clockheld=[i for i in comb if'clock_infrastructure'in reason[i]],held={str(i):sorted(reason[i])for i in comb if reason[i]},net_data=nets,ins={str(k):v for k,v in ins.items()},outs={str(k):v for k,v in outs.items()}),separators=(',',':')))
print({k:v for k,v in report.items()if k not in('held_examples','Liberty_FF_roles','holds')},flush=True)
