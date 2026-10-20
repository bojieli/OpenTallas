"""Bounded PEER floorplan diagnosis; complete identity read-only, no placement edits."""
from pathlib import Path
import sys,json,gzip,collections,heapq,re,hashlib
p=Path(sys.argv[1]);out=p.parent/'classification';out.mkdir(exist_ok=True);d=json.load(gzip.open(p,'rt'));seq={x['instance']:x for x in d['sequential_instances']};comb={x['output_net']:x for x in d['combinational_cells']};counts=collections.Counter();over=collections.Counter();top=[];fixed=[];bybucket=collections.defaultdict(list);fixed_macro=[];all_fixed_macro=[]
def cls(x):
 if x['kind'].startswith('synchronous_sram') or x['kind']=='memory_data_control':return 'macro'
 if x['kind'] in ('input_port','output_port'):return x['kind']
 c=seq.get(x.get('instance'),{}).get('boundary_classification','unknown')
 return 'boundary_input' if c=='direct_port_data_input' else 'boundary_output' if c=='direct_port_data_output' else 'boundary_both' if c=='direct_port_data_input_and_output' else 'interior_or_multistage'
def ports(x):
 s=seq.get(x.get('instance'),{});return {'input':s.get('direct_input_port_bits',[]),'output':s.get('direct_output_port_bits',[])}
def path(a,b):
 target=a['net'];start=b['net'];q=collections.deque([start]);seen={start};toward={}
 while q and len(seen)<=20000:
  n=q.popleft()
  if n==target:break
  c=comb.get(n)
  if not c:continue
  for z in c['input_pins']:
   dep=z['net']
   if dep not in seen:seen.add(dep);toward[dep]=(n,c,z['pin']);q.append(dep)
 else:return {'status':'OPEN_no_path_within20000nets','visited':len(seen)}
 if target not in seen:return {'status':'OPEN_no_path','visited':len(seen)}
 nodes=[];n=target
 while n!=start:
  nxt,c,pin=toward[n];nodes.append({'instance':c['instance'],'master':c['master'],'function':c['function'],'input_pin':pin,'input_net':n,'output_pin':c['output_pin'],'output_net':nxt});n=nxt
 return {'status':'PASS_concrete_Liberty_dependency_path','nodes':nodes,'visited':len(seen)}
for i,e in enumerate(d['data_stage_edges']):
 a,b=e['root'],e['endpoint'];
 if cls(a).startswith('boundary') and cls(b)=='macro':all_fixed_macro.append({'root':a,'endpoint':b,'root_ports':ports(a),'endpoint_ports':ports(b)})
 dist=sum(abs(x-y) for x,y in zip(a['xy_um'],b['xy_um']));k=cls(a)+' -> '+cls(b);counts[k]+=1
 if dist<=405+1e-8:continue
 over[k]+=1;z={'root':a,'endpoint':b,'root_class':cls(a),'endpoint_class':cls(b),'distance_center_L1_um':dist,'excess_over405_um':dist-405,'root_ports':ports(a),'endpoint_ports':ports(b)}
 h=bybucket[k]
 if len(h)<5:heapq.heappush(h,(dist,i,z))
 elif dist>h[0][0]:heapq.heapreplace(h,(dist,i,z))
 if (cls(a).startswith('boundary') and cls(b)=='macro') or (cls(a)=='macro' and cls(b).startswith('boundary')):fixed_macro.append(z)
 if len(top)<20:heapq.heappush(top,(dist,i,z))
 elif dist>top[0][0]:heapq.heapreplace(top,(dist,i,z))
 if cls(a).startswith('boundary') and cls(b).startswith('boundary'):fixed.append(z)
worst=[z for _,_,z in sorted(top,reverse=True)]
bucket_samples={k:[z for _,_,z in sorted(h,reverse=True)] for k,h in bybucket.items()}
for z in worst+fixed+[z for h in bucket_samples.values() for z in h]:z['one_cause_cone_path']=path(z['root'],z['endpoint'])
r={'schema':'peer.pre_cts_complete_stage_classification.v1','scope':'3_place DIAGNOSTIC standardcell-center stage L1, actual macro pin XY. No timing/admission or exact standardcell pin claim. Fixed boundary membership cannot be altered by interior-only movement.','identity_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'odb_sha256':d['odb_sha256'],'all_pairs':dict(counts),'over405_pairs':dict(over),'worst20':worst,'fixed_boundary_pairs_over405':fixed,'fixed_macro_boundary_pairs_over405':fixed_macro,'all_boundary_macro_pairs':all_fixed_macro,'port_bits':d['port_bits'],'worst_by_bucket':bucket_samples,'macro_instances':[{k:x[k] for k in ('instance','master','kind')} for x in d['sequential_instances'] if x['kind']=='synchronous_sram']}
(out/'classification.json').write_text(json.dumps(r,indent=2)+'\n');print({k:v for k,v in r.items() if k not in ('worst20','fixed_boundary_pairs_over405','macro_instances','fixed_macro_boundary_pairs_over405','worst_by_bucket','all_boundary_macro_pairs','port_bits')});print('fixed_pairs',len(fixed))
