#!/usr/bin/env python3
"""Fleet-only generic bit-cell fanout census; a fail prevents a gate; PASS is not mapped qualification."""
import collections,hashlib,json,subprocess,sys
from pathlib import Path
r=Path(sys.argv[1]).resolve();o=Path(sys.argv[2]).resolve();o.mkdir(parents=True,exist_ok=True)
fs=['physical/common_flow/ot_keep_regs.tcl','rtl/hdc/nearhbm/ot_qwen_tp8_pv_join_cold_t.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_prefix.sv','rtl/hdc/ot_hdc_delay.sv','physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv']
ys='read_verilog -sv -DSYNTHESIS '+' '.join(str(r/f)for f in fs if f.endswith('.sv'))+'\nhierarchy -check -top ot_qwen_tp8_pv_join_cold_t -chparam COLD_INIT 1 -chparam RESET_PIN 1\ntcl '+str(r/'physical/common_flow/ot_keep_regs.tcl')+'\nsynth -top ot_qwen_tp8_pv_join_cold_t -flatten -noabc\nwrite_json synth.json\n'
(o/'census.ys').write_text(ys)
with(o/'synth.log').open('w')as f:p=subprocess.run(['yosys','-s','census.ys'],cwd=o,stdout=f,stderr=subprocess.STDOUT)
if p.returncode:raise SystemExit(p.returncode)
d=json.loads((o/'synth.json').read_text())['modules']['ot_qwen_tp8_pv_join_cold_t'];names={};drivers={};loads=collections.Counter()
for n,v in d['netnames'].items():
 for i,b in enumerate(v['bits']):
  if isinstance(b,int):names.setdefault(b,f'{n}[{i}]')
for n,c in d['cells'].items():
 for pn,bs in c['connections'].items():
  for b in bs:
   if isinstance(b,int):
    if c['port_directions'][pn]=='input' and pn not in ['C','CLK']:loads[b]+=1
    elif c['port_directions'][pn]=='output':drivers[b]=n
bad=[{'net':names.get(b,str(b)),'loads':n,'driver':drivers.get(b,'PORT')}for b,n in loads.most_common()if n>32]
x={'parameters':{'COLD_INIT':1,'RESET_PIN':1,'J_LAT':7,'MUT':0},'source_sha256':{f:hashlib.sha256((r/f).read_bytes()).hexdigest()for f in fs},'bit_cells':len(d['cells']),'max_nonclock_loads':max(loads.values()),'over32':bad,'gate_permitted':False,'qualification':'generic synth bit-cell lower-level census only; mapped native/reset reach/clock/pins still required'}
(o/'result.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'max_nonclock_loads':x['max_nonclock_loads'],'over32':len(bad),'worst':bad[:8]}))
