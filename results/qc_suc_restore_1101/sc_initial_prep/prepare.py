from pathlib import Path
import json,math,collections,hashlib,shutil
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
r=Path('/srv/opentallas-scratch2/claude/codex-qc-sc-initial-kit-1101');w=Path('/srv/opentallas-scratch2/claude/wt/codex-qc-suc');ref=w/'results/qc_suc_restore_1101/sc_ref';W,H=244.56,514.08;margin=4.32;uW,uH=W-2*margin,H-2*margin;cx,cy=W/2,H/2
sinks=json.loads((r/'clock_sink_names.json').read_text());names=sorted(n for m,n in sinks);assert len(names)==42665 and len(set(names))==42665
pg=[]
for j in range(60):
 for a,b in [(6.324,6.444),(6.516,6.636)]:
  if b+j*4.32<=W-margin:pg.append([a+j*4.32,margin,b+j*4.32,H-margin])
# Actual ASAP7 BUFx24 dimensions and row/site lattice. All tree masters uniform for the initial hypothesis.
bw,bh=1.62,.27
snap_displacements=[]
def snap(x,y):
 yy=margin+bh/2+math.floor((y-margin-bh/2)/bh+.5)*bh
 ix=math.floor((x-margin-bw/2)/.054+.5);opts=[]
 for j in range(ix-28,ix+29):
  xx=margin+bw/2+j*.054
  if xx-bw/2<margin or xx+bw/2>W-margin:continue
  if any(xx-bw/2 < b[2]+.108 and xx+bw/2 > b[0]-.108 for b in pg):continue
  opts.append((abs(xx-x),xx))
 assert opts,(x,y)
 xx=min(opts)[1];snap_displacements.append(abs(xx-x)+abs(yy-y));return [round(xx,6),round(yy,6)]
nodes=[dict(name='sc_ck_root',parent='port:ck',master='BUFx24_ASAP7_75t_R',xy_um=snap(cx,cy),island_rect_um=[cx-4.32,cy-4.32,cx+4.32,cy+4.32])];hubs=[('',cx,cy,'sc_ck_root')]
for lv in range(5):
 nx=[];ox=uW/(4*2**lv);oy=uH/(4*2**lv)
 for pref,x,y,par in hubs:
  for i,(sx,sy) in enumerate([(-1,-1),(-1,1),(1,-1),(1,1)]):
   nm='sc_ck_'+pref+str(i)+'_br';nodes.append(dict(name=nm,parent=par,master='BUFx24_ASAP7_75t_R',xy_um=snap(x,y+(i-1.5)*1.08)));nx.append((pref+str(i),x+sx*ox,y+sy*oy,nm))
 hubs=nx
leafs=[];q,rem=divmod(len(names),len(hubs));pos=0
for i,(pref,x,y,par) in enumerate(hubs):
 nm='sc_ck_'+pref+'_leaf';nodes.append(dict(name=nm,parent=par,master='BUFx24_ASAP7_75t_R',xy_um=snap(x,y)));n=q+(i<rem);leafs.append(dict(node=nm,sinks=names[pos:pos+n],load_class='register'));pos+=n
