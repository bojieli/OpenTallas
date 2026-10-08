#!/usr/bin/env python3
"""Endpoint-specific pad sizing from immutable predecessor reports; not signoff."""
import argparse,gzip,json,hashlib
from pathlib import Path
from qwen_embedding_pad_nldm import block,caps,table,chain

def price(paths,libs,depth):
 rows=[]
 for corner,check,guard in [('ss','max',30),('ff','min',15)]:
  lib=libs/f'asap7sc7p5t_INVBUF_RVT_{corner.upper()}_nldm_220122.lib.gz'
  txt=gzip.open(lib,'rt').read();buf=block(txt,'cell','BUFx2_ASAP7_75t_R')
  tables={k:table(buf,k) for k in ['cell_rise','cell_fall','rise_transition','fall_transition']}
  cap=caps(txt,'BUFx2_ASAP7_75t_R','A')
  for row in paths:
   if row['corner']!=corner or row['check']!=check:continue
   stages=[s for s in row['stages'] if s['cell']=='BUFx2_ASAP7_75t_R' and s['pin'].endswith('/Y')]
   assert len(stages) in (4,5), row
   pol=row['polarity'];old=sum(s['increment_ps'] for s in stages)
   wire=max(0,max(s['cap_ff']-cap[pol] for s in stages[:-1]))
   # Use the actual predecessor final fanout capacitance. Preserve inverter and
   # net delays, clock/constraint and endpoint requirements in the delta model.
   def estimate(w):
    slew=150.;delay=0.;extrapolated=False
    from qwen_embedding_pad_nldm import interpolate
    for i in range(depth):
     load=cap[pol]+w if i<depth-1 else stages[-1]['cap_ff']
     d,e=interpolate(tables['cell_'+pol],slew,load)
     slew,_=interpolate(tables[pol+'_transition'],slew,load)
     delay+=d;extrapolated|=bool(e)
    return delay,extrapolated
   delay,extra=estimate(wire if corner=='ss' else 0)
   delta=delay-old
   projected=row['slack_ps']+(-delta if corner=='ss' else delta)
   rows.append(dict(kind=row['kind'],input=row['input'],endpoint=row['endpoint'],corner=corner,polarity=pol,
      original_slack_ps=row['slack_ps'],old_buffer_count=len(stages),old_buffer_delay_ps=old,
      final_load_ff=stages[-1]['cap_ff'],observed_max_internal_wire_cap_ff=wire,
      proposed_buffer_count=depth,proposed_buffer_delay_ps=delay,delay_delta_ps=delta,
      projected_slack_ps=projected,analytical_guard_ps=guard,guarded_estimate_ps=projected-guard,
      sensitivity_delay_zero_wire_ps=estimate(0)[0],sensitivity_delay_one_ff_wire_ps=estimate(1)[0],
      extrapolated=extra))
 return rows

def main():
 p=argparse.ArgumentParser();p.add_argument('--paths',type=Path,required=True);p.add_argument('--libs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 paths=json.loads(a.paths.read_text());result=dict(schema='opentallas.qwen.embedding_pad_endpoint_price.v1',source_paths_sha256=hashlib.sha256(a.paths.read_bytes()).hexdigest(),
  limitations=['Analytical delta only, not closure; real SS/FF+15ps and DRC0 remain mandatory.', 'Next-buffer loads fall below characterized minimum; linear extrapolation is flagged.', 'Wire capacitance is predecessor-based; placement and clock changes are not guaranteed by an analytical guard.', 'Only BUFx2 delays replaced; actual inverter, wire, endpoint and clock terms retained.'],depths={})
 for depth in (8,9,10,11):
  rows=price(paths,a.libs,depth)
  mins={k:{c:min(r['guarded_estimate_ps'] for r in rows if r['kind']==k and r['corner']==c) for c in ('ss','ff')} for k in ('code','scale')}
  result['depths'][str(depth)]=dict(min_guarded_ps=mins,rows=rows,all_paths_estimate_above15=all(r['guarded_estimate_ps']>=15 for r in rows))
 a.out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({n:{'min':r['min_guarded_ps'],'pass':r['all_paths_estimate_above15']} for n,r in result['depths'].items()},indent=2))
if __name__=='__main__':main()
