#!/bin/bash
set -euo pipefail
mkdir -p retained
yosys -Q -T -p 'read_json candidate/candidate.json; write_verilog retained/qfd_dv_stream_controls.v; design -reset; read_liberty -lib mapped/combined.lib; read_verilog retained/qfd_dv_stream_controls.v; hierarchy -top qfd_dv_stream_controls; proc; techmap; opt_clean; write_json retained/reimport.json; stat' > retained/reimport.log 2>&1
python3 - <<'PY'
import json,collections,pathlib
p=pathlib.Path('retained');d=json.loads((p/'reimport.json').read_text())['modules']['qfd_dv_stream_controls'];src=json.loads(pathlib.Path('candidate/candidate.json').read_text())['modules']['qfd_dv_stream_controls']
def count(m):return dict(collections.Counter(c['type'] for c in m['cells'].values()))
expected=collections.Counter(count(src));expected.pop('$scopeinfo',None)
# write_verilog expresses enabled FFs as an exact feedback mux and plain FF.
for old,new in [('$_DFFE_PP_','$_DFF_P_'),('$_DFFE_PN0P_','$_DFF_PN0_')]:
 n=expected.pop(old,0);expected[new]+=n;expected['$_MUX_']+=n
assert count(d)==dict(expected),(count(d),dict(expected))
loads=collections.Counter()
for c in d['cells'].values():
 for pn,bs in c['connections'].items():
  if c['port_directions'][pn]=='input':loads.update(x for x in bs if isinstance(x,int))
clock=set(d['ports']['ck']['bits']);viol=[(x,n) for x,n in loads.items() if x not in clock and n>32];assert not viol,viol
p.joinpath('retention.json').write_text(json.dumps({'native_comb_master_census_preserved':True,'enabled_ff_exact_feedback_mux_expansion':2179,'cells':len(d['cells']),'max_nonclock_load':max(n for x,n in loads.items() if x not in clock),'retained_native_comb_cells':sum(not c['type'].startswith('$_') for c in d['cells'].values()),'generic_sequential_not_native':True,'qualified':False},indent=2)+'\n')
print(p.joinpath('retention.json').read_text())
PY
