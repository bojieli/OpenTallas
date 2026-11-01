#!/usr/bin/env python3
import json,re,math,statistics
from pathlib import Path
r=Path('/srv/opentallas-scratch2/claude/codex-kv-residuals-1101/hubei/ff');text=(r/'rtl/kv3_hub_Ei_part_bound.sv').read_text();cells=[]
for line in (r/'geom_final1131/geom.tsv').open():
 f=line.rstrip().split('\t')
 if f[0]=='C' and f[2]=='S':cells.append((f[8],(float(f[4])+float(f[6]))/2,(float(f[5])+float(f[7]))/2))
def xy(prefix):
 q=[p[1:] for p in cells if p[0].startswith(prefix)];assert q,prefix
 return tuple(statistics.median(p[i] for p in q) for i in [0,1])
base=xy('u_bound.u_rst_in/');origin=xy('u_bound.u_cland_origin/');rows=json.loads(Path('actual_crossings.json').read_text())['rows'];ins=sorted({p['dst_bus'] for p in rows if p['dst']=='hub_Ei'});outs=sorted({p['src_bus'] for p in rows if p['src']=='hub_Ei'})
chain=['rst_rl_59','rst_rl_60','rst_rl_61','rst_rl_65','rst_rl_68','rst_n_t3'];parent='rst_root_n'
for q in chain:
 m=re.findall(r'ot_dp_rrelay\s+\w+\s*\(([^;]*?\.q\(\s*'+re.escape(q)+r'\s*\)[^;]*?)\);',text,re.S);assert len(m)==1
 pins=dict(re.findall(r'\.(clk|d|q)\(\s*(\w+)\s*\)',m[0]));assert pins['clk']=='clk' and pins['d']==parent;(parent:=q)
clock={'landing_reader_start':{'depth':7,'branches':{}},'landing_writer_start':{'depth':7,'branches':{}},'landing_raw_branches':[]};hops=[];rawhops=[]
for mode,buses in [('reader',ins),('writer',outs)]:
 for bus in buses:
  pref='u_bound.u_cland_'+bus+'/' if mode=='reader' else 'u_bound.u_cland_fstart_'+bus+'/'
  end=xy(pref);stages=[]
  for i in range(7):
   pos=[round(origin[k]+(end[k]-origin[k])*(i+1)/7,5) for k in [0,1]];stages.append({'xy_um':pos,'raw_reset':'rst_n_t3'})
   role=f'{mode}:{bus}:{i}';name=f'ei7_{mode}_{bus}_{i}';raw=[];prev=base
   for j,q in enumerate(chain):
    pt=[round(base[k]+(pos[k]-base[k])*(j+1)/len(chain),5) for k in [0,1]];raw.append({'original':q,'xy_um':pt});rawhops.append(abs(pt[0]-prev[0])+abs(pt[1]-prev[1]));prev=pt
   clock['landing_raw_branches'].append({'name':name,'base':'rst_root_n','stages':raw,'consumers':[role]})
  prev=origin
  for s in stages:
   pt=s['xy_um'];hops.append(abs(pt[0]-prev[0])+abs(pt[1]-prev[1]));prev=pt
  clock[f'landing_{mode}_start']['branches'][bus]={'stages':stages}
# Also literal reset branch near original origin; no original relay movement or tap substitution.
clock['landing_raw_branches'].append({'name':'ei7_origin','base':'rst_root_n','stages':[{'original':q,'xy_um':[round(base[k]+(origin[k]-base[k])*(j+1)/len(chain),5) for k in [0,1]]} for j,q in enumerate(chain)],'consumers':['origin']})
ledger=[]
for row in rows:
 w=7 if row['src']=='hub_Ei' else 0;rdepth=7 if row['dst']=='hub_Ei' else 0;k=row['ring_k'];new=k+w-rdepth
 ledger.append({'port':row['port'],'src':row['src'],'dst':row['dst'],'bus':row['dst_bus'],'base_k':k,'candidate_k':new,'kw':6,'strap_bits':new%(1<<6),'ring_depth':row['ring_depth'],'writer_start':w,'reader_start':rdepth,'crossing_boot_extra':w+rdepth,'steady_data_cycles_added':0,'qualification':'actual native CAB models cover all four observed mixed-link K classes; no arbitrary clipping'})
report={'enabled':False,'purpose':'ONE R7 disabled existing-API physical proposal, not generated/placed/adopted','input_rings':len(ins),'output_rings':len(outs),'new_start_ff':7*(len(ins)+len(outs)),'literal_raw_copy_ff':sum(len(b['stages']) for b in clock['landing_raw_branches']),'original_same_clock_chain':chain,'base':'rst_root_n','base_xy':base,'origin_xy':origin,'planned_start_hop_max_um':max(hops),'planned_raw_hop_max_um':max(rawhops),'geometric_hops_within405':max(hops)<=405 and max(rawhops)<=405,'limits':'Proposal coordinates only. Actual generated RTL literal-chain validation, macro-free legal placement, r2r/clock/fill LOOK and normal gates still required. Does not fix other8 residual reach failures or clock hierarchy. No raw boot-q equivalence claim.','clock_patch':clock,'link_ledger':ledger}
Path('r7_geometry_proposal.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['clock_patch','link_ledger']},indent=1))
