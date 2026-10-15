#!/usr/bin/env python3
"""Exact current149-clock constituents; geometry proposals stay separate from physical qualification."""
import hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def show(commit,path):return subprocess.check_output(['git','-C',str(ROOT),'show',f'{commit}:{path}'])
def loadjob(name):return json.loads((Path.home()/'.local/state/closure_loop/jobs'/f'{name}.json').read_text())
J={'mul4':'s81engm_mul4-boundary810-0852-2e57a7a75','chunk8':'s81engm_chunk8-v21-bf044b7f6','add8':'s81engm_add8-v21-bf044b7f6','norm':'s81engm_norm-v21-bf044b7f6','sum':'s81engm_sum-fixed808-0833-26b917e43','signed_sqrt':'s81engm_signed_sqrt-v21-16a883417','sigmoid':'s81engm_sigmoid-v21-bf044b7f6','control':'s81engm_control-c810-6af87135e','rly':'s81engm_rly-component-0822-772decf15','shctl':'s81engm_shctl-bankv1benchfix-1421-dfd1e697a','shcol':'s81engm_shcol-bankv1benchfix-1421-dfd1e697a'}
masters={}
for name,job in J.items():
 d=loadjob(job);c=d['spec']['source']['commit'];p=f'physical/ref_tile/s81engm_{name}/spec.json';s=json.loads(show(c,p));io=s.get('io_tcl');masters[name]={'top':s['top'],'source_commit':c,'job':job,'job_status_observed':d['status'],'outline_um':[s['outline']['w'],s['outline']['h']],'source_spec':p,'source_spec_sha256':hashlib.sha256(show(c,p)).hexdigest(),'pin_tcl':io,'pin_tcl_sha256':hashlib.sha256(show(c,io)).hexdigest() if io else None,'normal_edges_added_here':0}
rows=[('shell',['shcol','shcol','shctl','shcol','shcol']),('add8',['add8']*4),('mul4a',['mul4']*4),('mul4b',['mul4']*4),('relay',['rly']),('reduceA',['chunk8']*3+['sum']+['chunk8']*3),('reduceB',['chunk8']*3+['sum','sum']+['chunk8']*3),('scalar',['norm','signed_sqrt','control','sigmoid','norm'])]
def plan(gap,margin):
 W=max(sum(masters[m]['outline_um'][0] for m in ms)+gap*(len(ms)-1) for _,ms in rows);y=margin;boxes=[]
 for row,ms in rows:
  rw=sum(masters[m]['outline_um'][0] for m in ms)+gap*(len(ms)-1);x=margin+(W-rw)/2;rh=max(masters[m]['outline_um'][1] for m in ms)
  for i,m in enumerate(ms):
   w,h=masters[m]['outline_um'];boxes.append({'row':row,'row_index':i,'master':m,'x':round(x,3),'y':round(y,3),'w':w,'h':h});x+=w+gap
  y+=rh+gap
 return {'width_um':round(W+2*margin,3),'height_um':round(y-gap+margin,3),'gap_um':gap,'outer_margin_um':margin,'leaves':len(boxes),'boxes':boxes,'registered_seam_reach':'OPEN: full actual pin-to-pin adjacency not yet repaired/proven','physical_status':'unqualified proposal, not a fitted/routed cluster'}
source=['rtl/dsrom_sys/engram/mix/dsfd_engram_mix4_c.sv','rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv']
roots=[{'bit':0,'scope':'top descriptor/BC/return/RS5','blocker':'unpartitioned top state/relay stations'}]
for q in range(4):
 b=1+37*q
 for i,n in enumerate(['shell.ctl','shell.col0','shell.col1','shell.col2','shell.col3','mix.control+relay']+[f'mix.arithmetic[{j}]' for j in range(31)]):roots.append({'bit':b+i,'scope':f'cluster{q}.{n}'})
rec={'schema':'opentallas.s81.mix4-current149-constituents.v1','source_commit':subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),'sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source},'static_define':'DSFD_ENGRAM_STATIC_ISSUE','ports':{'ck':149,'rst':1,'c_cmd':85,'c_done':9,'c_st':2,'rq_v':20,'rq_row':280,'rs_v':20,'rs_d':10240,'wq_v':4,'wq_row':56,'wq_mask':64,'wq_d':2048},'masters':masters,'clock_entries':roots,'cluster_logical_entries':37,'cluster_physical_children':38,'clock_blockers':['Control and105-bit relay share one logical entry but have independently measured R; no per-child clock qualification inferred.','Top root0 RS5 stations/state not yet physically partitioned.'],'legacy_shell_row_correction':'Current submitted shcol kit is164.16x54, not old172.8x54; old801.36 assertion was a conservative legacy row reference. Exact current constituent widths and legal channel allowance determine actual cluster.','proposals':{'diagnostic_5p4_gaps':plan(5.4,2.16),'conservative_21p6_channels':plan(21.6,21.6)},'current_home_status':'No parent fit/clock/seam qualification; do not adopt old763.56/771.12/801.36 dimensions as current hardened parent','native_VM_profile':'W0 numerical baseline868; new static149 W1 full128SRAM proof4456f664b in progress, hypothesis869 only'}
p=ROOT/'results/arch/s81_mix4_current149_1417';p.mkdir(parents=True,exist_ok=True);(p/'constituents.json').write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps({k:{a:v[a] for a in ['width_um','height_um','leaves']} for k,v in rec['proposals'].items()},indent=1))
