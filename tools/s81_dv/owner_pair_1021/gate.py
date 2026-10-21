#!/usr/bin/env python3
"""Required odd-overlap RD + canonical RB composition, fleet only; no layer claim."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import numpy as np

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(root/'tools/s81_dv'))
from layer_prog.owner_fold import pair_vehicle
from layer_prog.lower_vpx import _payload
a.out.mkdir(parents=True, exist_ok=False)
vehicle = pair_vehicle(4)
# Real component boundary inputs, not a checkpoint producer or intermediate sums.
rank = np.array([[1e20, 1, -3, 1.0000001, 4, -1e20, 7, 1e-6],
                 [-1e20, 2, 1e-10, -1, 2, 1e20, -2, 4],
                 [3, 1e20, 4, 2, -8, 3, 1e20, -4],
                 [1e-10, -1e20, -2, 1e-7, 1, 1e-10, -1e20, 2]], dtype=np.float32)
expected = np.add(np.add(rank[0],rank[1],dtype=np.float32),
                  np.add(rank[2],rank[3],dtype=np.float32),dtype=np.float32)
def pack(words): return sum(int(x) << (32*i) for i,x in enumerate(words))
def line(payload): return 1 | (1 << 4) | (payload << 21)
stim = []
for r, pair in enumerate(vehicle['staged_pairs']):
    for half, row in enumerate(pair['rows']):
        body = row | (15 << 10) | (pack(rank[r].view(np.uint32)[half*4:half*4+4]) << 14)
        stim.append((80 + len(stim)*8, line(_payload(16,5,1,body))))
for k, step in enumerate(vehicle['commands']):
    for j, template in enumerate(step['templates']):
        stim.append((200 + k*80 + j*9, line(int(template['word'],16))))
assert len(stim) <= 64 and max(t for t,_ in stim) < 1900
(a.out/'stim.mem').write_text(''.join(f'{x:0276x}\n' for _,x in stim)+ '0\n'*(64-len(stim)))
(a.out/'dates.mem').write_text(''.join(f'{t:08x}\n' for t,_ in stim)+ 'ffffffff\n'*(64-len(stim)))
(a.out/'expected.mem').write_text(f'{pack(expected.view(np.uint32)):064x}\n')
text = (root/'tools/s81_slice/vs_bench.sh').read_text()
src = re.search(r'srcs="(.*?)"\n',text,re.S).group(1).split()
src = [s for s in src if not s.endswith('/tb_s81sl_vs.sv')]
src += ['rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv',
        'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstopt.sv',
        'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv',
        'tools/s81_dv/owner_pair_1021/tb_owner_pair.sv']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
pins = {s:sha(root/s) for s in src}
v = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd = [str(v),'--binary','--timing','-O1','-fno-dfg','--unroll-count','4',
       '-Wno-fatal','-Wno-WIDTH','--top-module','tb_owner_pair','-Mdir',str(a.out/'obj'),
       '-j','2',*[str(root/s) for s in src],'-CFLAGS','-O1']
record = dict(status='RUNNING', full_layer=False, full_token=False, admitted=False,
              scope='Synthetic eight-element rank partials -> real native target5 staging -> XRT local RD/DL4/VP SRAM -> canonical VS11',
              source_sha256=pins, compiler_sha256={n:sha(root/n) for n in
                  ['tools/s81_dv/layer_prog/owner_fold.py','tools/s81_dv/layer_prog/lower_vpx.py']},
              argv=cmd, vehicle=vehicle, fixed_stimulus_dates=[t for t,_ in stim],
              inputs_bits=rank.view(np.uint32).tolist(), expected_bits=expected.view(np.uint32).tolist(),
              open=['actual wo_b producer/capture','four-rank ingress','selected die row leases/routes','full tile/result calendar'])
def save(): (a.out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
save()
with (a.out/'build.log').open('w') as log:
    b = subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
if b.returncode:
    record.update(status='FAIL',reason='build',exit_code=b.returncode);save();sys.exit(1)
guard_dir = Path.home()/'.local/opentallas-tools/verilator-5.050/share/ot_nba_guard'
sys.path.insert(0,str(guard_dir)); import verilator_nba_guard as G
guard = G.scan(str(a.out/'obj')); (a.out/'nba_guard.json').write_text(json.dumps(guard,indent=2)+'\n')
if guard['findings']:
    record.update(status='FAIL',reason='NBA guard');save();sys.exit(86)
checks={}
for name,mut in [('positive',0),('negative_odd_destination',1)]:
    r = subprocess.run([str(a.out/'obj/Vtb_owner_pair'),f'+MUT={mut}',f'+COUNT={len(stim)}'],
                       cwd=a.out,capture_output=True,text=True)
    log = r.stdout+r.stderr; (a.out/(name+'.log')).write_text(log)
    checks[name] = dict(exit_code=r.returncode, passed=(r.returncode==0 and 'OWNER_PAIR PASS' in log)
                       if not mut else (r.returncode!=0 and 'OWNER_PAIR FAIL' in log and 'BAD got=' in log))
assert pins == {s:sha(root/s) for s in src}, 'source changed during proof'
record.update(status='PASS_SOURCE_COMPONENT' if all(c['passed'] for c in checks.values()) else 'FAIL',checks=checks)
save(); print(json.dumps(dict(status=record['status'],checks=checks)),flush=True)
sys.exit(int(record['status']=='FAIL'))
