"""Build proposed 23-cut clock input/area budget; no STA, placement, or view adoption."""
import json,math,re
from pathlib import Path
P=Path('/srv/opentallas-scratch2/claude/codex-kvleaf-clock-0336');O=P/'prepared';O.mkdir(exist_ok=True)
load=lambda n:json.loads((P/n).read_text())
ref=load('natural_cut_reference.json');census=load('parent_census.json');libs=load('native_libcaps.json');sr=load('sram_contracts.json')
W,H=1442.88,1226.88;halo=4.32
roots=[{'pin':m[0],'xy_um':[float(m[1]),float(m[2])],'layer':'M7','provenance':'actual private 23-cut kit io.tcl; not current adopted plan'} for m in re.findall(r'place_pin -pin_name (clk(?:_t\d+)?) -layer M7 -location \{([\d.]+) ([\d.]+)\}',(P/'reference_io.tcl').read_text())]
assert len(roots)==16
moves={'u_lf.u_vsw':[51.84,514.08],'u_lf.u_vn.u_a':[609.12,501.12],'u_lf.u_ve.u_m':[185.76,829.44],'u_lf.u_ve.u_s':[371.52,838.08],'u_lf.u_rxsf':[388.8,440.64]}
children=[]
for row in ref['core_rows']:
 i=row['source_plan_inst']
 if i=='u_lf.u_vn.u_b' or row['source_interface']['module'].endswith('_vn_b'):continue
 b=row['known_parent_placement'];xy=moves.get(i,b['origin_um']);w,h=b['outline_um'];clock='ck' if 'rxs' in row['source_interface']['module'] else 'clk'
 assert clock in row['source_interface']['ports'],(i,clock)
 children.append({'inst':i,'source_interface':row['source_interface'],'clock_port':clock,'reference_geometry':b,'proposed_origin_um':xy,'body_um':[w,h],'orient':b['orient'],'clock_input_proposal':{'pin':clock,'local_xy_um':[.012,round(h/2,6)],'root_master':'BUFx24_ASAP7_75t_R','basis':'PROPOSED west-face entry feeding planned native BUF24 root; no measured child pin/cap/timing claim','cap_fF':{c:libs['corners'][c]['cells']['BUFx24_ASAP7_75t_R']['capacitance'] for c in ('TT','FF')}},'qualification':'MODEL_ONLY; exact source/parameters/ABI and new native full views remain required'})
assert len(children)==23,len(children)
masters={x['master']:x for x in sr['variants'][0]['macro_masters']};sram=[]
for n,(kind,y) in enumerate([(512,885.6),(512,928.8),(128,972),(128,1028.16)]):
 master=next(v for k,v in masters.items() if f'_{kind}x' in k);xy=[635.04,y]
 sram.append({'inst':f'PROPOSED_REAL_SRAM_{n}','master':master['master'],'body_um':master['body_um'],'proposed_origin_um':xy,'placement_basis':'proposed tower, not measured parent placement','clock_port':'clk','clock_xy_um':[xy[0]+.012,y+.780],'cap_fF':{c:master['corners'][c]['clock_pins'][0]['capacitance_fF'] for c in ('TT','FF')}})
def rect(x):
 a,b=x['proposed_origin_um'];w,h=x['body_um'];return (a,b,a+w,b+h)
def intersect(a,b):return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
blocks=children+sram;boxes=[rect(x) for x in blocks];issues=[]
for i,a in enumerate(boxes):
 if min(a)<0 or a[2]>W or a[3]>H:issues.append(['bounds',blocks[i]['inst']])
 for j,b in enumerate(boxes[:i]):
  if intersect((a[0]-halo,a[1]-halo,a[2]+halo,a[3]+halo),b):issues.append(['body_halo',blocks[i]['inst'],blocks[j]['inst']])
 for root in roots:
  x,y=root['xy_um'];reserve=(x-5.184,y-4.86,x+5.184,y+4.86)
  if intersect(a,reserve):issues.append(['clock_root_keepout',blocks[i]['inst'],root['pin']])
assert not issues,issues
xs=sorted(set(x['xy_um'][0] for x in roots));ys=sorted(set(x['xy_um'][1] for x in roots))
xb=[0]+[(a+b)/2 for a,b in zip(xs,xs[1:])]+[W];yb=[0]+[(a+b)/2 for a,b in zip(ys,ys[1:])]+[H]
areas=[]
for root in roots:
 x,y=root['xy_um'];ix=xs.index(x);iy=ys.index(y);r=(xb[ix],yb[iy],xb[ix+1],yb[iy+1]);a=(r[2]-r[0])*(r[3]-r[1]);a-=sum(intersect(r,(b[0]-halo,b[1]-halo,b[2]+halo,b[3]+halo)) for b in boxes);areas.append(a)
assert min(areas)>0
# Expanded halos may overlap: subtracting their sum is conservative free-area lower bound.
def alloc(n):
 raw=[n*a/sum(areas) for a in areas];v=[int(x) for x in raw]
 for i in sorted(range(16),key=lambda i:raw[i]-v[i],reverse=True)[:n-sum(v)]:v[i]+=1
 return v
def tree(n):
 count=0;levels=0
 while n>1:n=math.ceil(n/8);count+=n;levels+=1
 return count,levels
terminals=[]
for child in children:
 x,y=child['proposed_origin_um'];u,v=child['clock_input_proposal']['local_xy_um']
 terminals.append({'inst':child['inst'],'pin':child['clock_port'],'xy_um':[x+u,y+v],'cap_fF':child['clock_input_proposal']['cap_fF'],'basis':'PROPOSED child entry, scalar ABI source verified; native entry unknown'})
