"""Actual-source INV->oneBUF8 input-leg NLDM, not a downstream route model."""
import json,sys,math
from pathlib import Path
R=Path(__file__).parent
sys.path.insert(0,str(R/'tool_snapshot/tools/die_plan'))
from die_clock_128 import _bilin
A=json.loads((R/'postbuffer_ledger.json').read_text());L=json.loads((R/'stage_lib.json').read_text())['corners']
rows=[]
for h in A['heads']:
 cvals={}
 for c in ['TT','FF']:
  cell=L[c]['cells'][h['source_master']];wire=h['first_wire_um'];cw=wire*.187*1.7;rw=wire*.0125096
  cap=h['source_inv_actual_loads'][0]['input_cap_ff'][c]
  el=rw*(cw/2+cap);v=[]
  for ins in [5,80]:
   for edge in ['rise','fall']:
    d=_bilin(cell['cell_'+edge],ins,cw+cap)+el
    s=math.hypot(_bilin(cell[edge+'_transition'],ins,cw+cap),2.2*el)
    v.append([d,s])
  cvals[c]={'delay_ps':[min(x[0] for x in v),max(x[0] for x in v)],'max_output_slew_ps':max(x[1] for x in v),'actual_input_cap_ff':cap,'total_load_ff':cw+cap}
 rows.append({'region':h['region'],'signal':h['signal'],'master':h['source_master'],'wire_um':wire,'corners':cvals,'downstream_known_static_load_ff':h['head_known_static_load_ff'],'unknown_native_load':h['head_unknown_native_load']})
summary={c:{'max_source_inv_output_slew_ps':max(r['corners'][c]['max_output_slew_ps'] for r in rows),'delay_ps':[min(r['corners'][c]['delay_ps'][0] for r in rows),max(r['corners'][c]['delay_ps'][1] for r in rows)]} for c in ['TT','FF']}
out={'scope':'347 actual mapped source INV -> literal single BUF8A, explicit source-home first-leg Manhattan construction (MODEL, not routed); stock TTFF NLDM, input INV slew5..80ps, M6/7 maxRC1.7coupling. The downstream BUF8Y, clockQ, source timing, nativeBTerm loads and global routes are NOT qualified by this bounded leg estimate.','summary':summary,'source_records':len(rows),'unknown_native_load_records':sum(bool(r['unknown_native_load']) for r in rows),'build_allowed':False,'rows':rows}
(R/'postbuffer_input_leg_model.json').write_text(json.dumps(out,indent=1)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=1))
