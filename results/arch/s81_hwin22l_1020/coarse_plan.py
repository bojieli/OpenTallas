import csv,collections,json,re,sys,hashlib
from pathlib import Path
sys.path.insert(0,'/audit/tools/ref_tile')
import native_census as C
import glob
roles,receipts=C.liberty_roles(glob.glob('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT*TT*.lib*')+glob.glob('/src/physical/asap7_memory_macros/*/*_tt.lib'))
boxes={'WEST':[43.2,163.89,155.8,203.85],'CENTRE':[155.8,163.89,405.8,203.85],'EAST':[405.8,163.89,518.4,203.85]}
if len(sys.argv)>1:boxes=json.loads(Path(sys.argv[1]).read_text())
fixedcoords={}
if len(sys.argv)>2:
 for row in csv.reader(open('/audit/terms.tsv'),delimiter='\t'):
  name,net,direction,master,block,x,y=row
  if master=='PORT'or block=='1':fixedcoords[name]=(x,y)
terms={}; byinst=collections.defaultdict(list); loads=collections.defaultdict(list); outs=collections.defaultdict(list); errors=[]
for row in csv.reader(open('/audit/terms_src.tsv'if len(sys.argv)>2 else'/audit/terms.tsv'),delimiter='\t'):
 name,net,direction,master,block,x,y=row;inst,pin=name.rsplit('/',1)
 if len(sys.argv)>2 and(master=='PORT'or block=='1'):
  if name not in fixedcoords:raise ValueError('missing fixed coordinate '+name)
  x,y=fixedcoords[name]
 if master=='PORT':seq=False;clock=pin=='ck'
 else:
  role=roles.get(master,{}).get('pins',{}).get(pin)
  if role is None:
   m=re.fullmatch(r'(.*)\[(-?\d+)\]',pin)
   if m and int(m[2]) in roles.get(master,{}).get('bus_order',{}).get(m[1],[]):role=roles[master]['pins'].get(m[1])
  if role is None:errors.append('missing Liberty '+name);continue
  seq=roles[master]['sequential'];clock=role['clock']
 d=dict(name=name,net=net,direction=direction,master=master,block=bool(int(block)),x=float(x),y=float(y),instance=inst,pin=pin,clock=clock,seq=seq)
 terms[name]=d;byinst[inst].append(d)
 if master=='PORT':
  if direction=='OUTPUT':loads[net].append(d)
 elif direction=='INPUT':loads[net].append(d)
 elif direction=='OUTPUT':outs[inst].append(net)
def event_seed(inst):
 if '.start_r' in inst:return 'CENTRE'
 m=re.search(r'g_event_(?:mem|broadcast)\[(\d+)\]',inst)or re.search(r'^u_ot_pr_core[./]fd\[(\d+)\]',inst)
 if m:
  e=int(m[1]);return 'WEST'if e<6 else'EAST'if e>=10 else'CENTRE'
 return 'CENTRE'
def reset(inst):return 'u_rr.' in inst or 'u_rr/'in inst
seedmemo={};seedactive=set()
def seed(inst):
 if inst in seedmemo:return seedmemo[inst]
 if not reset(inst):return event_seed(inst)
 if inst in seedactive:raise ValueError('reset cycle '+inst)
 seedactive.add(inst);owners=set();seen=set();stack=list(outs[inst])
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n)
  for d in loads[n]:
   if d['master']=='PORT':owners.add('CENTRE')
   elif d['seq'] or d['block']:owners.add(seed(d['instance']))
   else:stack.extend(outs[d['instance']])
 seedactive.remove(inst);v=next(iter(owners))if len(owners)==1 else'CENTRE';seedmemo[inst]=v;return v
