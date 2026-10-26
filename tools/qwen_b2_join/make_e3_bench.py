#!/usr/bin/env python3
"""Use the actual E3 specialized VM, with every native physical leaf clock exposed."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools'))
from die_port_bind import parse_modules
p=R/'rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3.sv'
m=parse_modules(p.read_text(),str(p))[0]
s=(R/'tools/qwen_b2_join/tb_b2_train.sv').read_text();a=s.index('qfd_sp_vector_memory_b2 #(');b=s.index('function automatic',a)
expr={'ck':'clk','rst_n':'rst_n','mee':"1'b1",'svr':'svr','svq':'svq','svq_v':'svq_v','ld':'ld','fault':'vf'};cons=[]
for n,(d,_)in m.ports.items():
 bits=m.width(n,m.env())
 if n in expr:e=expr[n]
 elif n.startswith('rb')and len(n)==3:e=f'rb[{n[-1]}]'
 elif n.endswith('_ck')or n.startswith('ck_'):e=f'{{{bits}{{clk}}}}'if bits>1 else'clk'
 elif d=='input':e="'0"
 else:e=''
 cons.append(f'.{n}({e})')
s=s[:a]+m.name+' dut('+',\n'.join(cons)+');\n'+s[b:]
s=s.replace('module tb_b2_train;','module tb_b2_train_e3;').replace('PASS b2 native halftrain SRAM','PASS b2 E3 partitioned2572clock native halftrain SRAM')
(R/'tools/qwen_b2_join/tb_b2_train_e3.sv').write_text(s)
