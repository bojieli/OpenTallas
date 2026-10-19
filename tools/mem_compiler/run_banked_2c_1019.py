#!/usr/bin/env python3
"""Fleet-only native bank functional qualification, including negative controls."""
from pathlib import Path
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parents[2]
out = ROOT/'results/arch/sram_pin_access_1019/functional'
out.mkdir(parents=True, exist_ok=True)
v = os.environ.get('VERILATOR', str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
version = subprocess.check_output([v, '--version'], text=True).strip()
assert '5.050' in version, version
src = [ROOT/'rtl/test/sram_pin_access_1019/banked_2c.sv',
       ROOT/'rtl/test/sram_pin_access_1019/tb.sv']
src += [ROOT/f'physical/asap7_memory_macros_v2/ot_sram_1r1w2c_{d}x64_m1/ot_sram_1r1w2c_{d}x64_m1.v' for d in (32,128,256)]
rec = {'verilator': version, 'cases': [], 'verdict': 'INCOMPLETE',
       'scope': 'functional native bank contracts; no physical escape qualification'}
for words,bits,mut in [(8,285,0),(16,546,0),(32,546,0),(128,256,0),(256,512,0),
                       (32,546,1),(32,546,2)]:
    tag = f'w{words}_b{bits}_m{mut}'
    obj=out/tag
    cmd=[v,'--binary','--timing','-Wno-fatal','--top-module','tb','-j','4',
         f'-GWORDS={words}',f'-GBITS={bits}',f'-GMUT={mut}','--Mdir',str(obj)]+list(map(str,src))
    with (out/f'{tag}_build.log').open('w') as f:
        subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
    cp=subprocess.run([str(obj/'Vtb')],capture_output=True,text=True)
    log=cp.stdout+cp.stderr
    (out/f'{tag}.log').write_text(log)
    ok=(cp.returncode==0 and 'BANKED_2C_PASS' in log) if mut==0 else (cp.returncode!=0 and 'BANK_MISMATCH' in log)
    rec['cases'].append({'words':words,'bits':bits,'mutant':mut,'exit':cp.returncode,'pass':ok,'log':f'{tag}.log'})
    (out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(tag, 'PASS' if ok else 'FAIL',flush=True)
    if not ok: raise SystemExit(1)
rec['verdict']='PASS'
(out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n')
print('BANKED_2C_MATRIX PASS five production shapes two mutants')
