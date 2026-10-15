#!/usr/bin/env python3
"""Compare the extracted real A gateway against its frozen inline RTL body."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
CORE='rtl/qwen_sys/static_schedule_20261014/ot_qwen_rom_core_ctrl_su_static.sv'
SRC='rtl/qwen_sys/static_schedule_20261014/ot_qwen_a_operand_gateway_v1.sv'
TB='rtl/test/qwen_split/tb_qwen_a_gateway_equivalence.sv'
DEC='rtl/hdc/ot_hdc_qwen_int8_embed_decode.sv'
FROZEN='02bbde74ca864c57e283fac6f02c8ce33769a2e9'
OUT=ROOT/'results/rtl/qwen_a_operand_gateway_1015'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 old=subprocess.check_output(['git','show',FROZEN+':'+CORE],cwd=ROOT,text=True)
 raw=old[old.index('    reg embed_active, embed_scale_pending;'):old.index('    // -- engine clock enable')]
 original=(ROOT/SRC).read_text()
 # Only rename module-boundary identifiers; retain original procedural body.
 refbody=raw.replace('    wire [SW-1:0] embed_faults;\n','').replace('start && st == S_IDLE','start_idle')
 for before,after in [('su_va_re','a_re'),('su_va_addr','a_addr'),('su_va_q','a_q'),('va_re','vm_re'),('va_addr','vm_addr'),('va_q','vm_q')]:refbody=refbody.replace(before,after)
 header=original[:original.index('    reg embed_active, embed_scale_pending;')].replace('ot_qwen_a_operand_gateway_v1','qwen_a_gateway_frozen_inline')
 reference=header+refbody+'endmodule\n'
 tests=[]
 variants=[('fullshape',original,1,1,True),('legacy_address',original,1,0,True),('plain_vm',original,0,1,True),
 ('token_truncation_mutant',original.replace('tok_r * (HID / EMB_CODE_LANES)','tok_r[15:0] * (HID / EMB_CODE_LANES)'),1,1,False),
 ('vm_gate_mutant',original.replace('assign vm_re = a_re & ~({SW{(INT8_EMBED != 0) && embed_active}});','assign vm_re = a_re;'),1,1,False),
 ('lane_capture_bypass_mutant',original.replace('embed_code_q[8*embed_lanes[el*ELI +: ELI] +: 8]','embed_code_q[8*a_addr[el*AW +: ELI] +: 8]'),1,1,False),
 ('scale_capture_bypass_mutant',original.replace('.scale(embed_scale_hold)','.scale(embed_scale_q)'),1,1,False),
 ('fault_drop_mutant',original.replace('embed_sel[el] && bad','1\'b0'),1,1,False)]
 with tempfile.TemporaryDirectory(prefix='q-a-gateway-') as td:
  td=Path(td);ref=td/'frozen.sv';ref.write_text(reference)
  for name,source,int8,full,success in variants:
   if not success and source==original:raise RuntimeError('unapplied mutant '+name)
   src=td/'dut.sv';src.write_text(source);exe=td/'sim'
   c=subprocess.run(['iverilog','-g2012','-s','tb_qwen_a_gateway_equivalence',f'-Ptb_qwen_a_gateway_equivalence.INT8={int8}',f'-Ptb_qwen_a_gateway_equivalence.FULL={full}','-o',str(exe),str(src),str(ref),str(ROOT/DEC),str(ROOT/TB)],capture_output=True,text=True)
   if c.returncode:raise RuntimeError(c.stdout+c.stderr)
   r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(OUT/(name+'.log')).write_text(r.stdout+r.stderr)
   if (r.returncode==0)!=success:raise RuntimeError(name+': '+r.stdout+r.stderr)
   if not success and 'GATEWAY_MISMATCH'not in r.stdout:raise RuntimeError('wrong mutant cause '+name)
   tests.append(dict(case=name,status='PASS'if success else'REJECTED_GATEWAY_MISMATCH',exit_code=r.returncode))
 receipt=dict(status='PASS_COMPONENT_RTL_EQUIVALENCE_NOT_PHYSICAL_RELEASE',reference_commit=FROZEN,reference_inline_sha256=hashlib.sha256(raw.encode()).hexdigest(),state_bits=466,logical_cycle_delta=0,tests=tests,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in [CORE,SRC,TB,DEC,'tools/qwen_host/check_a_operand_gateway.py','tools/uarch_model.py','results/arch/qwen_a_operand_gateway_1015/partition_model.json']})
 (OUT/'source.json').write_text(json.dumps(receipt,indent=2)+'\n');print('PASS 3 real gateway equivalence configurations and 5 cause-specific RTL mutants')
if __name__=='__main__':main()
