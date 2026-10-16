#!/usr/bin/env python3
"""Source-exact CP component gate; launch under ot-run on a compute host.

Actual RTL arithmetic and SRAM history; VM returns are declared boundary inputs.
This verifies the component and its fixed calendar, not native full-die memory.
"""
from pathlib import Path
import argparse, sys, subprocess, json, hashlib, time
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/s81_suhc'))
import su_gate as G
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--work',required=True,type=Path)
ap.add_argument('--fixtures',type=Path,default=root/'results/rtl/s81_cp_1014/fixtures')
ap.add_argument('--mutant',action='store_true')
ap.add_argument('--core',action='store_true')
ap.add_argument('--jobs',type=int,default=8)
a=ap.parse_args()
base=a.fixtures.resolve(); mode=int(a.mutant); variant='core' if a.core else 'vm'
top='tb_s81_su_cp_vm' if variant=='vm' else 'tb_s81_su_cp'
out=a.work.resolve()/f'build_{variant}_m{mode}';out.mkdir(parents=True,exist_ok=True)
(out/'receipt.json').unlink(missing_ok=True)
files=[root/p for p in dict.fromkeys(G.RTL+G.H.FP['rtl']+['rtl/dsrom_sys/s81_suhc/ot_s81_su_cp.sv','rtl/dsrom_sys/s81_suhc/ot_s81_su_cp_vm.sv',f'rtl/dsrom_sys/s81_suhc/test/{top}.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v'])]
vl=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
cmd=[str(vl),'--binary','--timing','-j',str(a.jobs),'-Wno-fatal','-Wno-lint','-Wno-style','-Wno-WIDTH','--top-module',top,f'-GMUT={mode}','--Mdir',str(out/'obj'),'-o','sim',*map(str,files)]
def pin(paths):
 return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

# Bind the inputs before compilation. Hashing only after simulation could
# attribute an old binary's numerical verdict to newly edited RTL or fixtures.
fixture_files=sorted(p for p in base.glob('L*/*') if p.is_file())
if not fixture_files:
 raise RuntimeError('no CP fixtures found: '+str(base))
source_pins=pin(files)
fixture_pins={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture_files}
t=time.time()
with (out/'build.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
if r.returncode:print('BUILD FAIL',r.returncode,flush=True);sys.exit(r.returncode)
checks=[]
for L in (2,8,14):
 p=subprocess.run([str(out/'obj/sim'),f'+DIR={base}/L{L:02d}'],capture_output=True,text=True);(out/f'run_L{L:02d}.log').write_text(p.stdout+p.stderr)
 ok=(('CP_VM PASS' if variant=='vm' else 'CP PASS') in p.stdout and p.returncode==0) if mode==0 else (('CP_VM FAIL' if variant=='vm' else 'CP FAIL') in p.stdout and p.returncode!=0 and ('BAD beat' in p.stdout or 'BAD row' in p.stdout))
 checks.append(dict(layer=L,expected='PASS' if mode==0 else 'FAIL',satisfied=ok,rc=p.returncode,summary=[l for l in p.stdout.splitlines() if l.startswith(('CP_DONE','CP_RESULT','CP_VM_DONE','CP_VM_RESULT','BAD beat','BAD row'))]))
 print(L,ok,p.stdout[-500:],flush=True)
protocol_mutant=None
if variant=='vm' and mode==0:
 p=subprocess.run([str(out/'obj/sim'),f'+DIR={base}/L02','+LATE=1'],capture_output=True,text=True)
 (out/'run_late_L02.log').write_text(p.stdout+p.stderr)
 ok=p.returncode!=0 and 'CP_VM FAIL' in p.stdout and 'cycles139 scheduled139 fault1' in p.stdout and 'cycles272 scheduled272 fault1' in p.stdout
 protocol_mutant=dict(satisfied=ok,rc=p.returncode,summary=[l for l in p.stdout.splitlines() if l.startswith(('CP_VM_DONE','CP_VM_RESULT'))])
 checks.append(dict(layer=2,expected='late VM response FAIL on unchanged schedule',satisfied=ok))
 print('PROTOCOL_MUTANT',ok,p.stdout[-500:],flush=True)
if source_pins!=pin(files):
 raise RuntimeError('CP sources changed during build/run; no receipt issued')
if fixture_pins!={str(p.relative_to(base)):hashlib.sha256(p.read_bytes()).hexdigest() for p in base.glob('L*/*') if p.is_file()}:
 raise RuntimeError('CP fixtures changed during build/run; no receipt issued')
record=dict(qualification='CP component with actual arithmetic and SRAM; declared VM interface fixtures; not a native full token',fixture_sha256=fixture_pins,protocol_mutant=protocol_mutant,mode=mode,seconds=time.time()-t,checks=checks,source_sha256=source_pins,verdict='PASS' if all(x['satisfied'] for x in checks) else 'FAIL')
(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n');sys.exit(0 if record['verdict']=='PASS' else 1)
