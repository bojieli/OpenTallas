#!/usr/bin/env python3
"""Physical home for real parallel rank compaction, not a collective substitute."""
import json
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_functional';pp={};x=4.044
 for p,n in [('i_d',2048),('i_v',4)]:
  pp[p]=[['N','M5',round(x+.096*i,3),.084] for i in range(n)];x+=.096*n+.96
 x=40.044
 for p,n in [('wq_d',512),('wq_mask',16),('wq_row',14),('wq_v',1),('wq_commit',1)]:
  pp[p]=[['S','M5',round(x+.096*i,3),.084] for i in range(n)];x+=.096*n+.96
 y=10.032
 for p,n in [('start',1),('raw_base_row',14),('done',1),('fault',1)]:
  pp[p]=[['W','M4',round(y+.096*i,3),.084] for i in range(n)];y+=.096*n+.96
 pp['clk']=[['W','M4',4.032,.084]];pp['rst_n']=[['W','M4',4.992,.084]]
 V.write(out,'ot_s81_hcx_gatherpack',[216.,216.],pp,'clk','N actual4parallel512b padded rank records; S two compiled512b VM writes; W control/root/reset','v20_hcx_gatherpack',{'source':'tools/s81/hcx_gatherpack_pins.py','clock_entries':{'stream':['clk']},'reset_entries':{'stream':['rst_n']},'adoption':'OPEN: actual collective flights, all four R_CYC, VM WL, pair cuts/native clocks/reset; default zero-flight calendar is component only'})
 home={'name':'sp_hcx_gatherpack','master':'ot_s81_hcx_gatherpack','at_um':[15600.,22770.],'outline':{'w':216.,'h':216.},'pin_file':'physical/s81_die_pins/v20_functional/ot_s81_hcx_gatherpack.tcl','clock':'stream_1p2','geometry':'full xsp7 instance rectangle0overlaps;21.6um east of controller; disjoint all six HCP/MIX/embedding reservations','qualification':'NEW actual compaction leaf; no collective/VM transport latency claim'}
 (out/'gatherpack_home.json').write_text(json.dumps(home,indent=1)+'\n')
 p=R/'results/arch/hier_contract_1011/s81.json';d=json.loads(p.read_text());d['slots']=[s for s in d['slots'] if s.get('name')!='sp_hcx_gatherpack']+[home];p.write_text(json.dumps(d,indent=1)+'\n')
 print('HCP_GATHERPACK_ASSIGNED real4x512 parallel input216sq')
if __name__=='__main__':main()
