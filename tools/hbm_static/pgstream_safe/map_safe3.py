#!/usr/bin/env python3
"""Fleet TT native-cell source mapping only; no placement/CTS claim."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
spec=json.loads(Path('physical/ref_tile/hbm_su_pg_stream_b_1019/spec.json').read_text())
sources=spec['sources']+[
 'rtl/hbm_accel/generic/adapters/static_su/programme/multirate_bridge_regional.sv',
 'rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pg_stream_safe3.sv']
top='ot_hbm_su_static_pg_stream_split_safe3'
libs=sorted((Path.home()/'.local/opentallas-pdk-asap7/lib/NLDM').glob('*.lib'))
assert len(libs)==5
seq=[p for p in libs if '_SEQ_' in p.name];assert len(seq)==1
args=' '.join('-liberty '+str(p) for p in libs)
ys='read_verilog -sv -defer -D SYNTHESIS '+' '.join(sources)+'\n'
ys+='hierarchy -check -top '+top+' '+' '.join('-chparam '+str(k)+' '+str(v) for k,v in dict(spec['params']).items())+'\n'
ys+='synth -top '+top+' -flatten\n'
# synth -flatten honors keep_hierarchy on actual stateful regional modules.
ys+=''.join('read_liberty -lib -ignore_miss_func '+str(p)+'\n' for p in libs)
ys+='dfflibmap -liberty '+str(seq[0])+'\nabc '+args+' -D 833\nclean\n'
ys+='write_json '+str(out/'hier_mapped.json')+'\n'
ys+='setattr -mod -unset keep_hierarchy\nflatten\ncheck -assert\nstat '+args+'\n'
ys+='write_json '+str(out/'mapped.json')+'\nwrite_verilog -noattr -noexpr '+str(out/'mapped.v')+'\n'
(out/'map.ys').write_text(ys)
binding=dict(top=top,source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
             libraries_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in libs},
             params=dict(spec['params']),native_timing_qualified=False,physical_qualified=False)
(out/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
with (out/'yosys.log').open('w') as log:
 r=subprocess.run([str(Path.home()/'.local/opentallas-tools/yosys-0.68/bin/yosys'),'-s',str(out/'map.ys')],stdout=log,stderr=subprocess.STDOUT)
if r.returncode:sys.exit(r.returncode)
rc=subprocess.call([sys.executable,'tools/hbm_static/pgstream_safe/census.py',str(out/'mapped.v'),str(out/'census.json'),'--top',top])
rb=subprocess.call([sys.executable,'tools/hbm_static/pgstream_safe/boundary.py',str(out/'mapped.json'),str(out/'boundary.json'),top])
sys.exit(rc or rb)
