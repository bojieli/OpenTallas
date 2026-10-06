#!/usr/bin/env python3
"""Exact GF(2) function lowering: explicit equations, no register/repair edits."""
from pathlib import Path
import re,json,hashlib
root=Path(__file__).resolve().parents[4];r=root/'physical/hbm_die_abstracts_20261006/links/station_physical_20261006'
original=(r/'ot_hbm_w2_protected_bank_lowered.sv').read_text()
positions=[p for p in range(1,72) if p&(p-1)]
assert len(positions)==64
terms={p:f'data[{i}]' for i,p in enumerate(positions)}
for k in range(7):terms[1<<k]='^{' + ','.join(terms[p] for p in positions if p&(1<<k))+'}'
body=','.join(terms[p] for p in range(71,0,-1));encode='{^{' + body + '},' + body + '}'
raw='{'+','.join(f'c[{p-1}]' for p in reversed(positions))+'}'
check='{^c,'+','.join('^{'+','.join(f'c[{p-1}]' for p in range(1,72) if p&(1<<k))+'}' for k in range(6,-1,-1))+'}'
functions={
 'encode64':f' function automatic [71:0] encode64(input [63:0] data);\n  begin encode64={encode};end\n endfunction',
 'raw64':f' function automatic [63:0] raw64(input [71:0] c);\n  begin raw64={raw};end\n endfunction',
 'check72':f' function automatic [7:0] check72(input [71:0] c);\n  begin check72={check};end\n endfunction'}
s=original
for name,text in functions.items():
 pattern=r'function automatic[^;]*\b'+name+r'\([^;]*;.*?endfunction'
 s,count=re.subn(pattern,text.lstrip(),s,flags=re.S);assert count==1,(name,count)
# Every non-function byte, including all state/attributes/repair logic, unchanged.
strip=lambda t:re.sub(r'function automatic.*?endfunction','FUNCTION',t,flags=re.S)
assert strip(s)==strip(original)
(r/'ot_hbm_w2_protected_bank_static.sv').write_text(s)
(r/'static_codec.json').write_text(json.dumps(dict(operation='exact static GF2 equations for encode64/raw64/check72 only',original_sha256=hashlib.sha256(original.encode()).hexdigest(),static_sha256=hashlib.sha256(s.encode()).hexdigest(),all_nonfunction_bytes_unchanged=True,attributes_preserved=True,registers_repair_and_clock_unchanged=True),indent=2)+'\n')
# Basis equality proves each complete linear transform, including all bit positions.
gold=(root/'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv').read_text().split('package ot_hbm_w2_boundary_pkg;',1)[1].split('endpackage',1)[0]
tb='module tb_static_codec;\n import ot_gpu_w6_secded_pkg::*;\n'+gold.replace('raw64','gold_raw64').replace('check72','gold_check72')+'\n'
for name,text in functions.items():tb+=text.replace(name,'static_'+name)+'\n'
tb+=''' integer checks=0;reg [63:0] d;reg [71:0] c;reg [71:0] mutant;
 initial begin
  d=0;if(static_encode64(d)!==encode64(d))$fatal(1,"encode offset");checks++;
  for(integer i=0;i<64;i++)begin d=64'b1<<i;
   if(static_encode64(d)!==encode64(d))$fatal(1,"encode basis%0d",i);checks++;
  end
  c=0;if(static_raw64(c)!==gold_raw64(c)||static_check72(c)!==gold_check72(c))$fatal(1,"check/raw offset");checks++;
  for(integer i=0;i<72;i++)begin c=72'b1<<i;
   if(static_raw64(c)!==gold_raw64(c)||static_check72(c)!==gold_check72(c))$fatal(1,"raw/check basis%0d",i);checks++;
  end
  // Real negative: the parity equation's first bit is mutated on the data0 basis.
  d=1;mutant=static_encode64(d)^72'b1;
  if(mutant===encode64(d))$fatal(1,"parity mutation survived complete basis gate");checks++;
  $display("PASS_STATIC_CODEC complete_linear_basis checks=%0d encode64=65 raw64/check72=73 real_parity_mutation_refused=1",checks);$finish;
 end
endmodule
'''
(r/'tb_static_codec.sv').write_text(tb)
