#!/usr/bin/env python3
"""Apply actual-tech M8 minimum-area landing fix without changing contact paths."""
import argparse,json,shutil
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args();s=Path(a.source);o=Path(a.out);o.mkdir(parents=True,exist_ok=True);d=json.load(open(s/'access_plan.json'));r=json.load(open(s/'reserved_access.json'));assert len(r)==27*len(d['paths'])
for i,q in enumerate(d['paths']):
 n,ly,x0,y0,x1,y1=r[i*27+8];x=q['stack'][0]/1000;assert n==q['net'] and ly=='M8' and round((x0+x1)*500)==q['stack'][0]
 r[i*27+8]=[n,ly,round(x-.096,3),y0,round(x+.096,3),y1]
json.dump(r,open(o/'reserved_access.json','w'),separators=(',',':'));shutil.copy2(s/'access_plan.json',o/'access_plan.json');ss=json.load(open(s/'summary.json'));ss['m8_minimum_landing_nm']=[192,40];ss['m8_minimum_area_dbu2']=7520;ss['constructed_landing_area_dbu2']=7680;ss['source119_recheck']='pending';json.dump(ss,open(o/'summary.json','w'),indent=2);print(ss)
