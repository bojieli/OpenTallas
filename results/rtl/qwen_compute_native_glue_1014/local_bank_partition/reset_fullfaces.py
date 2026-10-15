import pathlib,json,re,hashlib
import numpy as np
from scipy.optimize import linear_sum_assignment
O=pathlib.Path('/tmp/qce-tile-glue-packing');R=pathlib.Path('/home/ubuntu/wt/q-compute-native-parents-1014');V=pathlib.Path('/tmp/qce-closed-head-views/physical/ref_tile/qkh_packet_v16/views/qkh_packet_v16')
c=json.loads((O/'fullface_candidate.json').read_text());base=json.loads(json.dumps(c));blocks=c['candidate_children'];banks=c['banks']
# Create one21.6um reset-master slot without changing the original67-bank artifact.
next(b for b in banks if b['inst']=='tx6_r0_lo').update(x=209.088,y=829.44)

def tr(b,p):
 x,y=p
 if b.get('orient')in['MY','R180']:x=b['w']-x
 if b.get('orient')in['MX','R180']:y=b['h']-y
 return [round(b['x']+x,6),round(b['y']+y,6)]
def pins(path,w,h):
 s=path.read_text();out={}
 for n,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1\n',s,re.S):
  rs=re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',body)
  if rs:
   rr=min(rs,key=lambda r:min(float(r[0]),float(r[1]),abs(w-float(r[2])),abs(h-float(r[3]))));x0,y0,x1,y1=map(float,rr);out[n]=[(x0+x1)/2,(y0+y1)/2]
 return out
vp=pins(V/'qkh_packet_v16.lef',21.6,21.6)
def node(n,x,y,level):return dict(inst=n,master='qkh_packet_v16',x=x,y=y,w=21.6,h=21.6,orient='R0',level=level,clock_xy_um=[x+vp['clk'][0],y+vp['clk'][1]],self_reset='local tie1; compiler16-edge reset initializes by D=0 capture, no self reset loop')
root=node('reset_root',393.12,664.2,1);mids=[node('reset_mid_low',32.4,572.4,2),node('reset_mid_high',340.2,850.04,2)]
branches=[node('reset_branch_w_low',5.4,400.68,3),node('reset_branch_w_mid',5.4,496.8,3),node('reset_branch_w_high0',5.4,880.2,3),node('reset_branch_w_high1',5.4,940.14,3),node('reset_branch_e_low',340.2,383.4,3),node('reset_branch_e_high',340.2,995.76,3)]
nodes=[root]+mids+branches;legs=[]
def xy(n,p):return tr(n,vp[p])
def dist(a,b):return round(abs(a[0]-b[0])+abs(a[1]-b[1]),6)
def add(kind,src,sp,sink,dp):
 a=xy(src,sp)if isinstance(src,dict)else src;b=xy(sink,dp);legs.append(dict(kind=kind,source=src['inst']if isinstance(src,dict)else'global_rst_n',source_pin=sp,sink=sink['inst'],sink_pin=dp,source_xy_um=a,sink_xy_um=b,manhattan_um=dist(a,b)))
for i in range(16):add('global_input_to_root',[449,689],'rst_n',root,f'd[{i}]')
for j,m in enumerate(mids):
 for i in range(16):add('root_to_mid',root,f'q[{j}]',m,f'd[{i}]')
for j,b in enumerate(branches):
 m=mids[0]if j!=5 else mids[1];q=[1,2,3,4,0,0][j]
 for i in range(16):add('mid_to_branch',m,f'q[{q}]',b,f'd[{i}]')
# Actual reset-pin targets.
targets=[]
for b in blocks:
 p=pins(R/b['view']/(b['master']+'.lef'),b['w'],b['h'])['rst_n'];targets.append(dict(inst=b['inst'],kind='existing_closed_child',xy_um=tr(b,p),proven=True))
for b in banks:
 if b['master']=='qkh_packet_v16':p=vp['rst_n']
 elif b['master'] in ['qwen_glue_v514','qwen_glue_v508']:p=c['speculative_face_master_pins'][b['master']]['positions']['rst_n']['xy_um'][0]
 else:
  a=json.loads((R/f"physical/ref_tile/{b['master']}/assigned_pins.json").read_text());p=a['positions']['rst_n']['xy_um'][0]
 targets.append(dict(inst=b['inst'],kind='data_bank',xy_um=tr(b,p),proven=True))
