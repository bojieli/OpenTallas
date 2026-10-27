import json,subprocess,sys,math
from pathlib import Path
root=Path('/srv/opentallas-scratch2/claude/wt/codex-flow-2004');sys.path.insert(0,str(root/'tools/die_plan'))
import schema as S,gen_phys as G,hold_demand as H
repo='/home/ubuntu/OpenTallas'
def read(ref,path):return json.loads(subprocess.check_output(['git','-C',repo,'show',f'{ref}:{path}']))
ref='b6b245b1d1';frag=read(ref,'results/qc_clk_mesh3/hold_demand_fragment.json');raw=read(ref,'physical/die_plan/qwen_compute/die_plan.json');raw['clock'].update(frag['clock']);p=S.Plan(raw)
pairs=frag['clock']['hold_demand']['pairs'];bits={k:0 for k in pairs};missing={}
for name,port in p.ports.items():
 a,b=port['src']['part'],port['dst']['part']
 if '@die' in (a,b):continue
 key='|'.join(sorted((a,b)));n=int(port.get('width',1))
 if key in bits:bits[key]+=n
 else:missing[key]=missing.get(key,0)+n
ff=H.HOLD_CELLS['HB4xp67']['ff_min_ps']*H.DATA_DERATE['cell_early'];hold=12.28
rows=[]
for key,d in pairs.items():
 n=math.ceil((hold+float(d))/ff-1e-9);rows.append(dict(pair=key,bits=bits[key],demand_ps=d,cells_per_bit=n,cells=bits[key]*n))
# Build-time type port contracts take the worst instance, excluding channels/scalars.
portrows=[]
for tn,t in p.types.items():
 im=G.input_hold_min(p,tn);widths={}
 for bus,bit,*_ in G.type_pins(p,tn):widths[bus]=max(widths.get(bus,0),bit+1)
 replicas=sum(x['type']==tn for x in p.parts.values())
 for bus,budget in im.items():
  pad=max(0,hold+12.5-budget['in_min_ps']);n=math.ceil(pad/ff-1e-9);w=widths.get(bus,0)
  portrows.append(dict(type=tn,port=bus,width=w,instances=replicas,in_min_ps=budget['in_min_ps'],cells_per_bit=n,cells=w*replicas*n))
summary=dict(source=ref,basis='UNCHECKED model count, not measured physical closure; hold12.28ps + demand; HB4ff46.90*.95; defaultsender12.5',pairs=len(pairs),bits=sum(bits.values()),pair_cells=sum(x['cells'] for x in rows),pair_area_mm2=sum(x['cells'] for x in rows)*.1021/1e6,pair_cells_per_bit=sorted(set(x['cells_per_bit'] for x in rows)),demand_ps=[min(pairs.values()),max(pairs.values())],type_port_model_cells=sum(x['cells'] for x in portrows),type_port_area_mm2=sum(x['cells'] for x in portrows)*.1021/1e6,uncovered_pairs=missing,zero_bits_pairs=[k for k,v in bits.items() if not v],pair_rows=rows,type_port_rows=portrows)
out=root/'results/hold_pad_dispatch_1026/mesh3_count.json';out.write_text(json.dumps(summary,indent=1)+'\n');print(json.dumps({k:v for k,v in summary.items() if k not in ['pair_rows','type_port_rows','uncovered_pairs']},indent=1));print('uncovered_pairs',len(missing))
