"""Check actual routed DEF signal-pin origin congruences before macro composition."""
from __future__ import annotations
import argparse, hashlib, json, math, re
from pathlib import Path

PREFERRED_AXIS = dict(M4='y', M5='x', M6='y', M7='x', M8='y', M9='x')

def check(path):
    text=Path(path).read_text()
    dbu=int(re.search(r'UNITS DISTANCE MICRONS (\d+)',text)[1])
    if dbu!=1000: raise ValueError('gate requires nanometre DEF units')
    size=list(map(int,re.search(r'DIEAREA \( 0 0 \) \( (\d+) (\d+) \)',text).groups()))
    tracks={(ax.lower(),layer):(int(off),int(pitch)) for ax,off,pitch,layer in re.findall(r'TRACKS ([XY]) (\d+) DO \d+ STEP (\d+) LAYER (\w+)',text)}
    pins=[]
    section=text.split('PINS ',1)[1].split('END PINS',1)[0]
    for name,body in re.findall(r'\n\s*- (\S+)(.*?);',section,re.S):
        if 'USE SIGNAL' not in body: continue
        fixed=re.search(r'\+ FIXED \( (-?\d+) (-?\d+) \) N',body)
        if not fixed: raise ValueError(f'{name}: expected actual FIXED N pin')
        fx,fy=map(int,fixed.groups())
        for layer,a,b,c,d in re.findall(r'\+ LAYER (\S+) \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \)',body):
            if layer not in PREFERRED_AXIS: continue
            axis=PREFERRED_AXIS[layer]; v=(int(a)+int(c))/2+fx if axis=='x' else (int(b)+int(d))/2+fy
            if v!=round(v): raise ValueError(f'{name}: fractional-nm pin centre')
            pins.append((name,layer,axis,int(v)))
    orientations={}
    for orient,flips in dict(R0=(False,False),MY=(True,False),MX=(False,True),R180=(True,True)).items():
        result={}
        for axis in ('x','y'):
            constraints=set()
            for name,layer,ax,centre in pins:
                if ax!=axis: continue
                off,pitch=tracks[(axis,layer)]; extent=size[0 if axis=='x' else 1]
                res=(off-extent+centre if flips[0 if axis=='x' else 1] else off-centre)%pitch
                constraints.add((layer,int(res),pitch))
            period=math.lcm(*(v[2] for v in constraints)) if constraints else 1
            allowed=[x for x in range(period) if all(x%pitch==res for _,res,pitch in constraints)]
            result[axis]=dict(constraints=sorted(constraints),period_nm=period,allowed_origin_residues_nm=allowed,compatible=bool(allowed))
        orientations[orient]=dict(axes=result,compatible=all(v['compatible'] for v in result.values()))
    return dict(schema='opentallas.actual-def-pin-origin.v1',source_sha256=hashlib.sha256(text.encode()).hexdigest(),size_nm=size,signal_pin_shapes=len(pins),orientations=orientations)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('def_path',type=Path);ap.add_argument('--out',type=Path);args=ap.parse_args()
    rec=check(args.def_path)
    output=json.dumps(rec,indent=1)+'\n'
    if args.out: args.out.write_text(output)
    else: print(output,end='')
