#!/usr/bin/env python3
"""Screen physical-only hub register anchors against complete existing connectivity."""
import json,re,sys,copy
from pathlib import Path
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot')
import geom_rules as G
D=G.Design(sys.argv[1]);before=G.r2r_metrics(D);moves=[]
for cid,c in list(D.cells.items()):
 n=c[6];mm=re.search(r'zh_err_q\\?\[(\d+)\\?\]',n);gm=re.search(r'\.gz\\?\[(\d+)\\?\]',n)
 if not (mm or gm):continue
 group=int(mm[1])//4 if mm else int(gm[1]);bit=int(mm[1])%4 if mm else 0
 # Each group's error launch and reduction meet in the empty channel between
 # the upper and lower macro rows. Macro and boundary-flop sites stay fixed.
 x=(160 if group in (0,2) else 300)+(bit*1.3 if mm else 8)
 y=(232 if group<2 else 248)+(0 if mm else 2)
 w,h=c[4]-c[2],c[5]-c[3]
 D.cells[cid]=c[:2]+(x,y,x+w,y+h)+c[6:]
 moves.append({'name':n,'old_xy':[c[2],c[3]],'xy_um':[x,y]})
after=G.r2r_metrics(D)
print(json.dumps({'before':before,'after':after,'moves':moves},indent=1))
