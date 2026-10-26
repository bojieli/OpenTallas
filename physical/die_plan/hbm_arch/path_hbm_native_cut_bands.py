#!/usr/bin/env python3
"""Reserve real M5/M7 tracks for measured native-W128 HBM cut demand.

The repaired W64 model was not a W128 capacity receipt. Native measurements need
5089bits through b003 and4128 through b011. Cores stay cappedM5; M7 is available
above them. Band reservations consume existing tracks, never raise a budget.
"""
import argparse,copy,json,shutil
from pathlib import Path


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--src',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
 if a.out.exists():raise FileExistsError(a.out)
 p=json.loads((a.src/'die_plan.json').read_text());receipt=[]
 for tn in ('q_b003','q_b011'):
  t=p['partition_types'][tn];w,h=t['outline_um'];before=copy.deepcopy(t.get('die_ft_bands',[]));bands=[]
  for b in before:
   b=copy.deepcopy(b)
   if b['dir']=='NS':b['layers']=[x for x in b['layers'] if x!='M7']
   if b['layers']:bands.append(b)
  bands.append(dict(dir='NS',span_um=[0,w],layers=['M7'],die_share=1.,note='D-HBM-B1 nativeW128: measured vertical FT demand, full free M7 above M5 cores; own vertical glue uses M3/M5'))
  if tn=='q_b011':
   lo,hi=285.12,371.52
   if not 0<=lo<hi<=w:raise ValueError('q_b011 bank outline changed')
   for c in t['hard_cores']:
    x,_=c['origin_um'];cw,_=c['outline_um']
    if x<hi and x+cw>lo:raise ValueError('new M5 band crosses a core')
   bands.append(dict(dir='NS',span_um=[lo,hi],layers=['M5'],die_share=1.,note='D-HBM-B1 nativeW128: core-free right channel, extra tracks for4128b; reserved after8.64um HC halo'))
  t['die_ft_bands']=bands;receipt.append(dict(type=tn,before=before,after=bands))
 shutil.copytree(a.src,a.out);(a.out/'die_plan.json').write_text(json.dumps(p,indent=1)+'\n');(a.out/'native_cut_bands_report.json').write_text(json.dumps(dict(qualification='PLAN_CAPACITY_ONLY',added_cycles=0,outline_growth=0,changes=receipt,pending='actual infrastructure-first leftover GRT + tile own-routing trial'),indent=1)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
