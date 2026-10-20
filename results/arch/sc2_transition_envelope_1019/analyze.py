#!/usr/bin/env python3
import json,pathlib,math,hashlib,random
from envelope import envelope,evaluate,witnesses
P=pathlib.Path(__file__).resolve().parent
records=json.loads((P/'native_tables.json').read_text())
results=[];comparisons=0
for r in records:
 for a in r['arcs']:
  expected=evaluate(a['table'],*a['query'])[0]
  assert math.isclose(expected,a['value'],rel_tol=3e-6,abs_tol=1e-17),(a['role'],expected,a['value'])
  comparisons+=1
  if 'transition_table' in a:
   expected=evaluate(a['transition_table'],*a['query'])[0]
   assert math.isclose(expected,a['transition_raw'],rel_tol=3e-6,abs_tol=1e-17)
   comparisons+=1
for inst in ('dependent','launch','capture'):
 sample=next(r for r in records if r['instance']==inst and r['bound']=='min')
 for a in sample['arcs']:
  # Wide common research domain includes all three conditional RC envelopes.
  # Clock and data are independent full axes for checks, not a diagonal sweep.
  domain=[[0,1000e-12],[0,46.08e-15]] if inst!='capture' else [[0,1000e-12],[0,1000e-12]]
  e=envelope(a['table'],domain)
  for _ in range(200):
   x=random.Random(_).uniform(*domain[0]);y=random.Random(_+201).uniform(*domain[1]);v=evaluate(a['table'],x,y)[0]
   assert e['lower']<=v<=e['upper']
  row=dict(instance=inst,role=a['role'],rf=a['rf'],domain_si=domain,delay_or_check=e)
  if 'transition_table' in a:row['output_transition']=envelope(a['transition_table'],domain,output_transition=True)
  results.append(row)
for lo,hi in zip(records[:len(records)//2],records[len(records)//2:]):
 assert lo['instance']==hi['instance'] and lo['arcs']==hi['arcs'], 'same-corner baseline roles must be identical'
i=json.loads((P/'input.json').read_text());m=json.loads((P/'access_model.json').read_text())
models={}
for c in ('tt','ss','ff'):
 b=i['timing'][c]['base'];a=m['timing'][c]
 s=b['out_slew_intrinsic_ps']+2.2*b['out_r_kohm']*46.08
 # Explicit new conditional waveform interpretation: monotone exponential
 # source step whose mean is its modeled 10-90 transition / ln(9), cascaded
 # with a nonnegative normalized passive RC impulse response. Markov gives
 # 90% arrival <=10*(mean_source+mean_access); 10% arrival >=0.
 models[c]=dict(generator_transition_at_max_load_ps=s,generator_transition_min_load_ps=b['out_slew_intrinsic_ps']+2.2*b['out_r_kohm']*.72,
  old_planner_writer_formula_upper_ps=a['output_slew_intrinsic_upper_ps']+2.2*a['max_output_r_kohm']*46.08,
  conditional_waveform_interval_ps=[0,10*(s/math.log(9)+max(a['output_lead_delay_upper_ps_by_load_ff'].values()))],
  proposed_setup_upper_over_0_1000_ps=b['setup_ps']+a['clock_lead_delay_upper_ps']+a['input_lead_delay_upper_ps']+249.25,
  proposed_hold_upper_over_0_1000_ps=b['hold_ps']+a['clock_lead_delay_upper_ps']+100.75,
  native_320ps_domain_exceeded=True,physical_characterization_claim=False,production_admission=False)
summary=dict(status='ANALYTICAL_AND_NATIVE_API_RESEARCH_ONLY',native_lookup_comparisons=comparisons,witnesses=witnesses(),
  models=models,envelopes=results,scope='Native piecewise bilinear LUT mathematical extrema; explicit extrapolation, no characterization-domain expansion or production integration.')
z=next(r for r in records if r['instance']=='dependent' and r['bound']=='min' and r['arcs'][0]['query']==[0,0.72e-15])
f=next(r for r in records if r['instance']=='dependent' and r['bound']=='min' and r['arcs'][0]['query']==[5e-12,0.72e-15])
summary['native_zero_vs_5ps']=[dict(rf=a['rf'],zero_delay_ps=a['value']*1e12,five_delay_ps=b['value']*1e12) for a,b in zip(z['arcs'],f['arcs'])]
assert all(abs(a['value']-b['value'])>1e-15 for a,b in zip(z['arcs'],f['arcs']))
(P/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
print('LOOKUP_AND_ENVELOPE_PASS',comparisons,'native lookups;',len(results),'arc/check envelopes')
