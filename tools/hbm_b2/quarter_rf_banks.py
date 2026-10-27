#!/usr/bin/env python3
"""Reserve native RF logic on ASAP7 rows, including all combinational cells."""
import argparse, collections, json, math
from pathlib import Path

def allocate(cells):
    banks=collections.defaultdict(list)
    for c in cells:banks[c['bank']].append(c)
    positions={};reports=[]
    for bank,cs in sorted(banks.items()):
        box=cs[0]['region_um'];x,y,X,Y=box
        if any(c['region_um']!=box for c in cs):raise ValueError('inconsistent bank region')
        start=math.ceil((x-1e-8)/.054)*.054;bottom=math.ceil((y-1e-8)/.27)*.27
        rows=[dict(x=start,y=bottom+i*.27)for i in range(math.floor((Y-bottom+1e-8)/.27))]
        area=0.; rects=[]
        for c in sorted(cs,key=lambda c:(-c['dimensions_um'][0],c['cell'])):
            w,h=c['dimensions_um']
            if abs(h-.27)>1e-7 or abs(w/.054-round(w/.054))>1e-7:raise ValueError('unsupported row footprint '+c['master'])
            row=next((r for r in rows if r['x']+w<=X+1e-8),None)
            if row is None:raise ValueError('RF bank full '+str(bank))
            positions[c['cell']]=[row['x']+w/2,row['y']+h/2]
            rects.append([c['cell'],row['x'],row['y'],w,h]);row['x']+=w;area+=w*h
        fill=area/((X-x)*(Y-y))
        if fill>.6+1e-8:raise ValueError('RF bank exceeds 60%')
        reports.append(dict(bank=bank,rect=box,cells=len(cs),area_um2=area,fill=fill,rectangles=rects))
    return dict(schema='opentallas.quarter_actual_rf_rows.v1',positions=positions,banks=reports,qualification='Actual bare-mapped RF cells only; all combinational and sequential footprints allocated; no PG/hold/reset/G1 claim.')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cells',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    r=allocate(json.loads(a.cells.read_text()));a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'rf_sites.json').write_text(json.dumps(r,indent=1)+'\n');(a.out/'preplaced.json').write_text(json.dumps(r['positions'])+'\n')
    (a.out/'obstacles.json').write_text(json.dumps([dict(name='actual_rf_'+str(b['bank']),rect=b['rect'])for b in r['banks']])+'\n')
    print(json.dumps({k:v for k,v in r.items()if k not in ('positions','banks')}));print([(b['bank'],b['cells'],b['area_um2'],b['fill'])for b in r['banks']])
if __name__=='__main__':main()
