#!/usr/bin/env python3
"""Reserve actual two-root HCP controller; no payload feedthrough ports.
The VM payload multicast is a staged die net, separate from controller metadata.
"""
import json
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_functional';out.mkdir(exist_ok=True)
 pp={};y=60.0
 for p,n in [('c_cmd',85),('c_done',9),('c_st',2)]:
  pp[p]=[['W','M4',round(y+.096*i,3),.192] for i in range(n)];y+=n*.096+.96
 x=60.0
 for p,n in [('rq_v',8),('rq_row',112),('rs_v',8)]:
  pp[p]=[['S','M5',round(x+.096*i,3),.192] for i in range(n)];x+=n*.096+.96
 y=80.0
 for p,n in [('stage_begin',1),('stage_v',1),('stage_word',7),('leaf_cmd_v',1),('leaf_ffn',1),('leaf_layer',6),('leaf_v',6),('leaf_fault',6),('leaf_d',192),('t_raw_v',1),('t_raw_d',192)]:
  pp[p]=[['E','M4',round(y+.096*i,3),.192] for i in range(n)];y+=n*.096+.96
 for p,x in [('cck',4.032),('crst_n',4.992),('sk',8.064),('srst_n',9.024)]:pp[p]=[['N','M5',x,.192]]
 V.write(out,'ot_s81_hcx_controller',[216.,216.],pp,'cck','W sequencer, S VM metadata, E projection leaf control/return; direct payload multicast outside this leaf', 'v20_hcp_controller',{'source':'tools/s81/hcx_controller_pins.py','clock_entries':{'stream':['cck'],'serial':['sk']},'reset_entries':{'stream':['crst_n'],'serial':['srst_n']},'adoption':'OPEN measured3:4 CDC/forward/return fixed calendar; FAST_CYC=0 must fault, never inferred qualification'})
 home={'name':'sp_hcx_ctl','master':'ot_s81_hcx_controller','at_um':[15362.4,22770.0],'outline':{'w':216.,'h':216.},'geometry':'exact xsp7 full instance rectangle0collisions;25um eastofembedding','pin_file':'physical/s81_die_pins/v20_functional/ot_s81_hcx_controller.tcl','qualification':'OPEN native two-root controller; parent wires+6 actual projection leaves+controller; no raw payload stub'}
 (out/'controller_home.json').write_text(json.dumps(home,indent=1)+'\n')
 p=R/'results/arch/hier_contract_1011/s81.json';d=json.loads(p.read_text());d['slots']=[s for s in d['slots'] if s.get('name')!='sp_hcx_ctl']+[home];p.write_text(json.dumps(d,indent=1)+'\n');print('HCP_CTL actual2root216x216 no4096payloadport')
if __name__=='__main__':main()
