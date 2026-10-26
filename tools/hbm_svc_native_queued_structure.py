#!/usr/bin/env python3
"""Count actual native controller FF sinks from the flattened Yosys JSON.

Run the committed structure.ys from the source root first. This counts register
bits after mapping real owner memories; it does not establish timing or CTS.
"""
import argparse
import hashlib
import json
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('netlist',type=Path)
p.add_argument('--log',type=Path)
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
raw=a.netlist.read_bytes()
m=json.loads(raw)['modules']['ot_hbm_svc_native_sector_queued_stack']
names={m['ports']['clk']['bits'][0]:'clk'}
names.update({b:f'pc_clk[{i}]' for i,b in enumerate(m['ports']['pc_clk']['bits'])})
roots={};types={}
for c in m['cells'].values():
    if 'ff' in c['type'].lower() and 'CLK' in c['connections']:
        clock=c['connections']['CLK']
        if len(clock)!=1 or clock[0] not in names:
            raise ValueError('Unrecognized actual register clock')
        name=names[clock[0]];bits=len(c['connections']['Q'])
        roots[name]=roots.get(name,0)+bits
        types[c['type']]=types.get(c['type'],0)+bits
if set(roots)!={'clk'}|{f'pc_clk[{i}]' for i in range(32)}:
    raise ValueError('Missing actual default32PC clock coverage')
base=Path(__file__).resolve().parents[1]
sources=['rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv','rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_queued_stack.sv']
r=dict(scope='Actual default32PC proc/flatten/opt/memory_map FF sinks; not CTS or physical qualification',
    structure_json_sha256=hashlib.sha256(raw).hexdigest(),
    root_FF_bits=dict(sorted(roots.items())),FF_types=types,
    max_root_FF=max(roots.values()),all_roots_le_15000=all(v<=15000 for v in roots.values()),
    total_FF=sum(roots.values()),source_sha256={s:hashlib.sha256((base/s).read_bytes()).hexdigest() for s in sources},
    protected_state_admitted=False,physical_qualified=False)
if a.log:r['raw_Yosys_log_sha256']=hashlib.sha256(a.log.read_bytes()).hexdigest()
a.out.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
if not r['all_roots_le_15000']:raise SystemExit(2)
