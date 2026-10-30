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

plans=json.load(gzip.open(B/'tree_balanced_proposal.json.gz','rt'));fullmodels={};reports={}
for root,sl in plans.items():
 rr=groups[root];pts={a['name']:a['xy']for a in rr};caps={a['name']:{c:seqcap[c][a['master']]for c in libs}for a in rr}
 model=M.predict_tree(sl,libs,pts,caps,.018515*.8,.17137*.9,input_slew_ps=20.);fullmodels[root]=model
 reports[root]=dict(build_qualified=False,sinks=len(rr),clock_cells=len(sl['core_tree']['nodes']),coordinates='actual FF5 FF body centres; actual clock ITerm points and placement still required',corners={c:{k:v for k,v in r.items()if k not in('nets','leaf_means')}for c,r in model['corners'].items()})
 print(root,json.dumps(reports[root]),flush=True)
with gzip.open(B/'balanced_full_models.json.gz','wt')as f:json.dump(fullmodels,f)
(B/'balanced_screen.json').write_text(json.dumps(dict(scope='UNPLACED common-branch clock model; no physical/STA/adoption claim',input_slew_ps=20.,clock_pin_caps_ff=seqcap,roots=reports),indent=1))