targets.append(dict(inst='residual_core_reset_TBD',kind='placeholder',xy_um=[220,720],proven=False))
slots=[(b,i)for b in branches for i in range(16)]
D=np.array([[dist(xy(b,f'q[{i}]'),t['xy_um'])for b,i in slots]for t in targets]);cost=np.where(D<=500,D,1e8+D)
rr,cc=linear_sum_assignment(cost);connections=[]
for ti,si in zip(rr,cc):
 b,i=slots[si];t=targets[ti];connections.append(dict(source=b['inst'],source_pin=f'q[{i}]',source_xy_um=xy(b,f'q[{i}]'),sink=t['inst'],sink_xy_um=t['xy_um'],sink_kind=t['kind'],sink_proven=t['proven'],manhattan_um=D[ti,si].item(),data_captures=3))
allb=blocks+banks+nodes;overlap=[];halo=[]
for i,a in enumerate(allb):
 for b in allb[i+1:]:
  dx=max(a['x']-b['x']-b['w'],b['x']-a['x']-a['w'],0);dy=max(a['y']-b['y']-b['h'],b['y']-a['y']-a['h'],0)
  if dx==0 and dy==0:overlap.append([a['inst'],b['inst']])
  if dx<5.4-1e-6 and dy<5.4-1e-6:halo.append([a['inst'],b['inst'],round(dx,6),round(dy,6)])
result=dict(status='STRUCTURAL_GEOMETRY_CANDIDATE_NOT_SOURCE_QUALIFIED',base_artifact_unchanged='fullface_candidate.json',outline_um=[449.28,1442.88],nodes=nodes,targets=targets,tree_legs=legs,target_connections=connections,body_overlaps=overlap,halo_5p4_violations=halo,boundary_violations=[b['inst']for b in allb if b['x']<0 or b['y']<0 or b['x']+b['w']>449.280001 or b['y']+b['h']>1442.880001],data_bank_changes=[dict(inst=b['inst'],old_y=next(z['y']for z in base['banks']if z['inst']==b['inst']),new_y=b['y'])for b in banks if b['y']!=next(z['y']for z in base['banks']if z['inst']==b['inst'])],captures=3,target_count=len(targets),tree_node_count=len(nodes),max_tree_leg_um=max(x['manhattan_um']for x in legs),max_target_leg_um=max(x['manhattan_um']for x in connections),target_legs_over_500=[x for x in connections if x['manhattan_um']>500],tree_legs_over_500=[x for x in legs if x['manhattan_um']>500],v16_insertion=json.loads((V/'insertion.json').read_text()),source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in[V/'qkh_packet_v16.lef',V/'insertion.json',O/'fullface_candidate.json']},reset_contract={'root_global_pin_um':[449,689],'root_d_all16_driven_by_global_reset':True,'all_mid_branch_d_all16_driven_by_one_distinct_parent_q':True,'branch_output_fanout':1,'initial_reset_edges':16,'tree_reset_pin':'local tie1 at every node, capture0 initializes tree','extra_assert_release_vs_old_parent_reset_q_edges':2,'new_bank_first_data_capture_global_edge':7,'old_unreset_face_first_data_capture_global_edge':1,'warmup_increment_edges':6},unresolved=['Residual-core reset target220,720 is a geometry placeholder, not a placed source endpoint.','Tree clock roots need independent actual parent clock qualification.','Local tie1 source/body connectivity and power PG qualification remain source/physical obligations.','Global reset asserted16edges must be proven to clear tree and bank local relay/data state before compiler issues work.','All three tree stages capture every edge with no enable; tree source exactness and negative controls are pending.','Actual extracted RC/timing/DRC/IR required; Manhattan reach is only a bound on direct pin displacement.'])
(O/'fullface_reset_tree.json').write_text(json.dumps(result,indent=2)+'\n');c['reset_tree']='reset_tree.json';c['reset_variant_data_bank_changes']=result['data_bank_changes'];(O/'fullface_candidate_with_reset.json').write_text(json.dumps(c,indent=2)+'\n')
print(json.dumps({k:result[k]for k in['tree_node_count','target_count','body_overlaps','halo_5p4_violations','boundary_violations','max_tree_leg_um','max_target_leg_um','target_legs_over_500','tree_legs_over_500']},indent=2))
# Re-evaluate existing data pin pairs for the four translated TX bank bodies.
oldpairs=json.loads((O/'fullface_per_bit_distances.json').read_text());newpairs=[]
for e in oldpairs:
 z=json.loads(json.dumps(e));n=z['leg']
 if n=='tx6_r0_r1' and int(z['bit'])<263:
  z['source_xy'][0]=round(z['source_xy'][0]-184.032,6);z['source_xy'][1]=round(z['source_xy'][1]+166.32,6)
 if n in ['s2_w_to_tx6_r0','s2_x_to_tx6_r0'] and int(z['bit'].split(':')[-1])<263:
  z['sink_xy'][0]=round(z['sink_xy'][0]-184.032,6);z['sink_xy'][1]=round(z['sink_xy'][1]+166.32,6)
 z['manhattan_um']=dist(z['source_xy'],z['sink_xy']);newpairs.append(z)
