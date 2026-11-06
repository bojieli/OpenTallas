#!/usr/bin/env python3
"""Smallest native full-shape cache proof, exact macro contract, three negative controls."""
import argparse,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--rw-sram',type=int,choices=[0,1],default=1);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
r=Path(__file__).resolve().parents[2];native=r/'rtl/hbm_accel/cores_split/reform_1106_svgr_top/ot_svgr_cache136_native.sv';base=r/'rtl/hbm_accel/loader/service_native';profile=json.loads((r/'physical/die_plan/hbm/over_cap_split/reform_1106/svgr_top_cache/profile.json').read_text())
tb=(base/'tb_hbm_svc_static_sm_packed136.sv').read_text().replace('ot_hbm_svc_static_sm_packed136 #(.PACKED136(1)) dut(.*);','ot_svgr_cache136_native #(.PACKED136(1),.RW_SRAM(1)) dut(.*);')
outs=[x for x in profile['port_inventory'] if x['direction']=='output'];decl='\n'.join('wire '+('['+str(x['width']-1)+':0] ' if x['width']>1 else '')+'lock_'+x['name']+';' for x in outs)
conns=','.join('.'+x['name']+'('+('lock_' if x['direction']=='output' else '')+x['name']+')' for x in profile['port_inventory'])
shadow=decl+'\not_hbm_svc_static_sm_packed136 #(.PACKED136(1)) baseline('+conns+');\ninteger lockstep_checks=0; always @(negedge clk) if(rst_n) begin\nif ({block_ready,bank_owned,busy,fault,out_packet[1098]} !== {lock_block_ready,lock_bank_owned,lock_busy,lock_fault,lock_out_packet[1098]}) $fatal(1,"native lockstep status/valid mismatch");\nif(out_packet[1098] && out_packet !== lock_out_packet) $fatal(1,"native lockstep packet mismatch");\nlockstep_checks=lockstep_checks+1; end\n'
tb=tb.replace(' wire [1098:0] off_packet;',shadow+' wire [1098:0] off_packet;').replace('STATIC_SM_PACKED136 PASS','STATIC_SM_PACKED136 PASS lockstep included')
tb=tb.replace('.RW_SRAM(1)', '.RW_SRAM('+str(a.rw_sram)+')');(a.out/'tb.sv').write_text(tb)
mems=[r/'physical/asap7_memory_macros_v2'/m/(m+'.v') for m in ['ot_sram_1r1w_128x256_m1_r2c2','ot_sram_1r1w_128x256_m1_r0c0_g256']]
source=native.read_text();mutants={'positive':source,'payload_flip':source.replace('.wd_in(write_data),.w_mask_in(1',".wd_in(write_data ^ 256'd1),.w_mask_in(1"),'read_address':source.replace('.r_addr_in(read_addr),.rd_out(cache_data[p]),',".r_addr_in(read_addr ^ 7'd1),.rd_out(cache_data[p]),",1),'read_edge_removed':source.replace('.r_ce_in(read_ok),.r_addr_in(read_addr)',".r_ce_in(1'b0),.r_addr_in(read_addr)",1)}
if a.rw_sram==0:mutants={'positive':source}
results={}
for name,text in mutants.items():
 if name!='positive' and text==source:raise RuntimeError('mutant not applied: '+name)
 sv=a.out/(name+'.sv');sv.write_text(text);binary=a.out/(name+'.vvp');log=a.out/(name+'.log')
 subprocess.run(['iverilog','-g2012','-s','tb_hbm_svc_static_sm_packed136','-o',str(binary),*map(str,mems),str(r/'rtl/gpu/ot_gpu_payload_assemble.sv'),str(base/'ot_hbm_svc_static_sm_packed136.sv'),str(sv),str(a.out/'tb.sv')],check=True)
 with log.open('w') as f:run=subprocess.run(['vvp',str(binary)],stdout=f,stderr=subprocess.STDOUT)
 data=log.read_text();passed=run.returncode==0 and 'STATIC_SM_PACKED136 PASS' in data
 if name=='positive' and not passed:raise RuntimeError(data)
 if name!='positive' and (run.returncode==0 or not any(s in data for s in ['native lockstep','packed136 cache payload/tag mismatch'])):raise RuntimeError('mutant not caught: '+name+' '+data)
 results[name]=dict(verdict='PASS' if passed else 'CAUGHT',returncode=run.returncode,log=log.name)
(a.out/'summary.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results,indent=2))
