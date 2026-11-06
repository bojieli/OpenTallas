#!/usr/bin/env python3
"""Apply reviewed q3 FORM A generator arguments after physical PASS. No other module is changed."""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('config');ap.add_argument('--write',action='store_true');a=ap.parse_args()
p=Path(a.config);s=json.loads(p.read_text());row=s['dies']['hbm']['core_kit']['item_args']['ot_hfd_coll_q3_vm_core'];out=[];i=0
while i<len(row):
 if row[i]=='--face-lockup':i+=2;continue
 if row[i]=='--face-stage' and row[i+1].split('=')[0]=='^writer_kq[0-7]$':i+=2;continue
 out.append(row[i]);i+=1
out+=['--face-lockup','^(?!writer_kq[0-7]$).*','--face-stage','^writer_kq[0-7]$=1']
print(json.dumps({'before':row,'after':out},indent=1))
if a.write:
 s['dies']['hbm']['core_kit']['item_args']['ot_hfd_coll_q3_vm_core']=out;p.write_text(json.dumps(s,indent=1)+'\n')
