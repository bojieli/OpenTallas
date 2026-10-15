#!/usr/bin/env python3
"""Assign real engine10 static lookup/MIX command fanout and completion leaf."""
import json,gzip
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_functional';pp={}
 for face,ports in [('E',[('c_cmd',85),('c_done',9),('c_st',2)]),('W',[('t_mix_cmd',85),('f_mix_done',9),('f_mix_st',2)]),('N',[('t_lk_cmd',85),('f_lk_done',9),('f_lk_st',2)])]:
  x=20.064
  for p,n in ports:
   pp[p]=[[face,'M5' if face=='N' else 'M4',round(x+.096*i,3),.084] for i in range(n)];x+=n*.096+.96
 pp['ck']=[['S','M5',4.044,.084]];pp['rst']=[['S','M5',5.004,.084]]
 fn=V.write(out,'ot_s81_engram_dispatch',[129.6,86.4],pp,'ck','E actual85bit sequencer; W MIX command/result; N lookup command/result; own stream clock root','v20_engram_dispatch',{'source':'tools/s81/engram_dispatch_pins.py','clock_entries':{'stream':['ck[0]']},'reset_entries':{'stream':['rst[0]']},'vector_ports':['ck','rst'],'adoption':'new source; source protocol+native CTS/TT/FF/DRC and physical fixed completion-slot phase must pass'})
 tcl=fn.with_suffix('.tcl');tcl.write_text(tcl.read_text().replace('-pin_name {ck}', '-pin_name {ck[0]}').replace('-pin_name {rst}', '-pin_name {rst[0]}'))
 home={'name':'sp_engram_dispatch','master':'ot_s81_engram_dispatch','at_um':[15120.,23007.6],'outline':{'w':129.6,'h':86.4},'clock':'stream_1p2','geometry':'full xsp7 instance rectangle0overlaps;21.6um above embedding,25.2um east of MIX face; no collision with reserved HCP/controller/gatherpack','pin_file':'physical/s81_die_pins/v20_functional/ot_s81_engram_dispatch.tcl','qualification':'real static engine10arg23 dispatch; lookup home/long sequencer relays and completion phase still OPEN'}
 (out/'dispatch_home.json').write_text(json.dumps(home,indent=1)+'\n')
 p=R/'results/arch/hier_contract_1011/s81.json';d=json.loads(p.read_text());d['slots']=[s for s in d['slots'] if s.get('name')!='sp_engram_dispatch']+[home];p.write_text(json.dumps(d,indent=1)+'\n');print('ENGRAM_DISPATCH1root assigned129.6x86.4')
if __name__=='__main__':main()