for ram in sram:terminals.append({'inst':ram['inst'],'pin':'clk','xy_um':ram['clock_xy_um'],'cap_fF':ram['cap_fF'],'basis':'native SRAM local clock shape + PROPOSED placement'})
for t in terminals:
 root=min(roots,key=lambda r:sum(abs(a-b) for a,b in zip(r['xy_um'],t['xy_um'])))
 t['proposed_core_root']=root['pin'];t['manhattan_to_root_um']=sum(abs(a-b) for a,b in zip(root['xy_um'],t['xy_um']))
 t['proposed_repeater_segments_200um']=math.ceil(t['manhattan_to_root_um']/200)
variants=[]
for row in census['rows']:
 cells=row['flop_types'];pop=alloc(row['flops']);per=[]
 for root,n,a in zip(roots,pop,areas):
  leaves=math.ceil(n/48);hard=[t for t in terminals if t['proposed_core_root']==root['pin']];branches,depth=tree(leaves+len(hard))
  per.append({'root':root['pin'],'proposed_soft_ff':n,'free_area_lower_bound_um2':a,'ff_leaves_48':leaves,'non_ff_terminal_budget':len(hard),'hard_terminal_cap_fF':{c:sum(t['cap_fF'][c] for t in hard) for c in ('TT','FF')},'branch_buffers_upper_budget':branches,'branch_depth_upper_budget':depth,'basis':'MODEL spatial population proportional to free area; native FF placement unknown. Hard terminals assigned by nearest root using proposed entry coordinates; 200um chain segments separate geometry budget, not delay proof.'})
 caps={c:sum(count*libs['corners'][c]['cells'][m]['capacitance'] for m,count in cells.items()) for c in ('TT','FF')}
 variants.append({'type':row['type'],'measured_parent_census':row,'soft_ff_total_clock_pin_cap_fF':caps,'distributed_tree':per,'ff_leaf_count_bounds':{str(n):math.ceil(row['flops']/n) for n in (32,48,64)},'clock_bom_budget':{'ff_leaf_buffers':sum(x['ff_leaves_48'] for x in per),'branch_buffers_conservative':sum(x['branch_buffers_upper_budget'] for x in per),'hard_terminal_roots':23,'die_input_roots':16,'buffer_body_envelope_um':[1.62,.27]},'standard_cell_utilization_of_free_area':row['standard_cell_area_um2']/sum(areas),'clock_timing_status':'UNRUN: source/capacity model only; no latency/window/slew prediction or 833ps qualification','cycles_added':0})
packet={'schema':'opentallas.kvleaf23.proposed_clock_input.v1','status':'MODEL_INPUT_PREP_NOT_ADOPTED','outline_um':[W,H],'die_core_roots':roots,'other_clock_inputs':{'fclk_in_ft3_i':[35.232,2.656],'fclk_in_ft4_i':[217.952,2.656],'scope':'actual io.tcl forwarded-clock roles; excluded from proposed core clock FF grid, not silently merged'},'children':children,'real_sram_loads':sram,'hard_clock_terminals':terminals,'geometry_checks':{'body_and_halo_overlap':issues,'clock_input_reserve_halfsize_um':[5.184,4.86],'macro_halo_um':halo,'free_area_lower_bound_um2':sum(areas),'qualification':'Analytical proposal only. Actual PG openings, rows, clock access and track phases must be reviewed.'},'variants':variants,'blocking_contracts':['Native parent 594 data+epoch versus plan597 ABI remains unresolved; no remapping inferred.','Child ordinary mapped FF/area and current exact-source full views unqualified. Footprints reference templates; proposed BUF24 roots give explicit input load contracts, not measured hardened-child input caps.','Actual FF spatial distribution, 16 input phases and child clock insertion windows unknown; no homogeneous phase assumption.','The four actual SRAM master/pin/cap contracts are measured; their tower placement is proposed.','Budget does not qualify postplacement wires, PG, DRC, NLDM timing, or full 833ps clock gates.'],'native_libcaps':libs,'real_sram_contract_source':sr}
(O/'model_inputs.json').write_text(json.dumps(packet,indent=2)+'\n')
print(json.dumps({'children':len(children),'sram':len(sram),'roots':len(roots),'free_area':sum(areas),'variants':[{k:v[k] for k in ('type','clock_bom_budget','standard_cell_utilization_of_free_area')} for v in variants]},indent=2))
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig,ax=plt.subplots(figsize=(10,9))
for b,x in zip(boxes,blocks):
 ax.add_patch(Rectangle(b[:2],b[2]-b[0],b[3]-b[1],facecolor='#d7e4f2' if x in children else '#f2d5ac',edgecolor='#41566b',lw=.7));ax.text((b[0]+b[2])/2,(b[1]+b[3])/2,x['inst'].replace('u_lf.','').replace('PROPOSED_REAL_SRAM_','RAM'),ha='center',va='center',fontsize=5)
for root in roots:
 x,y=root['xy_um'];ax.scatter([x],[y],c='red',s=14);ax.text(x,y+10,root['pin'],fontsize=6,ha='center')
ax.set(xlim=(0,W),ylim=(0,H),aspect='equal',xlabel='um',ylabel='um',title='KVleaf23 proposed bodies / four real RAM contracts / 16 retained core inputs\nMODEL INPUT PREP — no ABI/PG/clock qualification')
fig.tight_layout();fig.savefig(O/'proposed_geometry.png',dpi=170)
