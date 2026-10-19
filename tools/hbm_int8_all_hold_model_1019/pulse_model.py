import pathlib,json,gzip,re
from lib_native import blocks,vec
P=pathlib.Path(__file__).parent;B=pathlib.Path('/srv/opentallas-scratch/claude/hbm-int8-cts-v2-run-1019');new=json.load(open(P/'full_scope_model.json'));old=json.load(open(P/'integrated_inputs/integrated_model.json'));out={}
for co in ['TT','FF']:
 f=next((B/'input/native_libs').glob('*SEQ*'+co+'*.lib*'));s=gzip.open(f,'rt').read() if f.suffix=='.gz' else f.read_text();body=next(b for n,b in blocks(s,'cell') if n=='DFFASRHQNx1_ASAP7_75t_R');ps=dict(blocks(body,'pin'));tables=[]
 for pn,pb in ps.items():
  for _,tb in blocks(pb,'timing'):
   if not re.search(r'timing_type\s*:\s*min_pulse_width',tb):continue
   when=re.search(r'when\s*:\s*"([^"]*)"',tb)
   for k in ['rise_constraint','fall_constraint']:
    for _,t in blocks(tb,k):tables.append(dict(pin=pn,edge=k,when=when[1] if when else None,index_1=vec(t,'index_1'),values=vec(t,'values')))
 resetcases=[dict(net='5549',wave=new['native'][co]['cases']['DFFASRHQNx1_ASAP7_75t_R/RESETN']['final_slew_with25ps_wire_bound'],chain=new['native'][co]['cases']['DFFASRHQNx1_ASAP7_75t_R/RESETN']['chain_minmax_ps'])]+[dict(net=n,wave=r['final_reset_slew_with_25ps_wire_budget'],chain=r['chain_total_min_max_ps']) for n,r in old[co]['reset'].items()]
 for r in resetcases:
  vals=[]
  for t in tables:
   if t['pin']!='RESETN':continue
   x=t['index_1'];v=t['values'];assert x[0]<=r['wave'][0]<=r['wave'][1]<=x[-1]
   for q in [r['wave'][0],r['wave'][1]]+[z for z in x if r['wave'][0]<=z<=r['wave'][1]]:
    i=min(len(x)-2,max(0,next((i-1 for i,z in enumerate(x) if z>=q),len(x)-2)));w=(q-x[i])/(x[i+1]-x[i]);vals.append(v[i]+w*(v[i+1]-v[i]))
  # Source is an ordinary synchronous sampled-reset QN. One cycle minimum pulse.
  # Reserve70ps original-driver asymmetry and20ps added-wire asymmetry; bounds must be verified.
  r['native_all_conditional_minimum_low_pulse_max_ps']=max(vals);r['conditional_one_cycle_low_pulse_bound_ps']=833.333-(r['chain'][1]-r['chain'][0])-70-20;r['conditional_pulse_margin_ps']=r['conditional_one_cycle_low_pulse_bound_ps']-max(vals)
 out[co]=dict(all_native_ASR_pulse_tables=tables,changed_reset_cases=resetcases)
json.dump(dict(schema='int8.reset.native_pulse.source_model.v1',claim='Conditional one-cycle synchronous sampled reset pulse budget; preserve actual source edge calendar. All one-dimensional Liberty pulse tables and conditions retained, no fake second dimension. TT/FF native pulse replay still required. CLK and SETN terminals unchanged.',corners=out),open(P/'pulse_model.json','w'),indent=2)
for co,r in out.items():print(co,'nativepulsemodel minimum',min(x['conditional_pulse_margin_ps'] for x in r['changed_reset_cases']))
