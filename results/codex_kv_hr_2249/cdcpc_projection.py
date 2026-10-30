#!/usr/bin/env python3
"""Opt-in completion of CDC_PC_DELTA(500db930a): project18 reserved output bits.
Retain the exact full-width internal state; only public port width changes.
No parent tie lowering is implied; caller must emit declared parent constants.
"""
import re,argparse,json
from pathlib import Path

def project(s,name='qkd_hr_cdc_pc_projected',mutant=False):
 s,n=re.subn(r'\bmodule qkd_hr_cdc_pc\s*\(', 'module '+name+'(',s,count=1)
 if n!=1:raise ValueError('wrong CDC_PC top')
 for kind in ('output','reg'):
  s,n=re.subn(r'\b'+kind+r' \[545:0\] u_tx__o_d;',kind+' [527:0] u_tx__o_d;',s,count=1)
  if n!=1:raise ValueError('unexpected TX output shape')
 s,n=re.subn(r'(?m)^    u_tx__o_d <= \\u_tx\.od_q ;$',r'    begin u_tx__o_d <= \\u_tx.od_q [527:0]'+(" ^ 528'd1" if mutant else '')+r'; _hr_tx_reserved <= \\u_tx.od_q [545:528]; end',s)
 if n!=1:raise ValueError('unexpected TX output register assignment')
 s=s.replace('  reg [527:0] u_tx__o_d;','  reg [527:0] u_tx__o_d;\n  reg [17:0] _hr_tx_reserved;')
 read_n=0
 def read(m):
  nonlocal read_n
  i=int(m[1])
  if i<528:return m[0]
  read_n+=1;return '_hr_tx_reserved['+str(i-528)+']'
 s=re.sub(r'\bu_tx__o_d\s*\[(\d+)\]',read,s)
 return s,dict(public_tx_width=528,removed_reserved_bits=list(range(528,546)),private_state_retained=True,added_cycles=0,changed_reserved_alias_reads=read_n,mutant=mutant,parent_constants='NOT LOWERED; adoption held')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('out');p.add_argument('--mutant',action='store_true');a=p.parse_args();s,r=project(Path(a.source).read_text(),mutant=a.mutant);Path(a.out).write_text(s);print(json.dumps(r))
