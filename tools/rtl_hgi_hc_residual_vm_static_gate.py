#!/usr/bin/env python3
import subprocess,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    run=ROOT/'run_hc_vm_residual';run.mkdir(exist_ok=True)
    files=['rtl/test/tb_hgi_hc_residual_vm_static.sv','rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_residual_vm_static.sv',
        'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv','rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv',
        'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
    receipt={'scope':'actual4SID32VMbanks96SRAM12taps→HCresidualproducer; not full arithmetic or physical/nativechip qualification',
        'source_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},'positions':8,'K':20480,'sectors':20480,'waves':640,'request_to_response_output_edges':18,'response_consumer_capture':19,'first_wave_emission':22,'wave_interval':4}
    for mutant in (0,1):
        with (run/f'm{mutant}.build.log').open('w') as log:
            subprocess.run(['iverilog','-g2012','-s','tb_hgi_hc_residual_vm_static',f'-Ptb_hgi_hc_residual_vm_static.MUT={mutant}',
                '-o',str(run/f'm{mutant}.vvp'),*[str(ROOT/f) for f in files]],stdout=log,stderr=subprocess.STDOUT,check=True)
        with (run/f'm{mutant}.log').open('w') as log:p=subprocess.run(['vvp',str(run/f'm{mutant}.vvp')],stdout=log,stderr=subprocess.STDOUT)
        out=(run/f'm{mutant}.log').read_text();print(mutant,p.returncode,out[-1200:],flush=True)
        receipt[f'm{mutant}']={'exit_code':p.returncode,'log_sha256':hashlib.sha256(out.encode()).hexdigest()}
        (run/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
        if mutant==0 and p.returncode:raise SystemExit('positive failed')
        if mutant==1 and not p.returncode:raise SystemExit('mutant escaped')
if __name__=='__main__':main()
