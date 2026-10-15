#!/usr/bin/env python3
"""Assign actual static command issuer, preserving the old engine0..6 faces.
All13 engines exist in the source; role masks and static calendars are compiler
contracts. Added endpoints need actual fixed transport relays before adoption.
"""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def main():
 out=R/'physical/s81_die_pins/v20_static_seq';out.mkdir(exist_ok=True)
 src=R/'physical/s81_die_pins/v18/generated/dsfd_stage_seq_c.json';old=json.loads(src.read_text());pp={}
 for p,v in old['ports'].items():pp[p]=[[v['face'],v['layer'],round(v['at'][0]+i*v['at'][1],3),v['depth']] for i in range(v['bits'])]
 for e in range(7,13):
  x=100.044+32.064*(e-7)
  for p,n in [(f'c{e}',85),(f'd{e}',9),(f's{e}',2)]:
   pp[p]=[['N','M5',round(x+.096*i,3),.084] for i in range(n)];x+=.096*n+.96
 pp['ckv']=[['S','M5',1680.012,.084]];pp['rsv']=[['S','M5',1680.972,.084]]
 occ=sorted((v[0],v[1],v[2],p) for p,vs in pp.items() for v in vs)
 for a,b in zip(occ,occ[1:]):assert a[:2]!=b[:2] or b[2]-a[2]>=.0475,(a,b)
 rec={'schema':'opentallas.s81.assigned_pins.v1','master':'dsfd_stage_seq_static_c','case':'v20_static_seq','outline_um':[1727.976,88.536],'ports':{p:{'bits':len(v),'uniform':False,'per_bit':v} for p,v in pp.items()},'clock_entries':{'stream':['ck[0]'],'serial':['ckv[0]']},'reset_entries':{'stream':['rst[0]'],'serial':['rsv[0]']},'vector_ports':['ck','ckv','rst','rsv'],'preserved_predecessor_pin_source':str(src.relative_to(R)),'source':'tools/s81/static_seq_pins.py','adoption':'NEW source: actual128x76 calendar and2contexts, all13engine ports; native CTS/TT/FF/DRC, real static transport and physical3:4 epoch remain required'}
 (out/'dsfd_stage_seq_static_c.json').write_text(json.dumps(rec,indent=1)+'\n')
 lines=[]
 for p,vs in pp.items():
  for i,(f,ly,c,d) in enumerate(vs):
   x,y={'N':(c,88.494),'S':(c,.042),'W':(.042,c),'E':(1727.934,c)}[f]
   nm=f'{p}[{i}]' if len(vs)>1 or p in rec['vector_ports'] else p
   lines.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary')
 (out/'dsfd_stage_seq_static_c.tcl').write_text('\n'.join(lines)+'\n')
 home={'name':'sp_sseq','cell':'dsfd_stage_seq_static_c','outline':{'w':1727.976,'h':88.536},'origin':{'x':13942.8,'y':19461.6,'orient':'R0'},'kind':'native_successor_reservation','parent':'s81_layer1','pin_file':'physical/s81_die_pins/v20_static_seq/dsfd_stage_seq_static_c.tcl','qualification':'static source all13engines, native gate/phase/transport required; no predecessor functional/timing equivalence'}
 (out/'home.json').write_text(json.dumps(home,indent=1)+'\n')
 p=R/'results/arch/hier_contract_1011/s81.json';d=json.loads(p.read_text());d['slots']=[s for s in d['slots'] if s.get('name')!='sp_sseq']+[home];p.write_text(json.dumps(d,indent=1)+'\n');print('STATIC_ISSUER13engines',sum(len(v) for v in pp.values()),'pins assigned,legacy0..6faces preserved')
if __name__=='__main__':main()
