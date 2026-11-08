#!/usr/bin/env python3
"""Geometry-only compact companion; never edits a plan of record or launches CAD."""
import argparse,collections,copy,json,math,pathlib

def make(pins,w=181.44,h=267.84):
    out=copy.deepcopy(pins);oldw,oldh=427.68,453.6;params={'M3':(.009,.036),'M4':(.024,.048),'M5':(.024,.048),'M6':(.032,.064)}
    for face in ('E','W','N','S'):
        axis='y'if face in ('E','W')else'x';old=oldh if axis=='y'else oldw;new=h if axis=='y'else w
        rows=sorted((p for p in out if p.get('face')==face and p['bus']!='clk'),key=lambda p:p[axis]);last={}
        pattern=('M4','M6','M4','M6','M4','M6','M4')if axis=='y'else('M3','M5','M3','M5','M3','M5','M3')
        for i,p in enumerate(rows):
            layer='M4'if p['bus']in{'rst_n','rst_lg_n'}else pattern[i%7]
            offset,pitch=params[layer];f=(i+.5)/len(rows);target=4.32+f*(new-8.64)
            n=max(round((target-offset)/pitch),last.get(layer,-1)+1);value=round(offset+n*pitch,6);last[layer]=n
            p.update(layer=layer);p[axis]=value
            if face=='E':p['x']=w
            elif face=='W':p['x']=0.
            elif face=='N':p['y']=h
            else:p['y']=0.
    for p in out:
        if p['bus']=='clk':p.update(x=90.72,y=133.824,layer='M5')
    uses={};overflow=[];duplicates=[]
    for face in ('E','W','N','S'):
        axis='y'if face in ('E','W')else'x';dim=h if axis=='y'else w
        for layer,(_,pitch)in params.items():
            rows=[p for p in out if p.get('face')==face and p['bus']!='clk'and p['layer']==layer]
            bins=collections.Counter(int(p[axis]/20)for p in rows)
            uses[f'{face}/{layer}']=round(max(bins.values(),default=0)*pitch/20,6)
            if any(p[axis]>dim-.192 or p[axis]<.192 for p in rows):overflow.append(f'{face}/{layer}')
            dup=[v for v,c in collections.Counter(p[axis]for p in rows).items()if c>1]
            if dup:duplicates.append((face,layer,dup))
    report={'outline_um':[w,h],'core_fill_estimate':13079.4/((w-8.64)*(h-8.64)),
            'outline_fill_estimate':13079.4/(w*h),'pin_track20':uses,'overflow':overflow,'duplicates':duplicates,
            'clock_xy_um':[90.72,133.824],'clock_anchor_origin_delta_um':[216-90.72,224.64-133.824],
            'corner_euclidean_um':math.hypot(w,h),'corner_manhattan_um':w+h,'clock_entry_corner_euclidean_um':max(math.hypot(x-90.72,y-133.824)for x in(0,w)for y in(0,h)), 'actual_stage_reach':'REQUIRES_PLACEMENT_REVIEW',
            'PIN_CYCLES':0,'P&R':'NOT_RUN','STA':'NOT_RUN','parent_POR':'UNCHANGED'}
    report['geometry_verdict']='FEASIBLE'if not overflow and not duplicates and max(uses.values())<=.5 else'REVISE'
    return out,report

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('pins',type=pathlib.Path);a.add_argument('--out',type=pathlib.Path,required=True);x=a.parse_args();x.out.mkdir(parents=True,exist_ok=True)
    pins,report=make(json.loads(x.pins.read_text()));(x.out/'pins.json').write_text(json.dumps(pins,indent=1)+'\n');(x.out/'model.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))
