import json,sys,statistics,re,gzip,math
from pathlib import Path
B=Path('/srv/opentallas-scratch2/claude/codex-collft-clock-0336');A=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336')
sys.path.insert(0,str(A/'src'));sys.path.insert(0,str(A/'natural_model/tools'));import core_infra_plan_metrics as M,die_clock_128 as C
rows=json.loads((B/'clock_sinks.json').read_text());proposal=json.loads((B/'eight_entry_proposal.json').read_text());ass=proposal['assignments'];groups={}
for a in rows:groups.setdefault(ass[a['name']]if a['root']=='clk'else a['root'],[]).append(a)
ports={t['name']:t['xy']for t in proposal['taps']};ports.update({'fclk_in_crec_rx_s1_i[0]':[61.536,2.656],'fclk_in_crec_rx_s2_i[0]':[176.608,2.656],'fclk_in_crec_tx_s1_i[0]':[292.256,990.944],'fclk_in_crec_tx_s2_i[0]':[407.584,990.944],'fclk_in_fltk_i[0]':[465.888,2.656],'fclk_in_fltv_i[0]':[469.792,2.656],'fclk_in_cland_dn_0[0]':[657.312,2.656]})
masters=['BUFx8_ASAP7_75t_R','BUFx12f_ASAP7_75t_R','BUFx24_ASAP7_75t_R'];libs={};seqcap={}
for corner in ('TT','FF'):
 libs[corner]=C.lib_cells(corner,str(A/'lib'),masters)
 f=next((A/'lib').glob(f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_*.lib*'));s=(gzip.open if f.suffix=='.gz'else open)(f,'rt').read()
 seqcap[corner]={}
 for master in sorted({a['master']for a in rows}):
  i=s.index('cell ('+master+')');j=s.find('\n  cell (',i+10);ss=s[i:j if j>=0 else len(s)]
  for pin,block in re.findall(r'\bpin\s*\(\s*(\w+)\s*\)\s*\{(.*?)(?=\n\s*pin\s*\(|\Z)',ss,re.S):
   if re.search(r'\bclock\s*:\s*true',block):
    m=re.search(r'\b(?:rise_)?capacitance\s*:\s*([0-9.eE+-]+)',block);assert m,(master,pin);seqcap[corner][master]=float(m[1]);break
  assert master in seqcap[corner],master
reports={};plans={};fullmodels={}
for gi,(root,rr)in enumerate(groups.items()):
 nodes=[];leaves=[];counter=[0];points={a['name']:a['xy']for a in rr};caps={a['name']:{c:seqcap[c][a['master']]for c in libs}for a in rr}
 def add(parent,xy,master):
  n='mp_collft_'+str(gi)+'_'+str(counter[0]);counter[0]+=1;nodes.append(dict(name=n,parent=parent,xy_um=list(xy),master=master));return n
 def branch(rr,parent,fromxy):
  xy=[statistics.median(a['xy'][i]for a in rr)for i in (0,1)]
  dist=sum(abs(xy[i]-fromxy[i])for i in (0,1));steps=max(1,math.ceil(dist/90))
  for k in range(1,steps):parent=add(parent,[fromxy[i]+(xy[i]-fromxy[i])*k/steps for i in (0,1)],masters[2])
  local_leaf=len(rr)<=8 and max(sum(abs(a['xy'][i]-xy[i])for i in (0,1))for a in rr)<=30
  n=add(parent,xy,masters[0]if local_leaf else masters[2])
  if local_leaf:leaves.append(dict(node=n,sinks=[a['name']for a in rr],load_class='register'));return
  axis=max((0,1),key=lambda i:max(a['xy'][i]for a in rr)-min(a['xy'][i]for a in rr));r=sorted(rr,key=lambda a:(a['xy'][axis],a['name']));mid=len(r)//2
  branch(r[:mid],n,xy);branch(r[mid:],n,xy)
 rootnode=add('port:ck',ports[root],masters[2]);branch(rr,rootnode,ports[root])
 sl=dict(module='collft_root_'+str(gi),outline_um=[786.24,993.6],core_tree=dict(clock_port='ck',stage_basis='electrical_latency',load_balance='joint_nldm_plan',latency_target_ps={'TT':250.,'FF':202.5},equal_load=False,nodes=nodes,leaves=leaves,gates=[]))
 model=M.predict_tree(sl,libs,points,caps,.018515*.8,.17137*.9,input_slew_ps=20.)
 reports[root]=dict(build_qualified=False,calibration_note='predictor valid_for_build_gating below means table calibration only, not pass of slew/geometry/phase checks',sinks=len(rr),clock_cells=len(nodes),coordinates='FF body centres from actual FF5 dump; actual CLK ITerm points still required',corners={c:{k:v for k,v in r.items()if k not in('nets','leaf_means')}for c,r in model['corners'].items()})
 plans[root]=sl;fullmodels[root]=model
 print(root,json.dumps(reports[root]),flush=True)
(B/'tree_screen.json').write_text(json.dumps(dict(scope='UNPLACED geometry/NLDM screen only; no clock timing measurements, no branch balancing, no passing build qualification',input_slew_ps=20.,wire_model='historical RCLK planning RC .014812kohm/um,.154233fF/um; no actual routed layer extraction',clock_pin_caps_ff=seqcap,roots=reports),indent=1))
with gzip.open(B/'tree_screen_plans.json.gz','wt')as f:json.dump(plans,f)

with gzip.open(B/'tree_screen_full_models.json.gz','wt')as f:json.dump(fullmodels,f)
