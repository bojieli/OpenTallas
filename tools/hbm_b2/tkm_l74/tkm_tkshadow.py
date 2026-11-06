#!/usr/bin/env python3
"""Add a dormant, cycle-exact shadow of the native tick-153 calendar."""
from pathlib import Path
import hashlib,json,re,argparse
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
s=a.source.read_text();before=hashlib.sha256(s.encode()).hexdigest()
if 'OT_TKM_TK_SHADOW' in s: raise SystemExit('already transformed')
m=re.search(r'  reg \[31:0\] _60260_;\n  always @\(posedge clk, negedge rst_n\)\n    if \(!rst_n\) _60260_ <= 32\x27d0;\n    else _60260_ <= (?P<d>[^;]+);',s)
assert m,'native tick register ownership changed'
d=m['d'];assert len(re.findall(r'_\d+_',d))==32
line=next(x for x in s.splitlines() if x.startswith('  assign { \\u.tk[31]') and x.endswith("- 32'd153;"))
lhs,rhs=line.split(' = ',1)
assert rhs.count('\\u.tick[')==32
add="\n`ifdef OT_TKM_TK_SHADOW\n  // Native tick ownership copied exactly; shadow == tick-153 at every edge.\n  reg [31:0] ot_tk_shadow_q;\n  always @(posedge clk, negedge rst_n)\n    if (!rst_n) ot_tk_shadow_q <= 32'hffffff67;\n    else ot_tk_shadow_q <= "+d+" - 32'd153;\n`endif"
s=s[:m.end()]+add+s[m.end():]
s=s.replace(line,'`ifdef OT_TKM_TK_SHADOW\n'+lhs+' = ot_tk_shadow_q;\n`else\n'+line+'\n`endif')
a.source.write_text(s)
a.receipt.parent.mkdir(parents=True,exist_ok=True)
a.receipt.write_text(json.dumps({'source':str(a.source),'base_sha256':before,'candidate_sha256':hashlib.sha256(s.encode()).hexdigest(),'native_tick_block':m.group(0),'native_D':d,'old_tk_assignment':line,'shadow_reset_hex':'ffffff67','declared_extra_state_bits':32,'added_cycles':0,'scope':'exact native tick reset/clock/unconditional D; all downstream uses unchanged'},indent=2)+'\n')
