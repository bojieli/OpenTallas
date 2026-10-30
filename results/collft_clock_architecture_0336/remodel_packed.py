import json,sys,statistics,re,gzip,math
from pathlib import Path
B=Path('/srv/opentallas-scratch2/claude/codex-collft-clock-0336');A=Path('/srv/opentallas-scratch2/claude/codex-qc-a0-0336')
sys.path.insert(0,str(A/'src'));sys.path.insert(0,str(A/'natural_model/tools'));import core_infra_plan_metrics as M,die_clock_128 as C
rows=json.loads((B/'clock_sinks.json').read_text());proposal=json.loads((B/'eight_entry_proposal.json').read_text());ass=proposal['assignments'];groups={}
for a in rows:groups.setdefault(ass[a['name']]if a['root']=='clk'else a['root'],[]).append(a)
ports={t['name']:t['xy']for t in proposal['taps']};ports.update({'fclk_in_crec_rx_s1_i[0]':[61.536,2.656],'fclk_in_crec_rx_s2_i[0]':[176.608,2.656],'fclk_in_crec_tx_s1_i[0]':[292.256,990.944],'fclk_in_crec_tx_s2_i[0]':[407.584,990.944],'fclk_in_fltk_i[0]':[465.888,2.656],'fclk_in_fltv_i[0]':[469.792,2.656],'fclk_in_cland_dn_0[0]':[657.312,2.656]})
masters=['BUFx6f_ASAP7_75t_R','BUFx8_ASAP7_75t_R','BUFx12f_ASAP7_75t_R','BUFx16f_ASAP7_75t_R','BUFx24_ASAP7_75t_R'];libs={};seqcap={}
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


plans=json.load(gzip.open(B/'tree_packed_proposal.json.gz','rt'));fullmodels={};reports={}
for root,sl in plans.items():
 old_port=sl['core_tree']['clock_port'];sl['core_tree']['clock_port']=root;sl['core_clock_port']=root;sl['module']='coll_ft__cla4a25d77'
 for n in sl['core_tree']['nodes']:
  if n['parent']=='port:'+old_port:n['parent']='port:'+root
 rr=groups[root];pts={a['name']:a['xy']for a in rr};caps={a['name']:{c:seqcap[c][a['master']]for c in libs}for a in rr};sl['clock_sink_points_um']=pts;sl['clock_sink_points_source']='final FF5 actual CLK ITerm getAvgXY; census/clock_pins.tsv'
 first=next(n for n in sl['core_tree']['nodes']if n['parent'].startswith('port:'));ep=ports[root];length=sum(abs(ep[i]-first['xy_um'][i])for i in (0,1));model=None
 for c in ('TT','FF'):
  cap=libs[c][first['master']]['cap'];elmore=length*.014812*(length*.154233/2+cap);slew=math.hypot(20.,2.2*elmore)
  one=M.predict_tree(sl,{c:libs[c]},pts,caps,.014812,.154233,input_slew_ps=slew)
  if model is None:model=dict(one);model['corners']={}
  row=one['corners'][c]
  for k in ('min_ps','mean_ps','max_ps'):row[k]+=elmore
  for a in row['leaf_means']:
   for k in ('min_ps','mean_ps','max_ps'):a[k]+=elmore
  for a in row['nets']:a['input_arrival_ps']+=elmore
  row['entry_wire_model']=dict(public_entry_xy_um=ep,first_buffer=first['name'],first_xy_um=first['xy_um'],wire_um=length,input_cap_ff=cap,total_port_load_ff=cap+length*.154233,elmore_ps=elmore,source_slew_ps=20.,first_input_slew_ps=slew,via_rc='NOT extracted; source-model only')
  model['corners'][c]=row
 fullmodels[root]=model
 reports[root]=dict(build_qualified=False,sinks=len(rr),clock_cells=len(sl['core_tree']['nodes']),coordinates='actual final FF5 CLK ITerm points, actual-row/body/site-packed planned buffer centres',corners={c:{k:v for k,v in r.items()if k not in('nets','leaf_means')}for c,r in model['corners'].items()})
 print(root,json.dumps(reports[root]),flush=True)
with gzip.open(B/'packed_full_models.json.gz','wt')as f:json.dump(fullmodels,f)
with gzip.open(B/'tree_packed_actual_pins.json.gz','wt')as f:json.dump(plans,f)
(B/'packed_screen.json').write_text(json.dumps(dict(scope='MODEL ONLY actual-pin and legal-body-packed clock forest; no installation/STA/route/adoption',input_slew_ps=20.,clock_pin_caps_ff=seqcap,roots=reports),indent=1))