maxby={}
for e in newpairs:maxby[e['leg']]=max(maxby.get(e['leg'],0),e['manhattan_um'])
result['data_leg_recheck']={'changed_body_translation_um':[-184.032,166.32],'groups':len(maxby),'max_um':max(maxby.values()),'failed_groups':{k:v for k,v in maxby.items()if v>500},'group_maxima_um':maxby}
result['tree_leg_group_maxima_um']={k:max(z['manhattan_um']for z in legs if z['kind']==k)for k in set(z['kind']for z in legs)}
result['branch_target_counts']={b['inst']:sum(z['source']==b['inst']for z in connections)for b in branches}
result['independent_clock_roots_if_adopted']=86
(O/'fullface_reset_tree.json').write_text(json.dumps(result,indent=2)+'\n')
(O/'fullface_reset_data_distances.json').write_text(json.dumps(newpairs,separators=(',',':'))+'\n')
print('DATA_RECHECK',json.dumps(result['data_leg_recheck']));print('GROUPS',json.dumps(result['tree_leg_group_maxima_um']));print('FANOUTS',json.dumps(result['branch_target_counts']))
# Explicit pin provenance and the96-bit physical branch ABI (77 used outputs).
for t in result['targets']:
 t['pin_basis']='placeholder'if t['kind']=='placeholder'else('frozen source manifest674d57420; route pending'if t['inst'].startswith('face_')else'actual LEF or source assigned pin manifest')
for z in result['target_connections']:
 if z['sink'].startswith('face_'):z['sink_proven']=False;z['sink_pin_basis']='frozen source manifest; routed fullword master pending'