memo={};active=set()
def owner(inst):
 if inst in memo:return memo[inst]
 ds=byinst.get(inst,[])
 if not ds:return 'CENTRE'
 if ds[0]['seq']or ds[0]['block']:return seed(inst)
 if inst in active:raise ValueError('comb cycle '+inst)
 active.add(inst);owners=set();seen=set();stack=list(outs[inst])
 while stack:
  n=stack.pop()
  if n in seen:continue
  seen.add(n)
  for d in loads[n]:
   if d['master']=='PORT':owners.add('CENTRE')
   elif d['seq']or d['block']:owners.add(seed(d['instance']))
   else:
    # Hierarchical memo is only safe for the terminal owner SET, not a mixed-to-centre collapse.
    stack.extend(outs[d['instance']])
 active.remove(inst);v=next(iter(owners))if len(owners)==1 else'CENTRE';memo[inst]=v;return v
hist=collections.defaultdict(lambda:dict(cells=0,area_um2=0));manifest=[]
for row in csv.reader(open('/audit/instances_src.tsv'if len(sys.argv)>2 else'/audit/instances.tsv'),delimiter='\t'):
 inst,master,block,orient,status,x0,y0,x1,y1=row
 if block=='1'or re.search(r'TAPCELL|FILL|DECAP|ENDCAP|tapcell',master):continue
 g=owner(inst);area=(float(x1)-float(x0))*(float(y1)-float(y0));hist[g]['cells']+=1;hist[g]['area_um2']+=area;manifest.append((g,inst,master))
for g,h in hist.items():
 b=boxes[g];h['box']=b;h['density']=h['area_um2']/((b[2]-b[0])*(b[3]-b[1]))
# Every actual registered/macro/input source to actual registered/macro/output sink, conservative all combinational inputs.
ememo={};vis=set()
def endpoints(net):
 if net in ememo:return ememo[net]
 if net in vis:raise ValueError('comb cycle '+net)
 vis.add(net);ends=set()
 for d in loads[net]:
  if d['clock']:continue
  if d['seq']or d['block']or d['master']=='PORT':ends.add(d['name'])
  else:
   for n in outs[d['instance']]:ends.update(endpoints(n))
 vis.remove(net);ememo[net]=ends;return ends
def box(d):
 if d['block']or d['master']=='PORT':return[d['x'],d['y'],d['x'],d['y']]
 return boxes[seed(d['instance'])]
def dist(a,b):return max(abs(a[0]-b[2]),abs(a[2]-b[0]))+max(abs(a[1]-b[3]),abs(a[3]-b[1]))
worst=0;bad=[];pairs=0
for d in terms.values():
 source=(d['master']=='PORT'and d['direction']=='INPUT'and not d['clock'])or(d['master']!='PORT'and d['direction']=='OUTPUT'and(d['seq']or d['block']))
 if not source:continue
 for name in endpoints(d['net']):
  e=terms[name];v=dist(box(d),box(e));pairs+=1;worst=max(worst,v)
  if v>405.000001:bad.append(dict(source=d['name'],endpoint=name,um=round(v,6),source_box=box(d),endpoint_box=box(e)))
result=dict(scope=('Complete original native1_synth source graph with unchanged actual macro/port pins'if len(sys.argv)>2 else'Complete actual c21k CTS graph and macro/port pins')+'; conservative structural region planning ONLY; not a gate or native placement',liberty_role_errors=errors,groups=dict(hist),boxes=boxes,cell_area=sum(h['area_um2']for h in hist.values()),endpoint_pairs=pairs,max_box_bound_um=worst,over405=len(bad),violations=sorted(bad,key=lambda r:-r['um'])[:100],reset_owner_hist=dict(collections.Counter(seedmemo.values())),input_sha256={n:hashlib.sha256(Path('/audit/'+n).read_bytes()).hexdigest()for n in (['terms_src.tsv','instances_src.tsv','terms.tsv']if len(sys.argv)>2 else['terms.tsv','instances.tsv'])})
Path('/audit/'+('source_'if len(sys.argv)>2 else'')+'coarse_plan'+('_w46'if len(sys.argv)>1 else'')+'.json').write_text(json.dumps(result,indent=2)+'\n')
Path('/audit/'+('source_'if len(sys.argv)>2 else'')+'coarse_manifest'+('_w46'if len(sys.argv)>1 else'')+'.tsv').write_text(''.join('\t'.join(r)+'\n'for r in manifest))
print(json.dumps(result,indent=2))
