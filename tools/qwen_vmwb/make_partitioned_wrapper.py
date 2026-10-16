#!/usr/bin/env python3
"""Emit additive opt-in parent ABI; existing production master stays byte-identical."""
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parents[2]
src=R/'rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory_par.sv'
s=src.read_text();old='qfd_sp_vector_memory_par';new=old+'_partitioned'
s=s.replace('module '+old+' (','module '+new+' (',1)
s=s.replace('    input wire ck,','    input wire [1007:0] native_ck,\n    input wire [95:0] return_ck,\n    input wire [2:0] read_control_ck,\n    input wire ck,',1)
removed=[]
for r in range(8):
 for i in [3*b+2 for b in range(8)]+[34+3*j for j in range(6)]:
  n=f'ck_r{r}_{i}';line=f'    input wire {n},\n';assert line in s;s=s.replace(line,'',1)
  # These old single-bank entries are elaboration-dead when independent bank clocks are selected.
  s=s.replace(f'.{n}({n})',f'.{n}(1\'b0)');removed.append(n)
s=s.replace('.PAR_RB(1), .PMUT(0), .NATIVE_BANKS(1)', '.PAR_RB(1), .PMUT(0), .NATIVE_BANKS(1),\n        .USE_NATIVE_CLOCKS(1), .RETURN_LEAVES(1), .READ_CONTROL_LEAVES(1), .RETURN_CLOCKS(1)',1)
s=s.replace('        .ck(ck),','        .native_ck(native_ck), .return_ck(return_ck), .read_control_ck(read_control_ck),\n        .ck(ck),',1)
assert s.count('.native_ck(native_ck)')==1
s='''// UNADOPTED parent source candidate. Full actual RTL is retained; residual write/control
// logic is not yet hardened, and no parent timing/fit is claimed. Native bank clock
// order is region-major,14banks/region,9pins/bank; old dormant bank-clock ABI pins
// are removed from this physical top. Return/control roots have no added RTL edges.
'''+s
out=src.with_name(new+'.sv');out.write_text(s)
manifest={'scope':'Actual additive source ABI only; no physical qualification','base_source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'new_top':new,'removed_dormant_clock_pins':removed,'new_clock_pins':{'native_ck':1008,'return_ck':96,'read_control_ck':3},'active_clock_entries_including_residual_parent_ck':1483,'port_bits':15864,'normal_edges_added':0,'open':'Remaining residual write/control/relay FFs; die homes/cuts/actual phase timing/parent route'}
p=R/'results/arch/qwen_vm_residual_1015/partitioned_parent_abi.json';p.write_text(json.dumps(manifest,indent=2)+'\n')
print(out)
