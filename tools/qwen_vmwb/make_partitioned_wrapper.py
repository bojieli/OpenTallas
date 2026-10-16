#!/usr/bin/env python3
"""Emit additive opt-in parent ABI; existing production master stays byte-identical."""
from pathlib import Path
import argparse,hashlib,json,re
p=argparse.ArgumentParser();p.add_argument("--return-ro",type=int,default=1);p.add_argument("--return-pin-input",type=int,choices=[0,1],default=0);args=p.parse_args()
assert args.return_ro>=1
ro=args.return_ro;pin=args.return_pin_input;relay_clocks=8*(22+14*ro)+(6*(10+ro)+255)//256
R=Path(__file__).resolve().parents[2]
src=R/'rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory_par.sv'
s=src.read_text();old='qfd_sp_vector_memory_par';new=old+'_partitioned'+('' if ro==1 else f'_ro{ro}')+('_pin'if pin else'')
s=s.replace('module '+old+' (','module '+new+' (',1)
s=s.replace('    input wire ck,',f'    input wire [1007:0] native_ck,\n    input wire [95:0] return_ck,\n    input wire [2:0] read_control_ck,\n    input wire [{relay_clocks-1}:0] relay_ck,\n    input wire ck,',1)
removed=[]
for r in range(8):
 for i in [4*b+2 for b in range(8)]+[34+3*j for j in range(6)]:
  n=f'ck_r{r}_{i}';line=f'    input wire {n},\n';assert line in s;s=s.replace(line,'',1)
  # These old single-bank entries are elaboration-dead when independent bank clocks are selected.
  s=s.replace(f'.{n}({n})',f'.{n}(1\'b0)');removed.append(n)
s=s.replace('.PAR_RB(1), .PMUT(0), .NATIVE_BANKS(1)', f'.PAR_RB(1), .PMUT(0), .NATIVE_BANKS(1), .RETURN_RO({ro}), .RETURN_PIN_INPUT({pin}),\n        .USE_NATIVE_CLOCKS(1), .RETURN_LEAVES(1), .READ_CONTROL_LEAVES(1), .RETURN_CLOCKS(1), .RELAY_TILES(1)',1)
s=s.replace('        .ck(ck),','        .native_ck(native_ck), .return_ck(return_ck), .read_control_ck(read_control_ck), .relay_ck(relay_ck),\n        .ck(ck),',1)
assert s.count('.native_ck(native_ck)')==1
s=f'''// UNADOPTED parent source candidate. Full actual RTL is retained; residual write/control
// logic is not yet hardened, and no parent timing/fit is claimed. Native bank clock
// order is region-major,14banks/region,9pins/bank; old dormant bank-clock ABI pins
// are removed from this physical top. Return transport RO={ro}: {ro-1} additional normal edges versus production RO1.
'''+s
out=src.with_name(new+'.sv');out.write_text(s)
manifest={'scope':'Actual additive source ABI only; no physical qualification','base_source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'new_top':new,'removed_dormant_clock_pins':removed,'new_clock_pins':{'native_ck':1008,'return_ck':96,'read_control_ck':3,'relay_ck':relay_clocks},'active_clock_entries_including_residual_parent_ck':1483+relay_clocks,'port_bits':15864+relay_clocks,'normal_edges_added':{'row_read':ro-1,'SU_answer':ro-1+pin},'open':'Remaining residual write/control FFs; die homes/cuts/actual phase timing/parent route'}
p=R/('results/arch/qwen_vm_residual_1015/partitioned_parent_abi'+('' if ro==1 else f'_ro{ro}')+('_pin'if pin else'')+'.json');p.write_text(json.dumps(manifest,indent=2)+'\n')
print(out)