assert pos==len(names) and len(nodes)==2389
sl=dict(schema='opentallas.master_plan_slice.v1',die='qwen_compute',kind='core',type='qfd_dv_s5_sc2_leaf',module='qfd_dv_s5_sc2_leaf',instances=['SC standalone unsigned initial placement prototype only'],master_plan_sha256='qc-sc-hard1-initial-unadopted',frozen=False,outline_um=[W,H],islands=[dict(name='sc_center_entry',rect_um=[cx-4.32,cy-4.32,cx+4.32,cy+4.32],centre_um=[cx,cy],clock_pin=dict(layer='M5',xy_um=[122.268,257.04]),use='center clock driver + M9/M5 via-stack hypothesis')],keepouts=[],bays=[],entry_pins=[],core_clock_port='ck',pushdown=dict(islands=[]),latency=dict(common_clock_latency_ps=dict(TT=250,FF=202.5),tol_ps=40,early_taps=False),pg_obstructions_um=dict(M4=[],M5=pg),core_tree=dict(clock_port='ck',nodes=nodes,leaves=leafs,trunk_layers=['M4','M5'],stage_basis='node_depth',install_stage='pre_gpl',equal_load=True,post_place_rebind='exact_count'))
(r/'slices').mkdir(exist_ok=True);(r/'slices/qfd_dv_s5_sc2_leaf.json').write_text(json.dumps(sl,indent=1)+'\n');shutil.copy(ref/'pins.json',r/'pins.json')
plan=json.loads((w/'physical/die_plan/qwen_compute/plan_of_record/plan_qc52.json').read_text());plan['partition_types']['sle_sc_v2'].setdefault('hard_cores',[]).append(dict(inst='u_core',module='qfd_dv_s5_sc2_leaf',outline_um=[W,H],origin_um=[345.6,648],orient='R0',pins_file=str(r/'pins.json'),note='UNADOPTED HARD1 standalone SC initial place prototype; parent closure/event held'))
(r/'prototype_plan.json').write_text(json.dumps(plan)+'\n')
recipe={'qfd_dv_s5_sc2_leaf':dict(ref_tile='results/qc_suc_restore_1101/sc_ref',plan_type='sle_sc_v2',plan_pins_contract=True,pins_file=str(r/'pins.json'),suffix='pin1center',insertion_ps=250,insertion_ff_ps=202.5,insertion_basis='Common250/202.5 reference only; center structured tree is unqualified hypothesis until actual sink/NLDM/root-slew model',util=.45,max_layer='M5',params=dict(HARD_PINREG=1),insertion_balance=False)};(r/'recipes.json').write_text(json.dumps(recipe,indent=1)+'\n')
caps={'TT':42036*.474736+629*.462899,'FF':42036*.522010+629*.503152};clockcap={'TT':len(nodes)*2.35026,'FF':len(nodes)*2.60735};area=json.loads((r/'mapped_area.json').read_text());usable=uW*uH
model=dict(scope='PREP ONLY; not a passing clock model or physical/source/native event adoption. No P&R launched.',HARD_PINREG=1,native_parent_default=0,source_candidate_commit='2d761bce9b5',whole_source_EQ='PENDING; new explicitdeclaration source versus existing mapped classic netlist',actual_standalone_mapped=area,actual_ff_types=dict(collections.Counter(m for m,n in sinks)),actual_ff_clock_net='ck for all42665 actual mapped FFs',source_ff_delta='No added-FF count inferred from parent subtraction. Source specialization has4shared-reset captures/15flags and391redundant plain captures removed; actual whole mapped42665FFs is authoritative for this netlist. Native source event/whole-source correctness still held.',ABI=dict(ports=27,bits=572,input_bits=357,output_bits=215,clocks=['ck'],resets=['rst_n'],mapped_face_guard='570/570PASS on retained actualnetlist; currentdeclaration source EQpending'),clock_tree=dict(cells=len(nodes),masters={'BUFx24_ASAP7_75t_R':len(nodes)},clock_stages=7,leaves=1024,initial_leaf_count=[q,q+1],actual_sink_names=len(names),initial_assignment='deterministic balanced-name partition only; actualgeometry exact_count rebind afterPLACE; NO claim of current geometric sink reach',center_entry_pin_um=[122.268,257.04],geometric_center_um=[cx,cy],actual_planned_root_center_um=nodes[0]['xy_um'],center_island_um=sl['islands'][0]['rect_um'],PG_rule='M5stripe rectangles cloned from same normal corePDN phase, .108um bodyguard; actualPG/sink/body geometry unqualified until own initialfloorplan/PLACE',max_geometric_row_site_PG_snap_um=max(snap_displacements),cell_area_um2=len(nodes)*.4374,buffer_input_cap_fF=clockcap,native_DFF_clock_cap_fF=caps,added_buffer_cap_vs_DFF={c:clockcap[c]/caps[c] for c in caps}),source_plus_seed_std_cells=336662+len(nodes),source_plus_seed_fill=(area['area_um2']+len(nodes)*.4374)/usable,physical_body_um=[345.6,648,590.16,1162.08],parent_scope='Parentfold/CAread/R8actualanchors/reset+FTmoves/nativeprofile+globalclock/commonframe allHELD; no parentP&R.')
(r/'model.json').write_text(json.dumps(model,indent=2)+'\n')
fig,ax=plt.subplots(figsize=(7,10));ax.add_patch(Rectangle((0,0),W,H,facecolor='#f7f7f7',edgecolor='black'))
by={n['name']:n for n in nodes}
for n in nodes:
 if n['parent'] in by:
  a=by[n['parent']]['xy_um'];b=n['xy_um'];ax.plot([a[0],b[0],b[0]],[a[1],a[1],b[1]],color='teal',lw=.25,alpha=.4)
ax.scatter([n['xy_um'][0] for n in nodes],[n['xy_um'][1] for n in nodes],s=.4,color='black');p=json.loads((r/'pins.json').read_text())['pins']
for face,c in [('N','blue'),('E','orange'),('W','green'),('S','crimson'),('C','purple')]:
 a=[z for z in p if z['face']==face];ax.scatter([z['x'] for z in a],[z['y'] for z in a],s=3,c=c,label=f'{face} {len(a)}bits')
ax.add_patch(Rectangle((cx-4.32,cy-4.32),8.64,8.64,fill=False,edgecolor='magenta',lw=1));ax.set_aspect('equal');ax.legend(fontsize=7,loc='center left');ax.set_xlabel('local x um');ax.set_ylabel('local y um');ax.set_title('SC HARD1 unsigned child initial-PLACE PREP ONLY\nActual336662cells /42665mappedFF /572pins\nCenter entry +2389buffer seed/7clockstages\nNO clock timing/model/parent/source adoption',fontsize=10);fig.tight_layout();fig.savefig(r/'plan.png',dpi=160)
print(json.dumps({k:model[k] for k in ['source_plus_seed_std_cells','source_plus_seed_fill','actual_ff_types']},indent=2));print('nodes',len(nodes),'snapmax',max(snap_displacements))
