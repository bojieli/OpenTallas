#!/usr/bin/env python3
"""Focused check of corrected actual clock VIA67 M7 enclosure against PG stems."""
import argparse,json
from shapely.geometry import box
from shapely.strtree import STRtree
p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--seed',required=True);p.add_argument('--out',required=True);a=p.parse_args();d=json.load(open(a.plan));seed=json.load(open(a.seed));rr=[(n,[round(v*1000) for v in r]) for n,ly,*r in seed if ly=='M7'];tree=STRtree([box(*r) for n,r in rr]);bad=[]
for i,q in enumerate(d['paths']):
 x,y=q['stack'];yy=q['m8'][1];r=[x-16-32,min(y-40,yy-40)-32,x+16+32,max(y+40,yy+40)+32]
 hits=[int(j) for j in tree.query(box(*r)) if r[0]<rr[j][1][2] and rr[j][1][0]<r[2] and r[1]<rr[j][1][3] and rr[j][1][1]<r[3]]
 if hits:bad.append(dict(group=i,net=q['net'],members=q['members'],pg_m7_with_spacing=r,clock_hits=[rr[j] for j in hits]))
s=dict(checked_groups=len(d['paths']),actual_m7_clock_bases=len(rr),conflicts=len(bad),failures=bad,verdict='PASS_CORRECTED_M7_ENCLOSURE' if not bad else 'FAIL_REPLAN_REQUIRED');json.dump(s,open(a.out,'w'),indent=2);print({k:v for k,v in s.items() if k!='failures'})
