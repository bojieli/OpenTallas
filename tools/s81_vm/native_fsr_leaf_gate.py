#!/usr/bin/env python3
"""Source-exact bank8 hard wrapper versus actual original32-bank FSR oracle."""
import pathlib,sys,subprocess
G=int(sys.argv[1]);mode=sys.argv[2];out=pathlib.Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
if G!=0:raise SystemExit('b0 representative currently implemented; other bank groups need directed bank-local fault oracle')
root=pathlib.Path(__file__).resolve().parents[2];r=root/'rtl/dsrom_sys/s81_ph/vm'
s=(root/'rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_static_fsr_split.sv').read_text()
s=s.replace('wire[31:0]ov,rv','wire[7:0]ov;wire[31:0]rv').replace('wire[287:0]oa,ra','wire[71:0]oa;wire[287:0]ra').replace('wire[255:0]ot,rt','wire[63:0]ot;wire[255:0]rt').replace('wire[3:0]f','wire f')
s=s.replace('dsfd_vm_static_suhc_fsr_split dut','dsfd_vm_static_fsr_b0 dut').replace('.ck({4{ck}})', '.ck(ck)').replace('.rst_n({4{rst}})', '.rst_n(rst)')
s=s.replace('ov!==rv||','ov!==rv[7:0]||').replace('q<32;q=q+1','q<8;q=q+1').replace('checks>10000','checks>1000').replace('FSR_SPLIT','NATIVE_FSR')
bench=out/'tb.sv';bench.write_text(s)
files=[r/'dsfd_vm_static_fsr_bank8.sv',r/'dsfd_vm_static_fsr_quartets.sv',r/'dsfd_vm_static_suhc_fsr.sv',bench]
subprocess.run(['iverilog','-g2012',*(['-DOT_VM_FSR8_MUT_TAG']if mode=='mutant'else[]),'-s','tb_dsfd_vm_static_fsr_split','-o',str(out/'sim'),*map(str,files)],check=True)
res=subprocess.run(['vvp',str(out/'sim'),'+mode=0','+seed=1'],text=True,capture_output=True,check=True);print(res.stdout,end='');(out/'run.log').write_text(res.stdout)
if mode=='mutant':
 if 'NATIVE_FSR FAIL mode0 'not in res.stdout:raise SystemExit('MUTANT NOT KILLED')
 raise SystemExit(1)
if 'NATIVE_FSR PASS mode0 'not in res.stdout:raise SystemExit(2)
