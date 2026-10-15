#!/usr/bin/env python3
"""Add a read-only scalar-result check to the already compiled real RTL image.

The selected macro has repair straps tied inactive. Its physical array uses
MUX2: address row=a>>1, column=2*b+(a&1). This checker reads the resulting SRAM
cells after simulation; it supplies no DUT operand or arithmetic result.
"""
from pathlib import Path
import argparse,re,subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_golden as G
import numpy as np
p=argparse.ArgumentParser();p.add_argument('build',type=Path);p.add_argument('vectors',type=Path);a=p.parse_args()
root=Path(__file__).resolve().parents[2];obj=a.build/'obj'
header=(obj/'Vtb_qwen_embedding_stage___024root.h').read_text()
pattern=r'\b(\w+)\*\s+(\w*u_control_vm\w*u_vm\w*g_t__BRA__7__KET__\w*u_t\w*g_b__BRA__2__KET__\w*u_bt);'
fields=set(re.findall(pattern,header))
if len(fields)!=1:raise RuntimeError('cannot uniquely bind actual RMS SRAM bank58; found '+repr(fields))
bank_type,bank_pointer=fields.pop()
bank_header=(obj/(bank_type+'.h')).read_text()
array='u_b__DOT__g_mac__DOT__u_lo__DOT__arr'
if not re.search(r'\b'+array+r'\b',bank_header):raise RuntimeError('selected bank does not expose actual mapped SRAM storage')
field=bank_pointer+'->'+array
bits=np.array([int(x,16)for x in(a.vectors/'expected.hex').read_text().split()],dtype=np.uint32)
expected=G.reduce_chunked([G.mul(v,v)for v in bits.view(np.float32)])
expected_bits=int(np.array([expected],dtype=np.float32).view(np.uint32)[0])
source=(root/'tools/qwen_split/embedding_stage_main.cpp').read_text().replace('#include <verilated.h>','#include <verilated.h>\n#include <cstdio>\n#include "Vtb_qwen_embedding_stage___024root.h"\n#include "'+bank_type+'.h"')
check=f'''    // RMS scalar14240 -> row890 -> bank58,line13,lane0.
    uint32_t actual=0;
    for(unsigned b=0;b<32;++b){{unsigned c=2*b+1;actual|=((top.rootp->{field}[6][c/32]>>(c%32))&1U)<<b;}}
    if(actual!=0x{expected_bits:08x}U){{std::fprintf(stderr,"FAIL actual SRAM RMS scalar got%08x expected{expected_bits:08x}\\n",actual);return 3;}}
    std::printf("PASS actual mapped SRAM RMS scalar14240=%08x repository R-ARITH reference\\n",actual);
'''
source=source.replace('    top.final();',check+'    top.final();')
cpp=a.build/'reduction_readback_main.cpp';cpp.write_text(source)
(a.build/'reduction_expected.hex').write_text(f'{expected_bits:08x}\n')
(a.build/'reduction_binding.txt').write_text(field+'\n')
libs=sorted(str(x)for x in obj.rglob('*.a')if x.name!='libverilated.a')
cmd=['g++','-std=c++20','-O2','-I'+str(obj),'-I/usr/share/verilator/include','-I/usr/share/verilator/include/vltstd',str(cpp),'/usr/share/verilator/include/verilated.cpp','/usr/share/verilator/include/verilated_timing.cpp','/usr/share/verilator/include/verilated_threads.cpp','-Wl,--start-group']+libs+['-Wl,--end-group','-pthread','-latomic','-o',str(obj/'Vtb_qwen_embedding_stage_readback')]
subprocess.run(cmd,check=True)
print('BOUND_ACTUAL_SRAM_RMS',f'{expected_bits:08x}',field)
