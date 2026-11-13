#!/usr/bin/env python3
"""Same-depth SD raw-reset copies on the free column west of landing bands.
The stock corridor planner cannot exit its clearance-grown band when the existing base is itself in that band.
No source equation, original chain terminal, reset-release depth or data latency changes.
"""
import argparse,copy,hashlib,json,pathlib,re,sys
HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import kv_start_corridor_event as K
import reach_rules as RR
from start_obstacle_path import relay_sites
from landing_raw_branches import RawBranches
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('plan');ap.add_argument('--out-plan',required=True);ap.add_argument('--report',required=True)
ap.add_argument('--reference-plan',required=True,help='Exact plan from which --bind-rtl was emitted; all SD semantic fields must still match')
ap.add_argument('--bind-rtl',required=True,help='Explicit completed bind RTL directory, not a cache guessed by this tool')
args=ap.parse_args()
p=json.load(open(args.plan));reference=json.load(open(args.reference_plan));reports={}
def semantic(t):
 t=copy.deepcopy(t);ck=t.get('clock',{});ck.pop('landing_origin_rect_um',None);ck.pop('landing_raw_branches',None)
 # This form may coexist with an independently reviewed forwarded-clock source re-site. Pins and all reset semantics stay exact.
 for pin in ck.get('landing_contract',{}).get('pins',[]):
  if pin.get('kind')=='clock' and pin.get('dir')=='out':
   pin.pop('source_clock_port',None);pin.pop('source_clock_tap',None)
 return t
for tn in ('kv3_sys_SD','kv3_sys_SD_v1'):
 t=p['partition_types'][tn];assert semantic(t)==semantic(reference['partition_types'][tn]),f'{tn}: reference-plan semantic mapping changed; regenerate bind RTL, never remap numeric terminals by guess';ck=t['clock'];lc=ck['landing_contract'];pins={r['name']:r['xy_um'] for r in lc['pins']}
 f=pathlib.Path(args.bind_rtl)/f'{tn}_part.sv';text=f.read_text();raw=re.search(r'assign cland_start_raw = (\w+);',text).group(1)
 byq={q:dict(d=d,depth=int(dep),xy=[float(x),float(y)]) for _,d,q,dep,x,y in K.REL.findall(text)}
 chain=[raw]
 while chain[-1] in byq and byq[chain[-1]]['d'] in byq:chain.append(byq[chain[-1]]['d'])
 chain.reverse(); assert len(chain)>=2
 bands=[v['rect_um'] for v in lc['bands'].values()];col=round(min(r[0] for r in bands)-12.96,3)
 obs=list(K.macro_boxes(t).values())+bands+ck.get('keepouts_um',[])
 origin=RR.start_info(t)['origin'];targets={'origin':origin}
 targets.update({'fstart:'+n[len('cland_fstart_out_'):]:xy for n,xy in pins.items() if n.startswith('cland_fstart_out_')})
 branches=[];rp={}
 for role,target in targets.items():
  found=None
  for k in range(len(chain)-2,-1,-1):
   base=chain[k];n=len(chain)-1-k;a=byq[base]['xy'];path=[a,[col,a[1]],[col,target[1]],list(target)]
   path=[q for j,q in enumerate(path) if j==0 or q!=path[j-1]]
   try:st=relay_sites(path,n,max_hop_um=380.0,site_boxes=obs,clearance_um=4.32)
   except ValueError:continue
   hops=[K.man(x,y) for x,y in zip([a]+st,st+[list(target)])]
   if max(hops)>380.0001:continue
   name='o' if role=='origin' else 'fs_'+role.split(':',1)[1]
   branches.append(dict(name=name,base=base,stages=[dict(original=chain[k+1+j],xy_um=xy) for j,xy in enumerate(st)],consumers=[role]))
   rp[role]=dict(base=base,terminal=raw,copies=n,site_um=st,max_hop_um=round(max(hops),3),hops_um=[round(x,3) for x in hops],column_x_um=col)
   found=True;break
  assert found,(tn,role,chain)
 ck['landing_raw_branches']=branches
 rb=RawBranches(tn,branches,text,t['outline_um'])
 for role in targets:rb.raw_for(role,raw)
 proof=rb.validate(text+'\n'+'\n'.join(rb.rtl))
 reports[tn]=dict(source_body=str(f),source_body_sha256=hashlib.sha256(text.encode()).hexdigest(),reference_plan=str(pathlib.Path(args.reference_plan).resolve()),raw_terminal=raw,branches=rp,phase_check=proof,added_data_cycles=0,added_reset_cycles=0)
 # All stages are original same-clk D-chain copies. Keep terminals identical even when names differ by type.
 assert all(b['stages'][-1]['original']==raw for b in branches)
import schema
errors=schema.validate(p); assert not errors,errors[:5]
pathlib.Path(args.out_plan).write_text(json.dumps(p,indent=1)+'\n');pathlib.Path(args.report).write_text(json.dumps(reports,indent=1)+'\n')
print(json.dumps({k:{'branches':len(v['branches']),'raw':v['raw_terminal'],'max_hop':max(z['max_hop_um'] for z in v['branches'].values()),'data_cycles':0,'reset_cycles':0} for k,v in reports.items()}))
