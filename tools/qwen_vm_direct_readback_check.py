#!/usr/bin/env python3
"""Reproduce four-state actual-provider gate and binary readback-cone equivalence."""
import argparse, hashlib, json, subprocess
from pathlib import Path
from qwen_vm_direct_readback import generate

def main(a):
    out=a.out;out.mkdir(parents=True,exist_ok=True);generated=out/'generated';generate(a.root,generated)
    bench=a.bench.read_text().replace('ot_qwen_finite_vm_adapter #(', 'ot_qwen_finite_vm_adapter_direct_readback #(.DIRECT_READBACK(DIRECT_MODE),')
    bench=bench.replace('module tb_qwen_su_service_gate;', 'module tb_qwen_su_service_gate;\nparameter DIRECT_MODE=1;')
    assert 'DIRECT_READBACK(DIRECT_MODE)' in bench
    (out/'bench.sv').write_text(bench)
    common=[a.root/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',a.root/'rtl/hdc/ot_hdc_cg.sv',a.root/'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
    files=common+[generated/n for n in ['ot_qwen_vm_bank4_direct_readback.sv','ot_qwen_checked_vm_bank_direct_readback.sv','ot_qwen_finite_vm_adapter_direct_readback.sv']]+[a.progress,out/'bench.sv']
    fixture=a.root/'results/rtl/qwen_hbm_activation_vm_realization_20261005/minimum_adapter_case/initial_x4096.u32.hex'
    results=[]
    for enabled in (0,1):
        sim=out/f'sim{enabled}';q=subprocess.run(['iverilog','-g2012','-s','tb_qwen_su_service_gate',f'-Ptb_qwen_su_service_gate.DIRECT_MODE={enabled}','-o',str(sim),*[str(p) for p in files]],capture_output=True,text=True);(out/f'compile{enabled}.log').write_text(q.stdout+q.stderr);assert q.returncode==0
        for case in ((0,) if not enabled else (0,1,2,3)):
            p=subprocess.run(['vvp',str(sim),'+FIXTURE='+str(fixture),f'+NEGATIVE={case}'],capture_output=True,text=True);(out/f'd{enabled}_c{case}.log').write_text(p.stdout+p.stderr)
            if not enabled: ok=p.returncode!=0 and 'captured SU conflict address returns mismatch' in p.stdout
            elif case==0:ok=p.returncode==0 and 'PASS captured_SU_conflict' in p.stdout
            else:ok=p.returncode!=0 and any(x in p.stdout for x in ['FOREIGN_ACK_REJECTED','UNPAID_NATIVE_ADVANCE','PREMATURE_CHASE_WITH_UNPAID_FRAME'])
            assert ok,(enabled,case,p.returncode,p.stdout[-1000:]);results.append(dict(enabled=enabled,case=case,expected_outcome=True,exit_code=p.returncode))
    cone='''module readback_cone(input clk,input [8191:0]partial,output equal);
wire [511:0] bank_word[0:3];reg[2047:0]old_q,new_q;
genvar b;generate for(b=0;b<4;b=b+1)begin:g_bank
wire[511:0]partial_q[0:3];genvar p;for(p=0;p<4;p=p+1)assign partial_q[p]=partial[b*2048+p*512+:512];
assign bank_word[b]=partial_q[0]|partial_q[1]|partial_q[2]|partial_q[3];end endgenerate
always @(posedge clk)begin
for(integer i=0;i<4;i=i+1)old_q[i*512+:512]<=bank_word[i];
'''+ '\n'.join(f'new_q[{i}*512+:512]<=g_bank[{i}].partial_q[0]|g_bank[{i}].partial_q[1]|g_bank[{i}].partial_q[2]|g_bank[{i}].partial_q[3];' for i in range(4))+ '\nend\nassign equal=old_q==new_q;endmodule\n'
    (out/'cone.sv').write_text(cone)
    q=subprocess.run([str(a.yosys),'-Q','-T','-p',f'read_verilog -sv {out}/cone.sv; prep -top readback_cone; flatten; opt; sat -seq 2 -set-init-zero -prove equal 1 -verify'],capture_output=True,text=True);(out/'cone_equivalence.log').write_text(q.stdout+q.stderr);assert q.returncode==0 and 'SUCCESS!' in q.stdout
    record=dict(scope='Actual full16 provider/NR5 NW16 SU mechanism plus source-expression binary cone proof; not fullROM or hardware protection qualification',cases=results,binary_readback_cone_equivalent=True,added_cycles=0,added_register_bits=0,source_pin={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [a.bench,a.progress,*common]},known_failure_preserved='DIRECT_MODE0 fails actual initialized data readback in Icarus11; DIRECT_MODE1 passes same fixture',physical_admission=False,adopted=False)
    (out/'result.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record['cases']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--bench',type=Path,required=True);p.add_argument('--progress',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--yosys',type=Path,default=Path('/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys'));main(p.parse_args())
