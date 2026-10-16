#!/usr/bin/env python3
"""Smallest actual protected bank + six negative controls; never rewrites pinned evidence."""
from pathlib import Path
import subprocess,tempfile,json,hashlib
root=Path(__file__).resolve().parents[3]
sources=['rtl/hbm_accel/generic/vm/ot_hgi_vm_wide_bank.sv','rtl/hbm_accel/generic/vm/tb_hgi_vm_wide_bank.sv','physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v']
output=Path(tempfile.mkdtemp(prefix='hgi-vm-bank-gate-'))
expected={0:'BANK_PASS',1:'READ_EXACT',2:'READ_EXACT',3:'WRITE_ACK_TIME_OR_ID',4:'READ_EXACT',5:'WRITE_ACK_TIME_OR_ID',6:'WRITE_II'}
records=[]
for mutant in range(7):
    exe=output/f'bank_m{mutant}.vvp'
    compilecmd=['iverilog','-g2012','-s','tb_hgi_vm_wide_bank','-P',f'tb_hgi_vm_wide_bank.TEST_MUT={mutant}','-o',str(exe),*sources]
    build=subprocess.run(compilecmd,cwd=root,capture_output=True,text=True)
    (output/f'build_m{mutant}.log').write_text(build.stdout+build.stderr)
    assert build.returncode==0,build.stderr
    run=subprocess.run(['vvp',str(exe)],cwd=root,capture_output=True,text=True)
    (output/f'run_m{mutant}.log').write_text(run.stdout+run.stderr)
    passed=(run.returncode==0 if mutant==0 else run.returncode!=0) and expected[mutant] in run.stdout
    records.append(dict(mutant=mutant,returncode=run.returncode,gate_pass=passed,expected=expected[mutant]))
    print(json.dumps(records[-1]),flush=True)
record=dict(records=records,source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest()for p in sources})
(output/'run_record.json').write_text(json.dumps(record,indent=2)+'\n')
print('ARTIFACT_DIR='+str(output),flush=True)
assert all(r['gate_pass']for r in records)
