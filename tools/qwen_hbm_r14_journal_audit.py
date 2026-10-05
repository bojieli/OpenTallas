#!/usr/bin/env python3
"""Partial independent checks of emitted observations; never invent events."""
import csv
import json
from decimal import Decimal
from pathlib import Path

def audit(path):
    with path.open() as stream:
        rows=list(csv.DictReader(stream,delimiter='\t'))
    failures=[];columns={};backing={};counts={}
    for r in rows:
        event=r['event'];counts[event]=counts.get(event,0)+1
        t=Decimal(r['observe_ps']);key=tuple(int(r[n]) for n in ['stack','tag','beat','sector'])
        if event=='CMD' and int(r['op']) in [2,3]:
            s=int(r['sector']);pc=((s>>2)^(s>>7)^(s>>12))&31
            bank=((((s>>12)^((s>>15)>>2))&7)<<2)|((s^(s>>15))&3)
            if int(r['pc'])!=pc or int(r['bank'])!=bank:failures.append({'event':r,'reason':'BANKMAP'})
            if not 0<=s<703125000:failures.append({'event':r,'reason':'FULL_ADDRESS_BOUND'})
            columns[key]=(t,int(r['op']))
        if event=='BACKING_WRITE':
            previous=columns.get(key)
            if previous is None or previous[1]!=3 or t-previous[0]<7274:
                failures.append({'event':r,'reason':'SOURCE_CWL_PLUS_BURST_MINIMUM_7274PS','column':str(previous)})
            backing[key]=t
        if event=='OWNED' and int(r['op'])==1:
            if key not in backing or backing[key]>t:failures.append({'event':r,'reason':'WRITE_VISIBLE_BEFORE_BACKING'})
    return {'status':'FAIL' if failures else 'PARTIAL_CHECKS_PASS_NOT_PROVIDER_PASS',
            'events':len(rows),'counts':counts,'failures':failures,
            'open_checks':['Full source bank timing/current refresh/turnaround',
                           'Allocation generations through queue reorder and tag quarantine',
                           '272/288 exact retirement and IRS/lease dependencies',
                           'Intended mutant failure reason, not arbitrary nonzero exit']}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('journal',type=Path);a=p.parse_args()
    print(json.dumps(audit(a.journal),indent=2,sort_keys=True))
