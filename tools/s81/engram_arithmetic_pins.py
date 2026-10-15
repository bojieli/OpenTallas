#!/usr/bin/env python3
"""Assign actual Engram arithmetic roots while parent control packing proceeds.
Shared arithmetic masters have registered S inputs and N outputs. These are real
source-port contracts, not permission to infer unmeasured parent crossings.
"""
import json,hashlib
from pathlib import Path
import v19_pins_1014 as V
R=Path(__file__).resolve().parents[2]
INVENTORY=Path('/home/ubuntu/wt/s81-engram-mix-1014/results/rtl/s81_engram_mix_1014/leaf_inventory.json')
def main():
 inv=json.loads(INVENTORY.read_text());out=R/'physical/s81_die_pins/v20_engram_arithmetic';out.mkdir(exist_ok=True);receipt=[]
 for suffix in ['mul4','chunk8','add8','norm','signed_sqrt','sigmoid']:
  name='ot_s81_engram_'+suffix;ip=inv[name];pp={};cursor={'S':20.052,'N':20.052}
  for p,v in ip['ports'].items():
   n=v['bits']
   if p in ['clk','arst_n']:continue
   f='S' if v['direction']=='input' else 'N';start=cursor[f];pp[p]=[[f,'M5',round(start+.096*i,3),.084] for i in range(n)];cursor[f]+=.096*n+.96
  pp['clk']=[['W','M4',4.032,.084]];pp['arst_n']=[['W','M4',4.992,.084]]
  V.write(out,name,[181.44,129.6],pp,'clk','registered operands/control S; registered arithmetic outputs N; independent W stream root/reset','v20_engram_arithmetic',{'source':'tools/s81/engram_arithmetic_pins.py','source_parameters':ip['parameters'],'clock_entries':{'stream':['clk']},'reset_entries':{'stream':['arst_n']},'adoption':'actual source native CTS/TT/FF/DRC required; no arithmetic parent/reach/clock-calendar qualification implied'})
  assert {p:len(v) for p,v in pp.items()}=={p:v['bits'] for p,v in ip['ports'].items()}
  receipt.append({'master':name,'outline_um':[181.44,129.6],'port_bits':sum(v['bits'] for v in ip['ports'].values()),'params':ip['parameters']})
 (out/'receipt.json').write_text(json.dumps({'source_inventory':'results/rtl/s81_engram_mix_1014/leaf_inventory.json from real Engram owner tree','inventory_sha256':hashlib.sha256(INVENTORY.read_bytes()).hexdigest(),'masters':receipt,'parent_status':'OPEN layout/control fanout/33roots/globalVM+staticflight; scalar tree and control master pins require actual neighbor plan','qualification':'native leaf assignment only, no generic-leaf equivalence or current whole-MIX fit claim'},indent=1)+'\n');print('ENGRAM_ARITHMETIC6masters exactsource ports',receipt)
if __name__=='__main__':main()
