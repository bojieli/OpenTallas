#!/usr/bin/env python3
"""Place channel-row mesh conductors below the adjacent face flop bank.

Two R19 floating-point tie decisions selected the upper symmetric PG lane.
This COPY delta chooses the lower legal lane for actual tree driver rows only;
no span, node, buffer or circuit edge changes.
"""
import argparse,json
from pathlib import Path

def lower_rows(straps,nodes):
    out=[list(s) for s in straps];changes=[]
    rows=sorted({float(n['xy'][1]) for n in nodes if not n['kids']})
    for y in rows:
        matches=[(i,s) for i,s in enumerate(out) if s[0]=='M8' and s[4]=='tile_row' and abs(s[1]-y)<=1.081]
        if len(matches)!=1:raise ValueError(f'driver row {y}: not exactly one mesh channel strap')
        i,s=matches[0]
        if s[1]>y:
            new=round(2*y-s[1],4)
            changes.append(dict(ideal_y=y,old_y=s[1],new_y=new))
            out[i][1]=new
    if len({tuple(s[:4]) for s in out})!=len(out):raise ValueError('row delta merges distinct conductors')
    return out,changes

def main():
    ap=argparse.ArgumentParser();ap.add_argument('straps',type=Path);ap.add_argument('nodes',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();out,changes=lower_rows(json.loads(a.straps.read_text()),json.loads(a.nodes.read_text()))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(out,indent=1)+'\n')
    a.out.with_suffix('.delta.json').write_text(json.dumps(dict(changes=changes,logic_stages_added=0),indent=1)+'\n')
    print(json.dumps(changes))
if __name__=='__main__':main()
