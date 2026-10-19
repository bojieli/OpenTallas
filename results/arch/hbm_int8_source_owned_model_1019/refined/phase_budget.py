"""Source-only all-sink native cell interval bound, common root canceled.
No actual RC, actual slew or physical skew assertion.
"""
import json,gzip,pathlib
P=pathlib.Path(__file__).parent
j=json.load(gzip.open(P/'clock_family_compare.json.gz','rt'));by={r['driver']:r for r in j['selected']};root='MODEL_clock_l0_0';rows=[]
def walk(n,acc,afterroot):
 r=by[n];full={c:[acc[c][k]+r['corners'][c]['native_cell']['delay_ps'][k] for k in (0,1)] for c in ('TT','FF')};div={c:[afterroot[c][k]+(0 if n==root else r['corners'][c]['native_cell']['delay_ps'][k]) for k in (0,1)] for c in ('TT','FF')}
 for s in r['children']:
  if s['cell'] in by:walk(s['cell'],full,div)
  else:rows.append(dict(sink=s,native_cell_only_arrival_ps=full,common_root_cancelled_native_cell_arrival_ps=div,actual_wire_phase=None))
walk(root,{c:[0,0] for c in ('TT','FF')},{c:[0,0] for c in ('TT','FF')});assert len(rows)==2892
summary=dict(status='NATIVE_CELL_INTERVAL_BOUND_ONLY_NO_WIRE_PHASE_QUALIFICATION',real_sinks=len(rows),common_root_cancelled_spread_upper_bound_ps={c:max(r['common_root_cancelled_native_cell_arrival_ps'][c][1] for r in rows)-min(r['common_root_cancelled_native_cell_arrival_ps'][c][0] for r in rows) for c in ('TT','FF')},native_cell_total_arrival_range_ps={c:[min(r['native_cell_only_arrival_ps'][c][0] for r in rows),max(r['native_cell_only_arrival_ps'][c][1] for r in rows)] for c in ('TT','FF')},actual_wire_delay=None,actual_wire_slew=None,root_actual_input_waveform=None,actual_spread80_qualification=False)
(P/'clock_native_phase_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with gzip.open(P/'clock_native_phase_budget.json.gz','wt') as f:json.dump(rows,f)
print(summary)