result['physical_branch_output_width']=96;result['used_branch_outputs']=77;result['unused_branch_outputs']=19
result['unresolved'].append('Five fullword face reset endpoints are from exact frozen source pin manifests, not CLOSED leaf LEFs; all fullword/native timing claims remain pending actual route.')
(O/'fullface_reset_tree.json').write_text(json.dumps(result,indent=2)+'\n')
# Exact86-root proposed ABI and Rref evidence. New body views have no timing values inferred.
clockrows=[]
def rref(view):
 p=view/'insertion.json'
 if not p.exists():return dict(Rref_tt_ps=None,Rref_ss_ps=None,Rref_ff_ps=None,Rref_basis='PENDING current master CTS/route')
 d=json.loads(p.read_text());return dict(Rref_tt_ps=d.get('tt',{}).get('boundary',{}).get('mean'),Rref_ss_ps=d.get('ss',{}).get('boundary',{}).get('mean'),Rref_ff_ps=d.get('ff',{}).get('boundary',{}).get('mean'),Rref_basis=str(p),Rref_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
for b in blocks:
 if b['master']=='ot_qwen_tile_rpair':port='ck_rp'+re.search(r'g_rb\[(\d+)\]',b['inst'])[1]
 elif b['master']=='ot_qwen_tile_node':port='ck_node'
 else:port='ck_lsl'+re.search(r'g_sl\[(\d+)\]',b['inst'])[1]
 pp=pins(R/b['view']/(b['master']+'.lef'),b['w'],b['h'])['clk'];clockrows.append(dict(port=port,inst=b['inst'],master=b['master'],xy_um=tr(b,pp),layer='M5 parent over child M4',binding='existing CLOSED master',**rref(R/b['view'])))
for b in banks:
 name=b['master']
 if name=='qkh_packet_v16':pp=vp['clk'];layer='M5';view=V
 else:
  pf=R/f'physical/ref_tile/{name}/assigned_pins.json';d=json.loads(pf.read_text());pp=d['positions']['clk']['xy_um'][0];layer=d['positions']['clk']['layer'];view=pathlib.Path('/tmp/qce-closed-head-views/physical/ref_tile')/name/'views'/name
 clockrows.append(dict(port='ck_bank_'+b['inst'],inst=b['inst'],master=name,xy_um=tr(b,pp),layer=layer,binding='proposed new parent ABI; master-specific physical qualification required',**rref(view)))
for b in nodes:clockrows.append(dict(port='ck_'+b['inst'],inst=b['inst'],master=b['master'],xy_um=xy(b,'clk'),layer='M5',binding='CLOSED reset master; proposed parent clock root',**rref(V)))
clockrows.append(dict(port='ck',inst='residual_core',master=None,xy_um=[224.652,1442.88],layer='M5',binding='existing parent face; residual sink clock still unqualified',Rref_tt_ps=None,Rref_ss_ps=None,Rref_ff_ps=None,Rref_basis='PENDING residual core CTS'))
assert len(clockrows)==86
(O/'fullface_clock_roots.json').write_text(json.dumps(dict(status='PROPOSED_ABI_NOT_INTEGRATED',count=86,rows=clockrows,note='Rref records measured boundary-mean insertion of current CLOSED views when available, not parent timing qualification. V263/V256 use currentPG3 W-clock(.096,1.308); fullword face leaf Rref remains null pending CTS.'),indent=2)+'\n')
# Native root-capture distance screen using actual CLOSEDv16 TT input arcs.
libp=V/'qkh_packet_v16_tt.lib';libs=libp.read_text();setup={}
for m in re.finditer(r'pin\("d\[(\d+)\]"\)\s*\{',libs):
 start=m.end()-1;depth=0;end=start
 for end in range(start,len(libs)):
  depth += (libs[end]=='{')-(libs[end]=='}')
  if depth==0:break
 body=libs[start:end+1];sb=body.split('timing_type : setup_rising;',1)[1]
 vals=re.findall(r'(?:rise_constraint|fall_constraint)\(scalar\)\s*\{\s*values\("([\d.eE+-]+)"\)',sb);setup[int(m[1])]=max(map(float,vals))
Rtt=result['v16_insertion']['tt']['boundary']['mean'];e=Rtt-result['v16_insertion']['tt']['boundary']['min'];screen=[]
for z in legs:
 if z['kind']!='global_input_to_root':continue
 i=int(re.search(r'\[(\d+)\]',z['sink_pin'])[1]);nom=setup[i]+Rtt+0.76*z['manhattan_um'];screen.append(dict(pin=z['sink_pin'],distance_um=z['manhattan_um'],setup_ps=setup[i],Rref_tt_ps=Rtt,wire_screen_ps=round(0.76*z['manhattan_um'],6),capture_screen_ps=round(nom,6),capture_plus_clock_extrema_ps=round(nom+e,6),budget_ps=190,margin_plus_clock_extrema_ps=round(190-nom-e,6)))
result['root_native_capture_screen']={'scope':'Analytical0.76ps/um wire-distance screen using actual routed TT leaf setup arcs and boundary-meanR; not extracted parent STA','wire_ps_per_um':0.76,'clock_extrema_capture_ps':e,'tt_lib_sha256':hashlib.sha256(libp.read_bytes()).hexdigest(),'pins':screen,'max_capture_plus_extrema_ps':max(z['capture_plus_clock_extrema_ps']for z in screen),'min_margin_ps':min(z['margin_plus_clock_extrema_ps']for z in screen)}
(O/'fullface_reset_tree.json').write_text(json.dumps(result,indent=2)+'\n')
c['proposed_bank_clock_entries']=[dict(inst=z['inst'],master=z['master'],clk_xy_um=z['xy_um'],layer=z['layer'],Rref_tt_ps=z['Rref_tt_ps'],Rref_ss_ps=z['Rref_ss_ps'],Rref_ff_ps=z['Rref_ff_ps'])for z in clockrows if z['port'].startswith('ck_bank_')]
c['clock_root_manifest']='fullface_clock_roots.json'
c['unresolved']=['Fullword face leaves use exact committed674d57420 frozen pin manifests; actual gates/CTS/routes and native interface timing are pending.','V263/V256 use currentPG3 Wclock(.096,1.308); PG2 DRT failures are not qualified views.','Control/metadata/instruction/address/fault/reset residual register inventory and residual-core clock/reset placements are unqualified.','Generic packet resets and old unreset payload/valid-only reset semantics require source proof under priced compiler warmup.','All Manhattan data/reset checks are geometry screens, not actual extracted parent STA/DRC/IR.','Independent NL packing/source binding remains open.']
(O/'fullface_candidate_with_reset.json').write_text(json.dumps(c,indent=2)+'\n')
print('NATIVE_CAPTURE_SCREEN',json.dumps({k:result['root_native_capture_screen'][k]for k in ['max_capture_plus_extrema_ps','min_margin_ps']}))
result['data_bank_changes']=[dict(inst=b['inst'],old_xy_um=[next(z['x']for z in base['banks']if z['inst']==b['inst']),next(z['y']for z in base['banks']if z['inst']==b['inst'])],new_xy_um=[b['x'],b['y']])for b in banks if [b['x'],b['y']]!=next([z['x'],z['y']]for z in base['banks']if z['inst']==b['inst'])]
for t in result['targets']:
 if t['inst'].startswith('face_'):t['proven']=False
result['root_native_capture_screen']['qualification']='Analytical screen passes by12.39947ps under0.76ps/um model; extracted parent STA still required.'
(O/'fullface_reset_tree.json').write_text(json.dumps(result,indent=2)+'\n');c['reset_variant_data_bank_changes']=result['data_bank_changes'];(O/'fullface_candidate_with_reset.json').write_text(json.dumps(c,indent=2)+'\n')
