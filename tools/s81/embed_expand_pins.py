#!/usr/bin/env python3
"""Place the real SRAM embedding expansion leaf in a verified upper-spine void.
Upstream full-table bank selection and S000 source-role controller binding remain
explicit independent obligations; the slot does not qualify either by inference.
"""
import json
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_embedding';out.mkdir(exist_ok=True)
 pp={};y=40.032
 for p,n in [('rom_d',512),('rom_idx',9),('rom_v',1),('header',512),('vm_base',14),('start',1)]:
  pp[p]=[['W','M4',round(y+.096*i,3),.192] for i in range(n)];y+=.096*n+.96
 x=40.032
 for p,n in [('vm_d',512),('vm_row',14),('vm_v',1),('hop_d',512),('hop_v',1),('hop_last',1)]:
  pp[p]=[['S','M5',round(x+.096*i,3),.192] for i in range(n)];x+=.096*n+.96
 for p,c in [('clk',4.032),('rst_n',4.992)]:pp[p]=[['N','M5',c,.192]]
 for p,c in [('busy',40.032),('done',40.992),('fault',41.952)]:pp[p]=[['E','M4',c,.192]]
 V.write(out,'ot_s81_embed_expand',[216.,216.],pp,'clk','W native ROM and source command; S native VM/hop fixed-calendar output; N root/reset','v20_embedding_source',{'source':'tools/s81/embed_expand_pins.py','adoption':'S000 input source role, full upstream ROM bank choice and fixed link/VM commit calendar remain unqualified'})
 home={'name':'sp_embed_expand','master':'ot_s81_embed_expand','at_um':[15120.,22770.],'outline':{'w':216.,'h':216.},'clock':'stream_1p2','role':'S000 source/input role; ordinary layer1 c8 excludes engine9 and must not falsely bind it','engine':9,'geometry':'xsp7 full instance plan at exact rectangle:0collisions; new MIX ends15094.8 leaving25.2umgap','memory':{'master':'ot_sram_1r1w_512x128_m4_r2c2','count':2,'size_um':[174.096,29.7]},'pin_file':'physical/s81_die_pins/v20_embedding/ot_s81_embed_expand.tcl','qualification':'NATIVE_LEAF_RESERVATION; role-specific controller and full-table ROM topology OPEN'}
 (out/'home.json').write_text(json.dumps(home,indent=1)+'\n')
 p=R/'results/arch/hier_contract_1011/s81.json';d=json.loads(p.read_text());d['slots']=[s for s in d['slots'] if s.get('name')!='sp_embed_expand']+[home];d['v20_embedding_home']='physical/s81_die_pins/v20_embedding/home.json';p.write_text(json.dumps(d,indent=1)+'\n')
 print('EMBED_EXPAND216x216 native source role reservation')
if __name__=='__main__':main()
