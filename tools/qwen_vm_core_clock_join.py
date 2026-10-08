#!/usr/bin/env python3
"""Extract literal core clock/MEIF statements and join the real protected provider."""
import argparse,json,hashlib,subprocess
from pathlib import Path

def extract(s):
 clock=s[s.index('    wire me_wake ='):s.index('    wire [(G >> SMIN)-1:0] me_o_we;')]
 a=s.index('    reg me_gop, me_tk_d, me_rdy_q, me_idl_q;');b=s.index('    always @(posedge clk) if (me_go)',a);book=s[a:b]
 a=s.index('    wire me_ifhold =');b=s.index('    wire [NW-1:0] mqw_nout',a);status=s[a:b]
 a=s.index('    reg pr_kvok_q, pr_kvdv_q, pr_su_kv, pr_mmo_q;');b=s.index('    //: descriptor is announced',a);pin=s[a:b]
 fb=next(line for line in s.splitlines() if 'wire fb_me_go =' in line)
 go=next(line for line in s.splitlines() if 'assign me_go =' in line)
 header='module source_core_clock #(parameter VM_OWNED_LEASE=1,DEC_LA_PINREG=0)(input clk,rst_n_i,me_mem_ok,vm_me_lease,issue_intent,output vm_me_wanted,effective,engine_clk,pending,take,output[31:0]accepts);\nlocalparam ME_STALL=1,ME_IDLE_GATE=1,DEC_LA_MEIF=1,DEC_LA_ISSUE_FB=1;\nlocalparam S_RUN=2;wire[1:0]st=S_RUN,d_unit=1;wire nx_v=1;\nwire me_ready,me_idle,me_go,me_en,me_clk_en;wire[15:0]me_progress;\nwire me_ready_pin=1,me_idle_pin=0;wire[15:0]me_progress_pin=0;wire me_go_pin;\nwire kv_ok=1,kvd_v=0,su_go=0,su_idle=1;wire[1:0]dst=0;\nwire fb_run=issue_intent,fb_is_me=1,fb_cond_me=1,fb_kvg_me=1,fb_wg_me=1,issue=0;\n'
 text=header+pin+clock+fb+"\n"+go+"\n"+book+status+'\nassign effective=me_en;assign engine_clk=me_clk;assign pending=me_gop;assign take=me_tk_d;\nreg[31:0]accepted=0;assign accepts=accepted;\nalways @(posedge me_clk)if(!rst_n_i)accepted<=0;else if(me_go_pin)accepted<=accepted+1;\nendmodule\n'
 return text

def run(a):
 a.out.mkdir(parents=True,exist_ok=True);root=a.root
 core=root/'results/rtl/qwen_vm_core_clock_join_20261007/inputs/core.sv'
 bench=root/'rtl/test/qwen_vm_core_clock_join_20261007/tb_core_clock_join.sv'
 slice=a.out/'source_core_clock.sv';slice.write_text(extract(core.read_text()))
 bank=root/'rtl/hbm_accel/qwen/vm_direct_readback_20261007'
 files=[root/'rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv',root/'rtl/hdc/ot_hdc_cg.sv',root/'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']+[bank/n for n in ['ot_qwen_vm_bank4_direct_readback.sv','ot_qwen_checked_vm_bank_direct_readback.sv','ot_qwen_finite_vm_adapter_direct_readback.sv']]+[slice,bench]
 (a.out/'source_pins.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [core,*files]},indent=2)+'\n')
 result={}
 for name,pin,lease in [('pinreg0',0,1),('pinreg1',1,1),('lease_disabled',0,0)]:
  sim=a.out/(name+'_sim');p=subprocess.run(['iverilog','-g2012','-s','tb_core_clock_join',f'-Ptb_core_clock_join.PINREG={pin}',f'-Ptb_core_clock_join.LEASE={lease}','-o',str(sim),*[str(p) for p in files]],capture_output=True,text=True);(a.out/(name+'_compile.log')).write_text(p.stdout+p.stderr);assert p.returncode==0
  p=subprocess.run(['vvp',str(sim)],capture_output=True,text=True);(a.out/(name+'.log')).write_text(p.stdout+p.stderr)
  ok=p.returncode==0 and 'PASS captured_intent1 supply_hold_and_PINREG_contract' in p.stdout if lease else p.returncode!=0 and 'UNPAID_SOURCE_ME_CLOCK' in p.stdout
  assert ok,(name,p.returncode,p.stdout);result[name]={'exit_code':p.returncode,'expected_outcome':True}
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);run(p.parse_args())
