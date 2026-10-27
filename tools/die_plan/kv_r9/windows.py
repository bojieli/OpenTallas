"""Select nonempty SPICE windows covering corners, both-corner MC extremes and the band edge.
No nominal or MC window may silently pass with zero measured taps (R7 w_cSW defect).
"""
import argparse
import json
from pathlib import Path


def select(rec, samples, width=900.0):
    taps = {t['part']: t['tap'] for t in rec['taps']}
    xlo, xhi = min(rec['xs']), max(rec['xs'])
    ylo, yhi = min(rec['ys']), max(rec['ys'])
    anchors = {'SW': (xlo,ylo), 'SE': (xhi,ylo), 'NW': (xlo,yhi), 'NE': (xhi,yhi)}
    for corner, data in samples.items():
        s = max(data['samples'][1:] or data['samples'], key=lambda a: max(a['tap_arr_ps'].values())-min(a['tap_arr_ps'].values()))
        for side, fn in [('min',min),('max',max)]:
            k = fn(s['tap_arr_ps'], key=s['tap_arr_ps'].get)
            anchors[f'{corner}_worst_{side}'] = taps[k]
    # Both transition bands, from the largest un-driven gap and the last driven row.
    yy = sorted(set(n['site'][1] for n in rec['nodes'] if n.get('driver')))
    a,b = max(zip(yy, yy[1:]), key=lambda q:q[1]-q[0])
    anchors.update(hub_S=((xlo+xhi)/2,a), hub_N=((xlo+xhi)/2,b), sys_edge=((xlo+xhi)/2,yy[-1]))
    result=[]
    for label,xy in anchors.items():
        k = min(taps, key=lambda k:(taps[k][0]-xy[0])**2+(taps[k][1]-xy[1])**2)
        x,y=taps[k]
        box=[max(xlo,x-width/2), max(ylo,y-width/2), min(xhi,x+width/2), min(yhi,y+width/2)]
        inside=sorted(k for k,(tx,ty) in taps.items() if box[0]-1e-6<=tx<=box[2]+1e-6 and box[1]-1e-6<=ty<=box[3]+1e-6)
        if not inside: raise ValueError(f'{label}: no measured tap')
        result.append(dict(name=label,box=box,anchor=list(xy),selected_tap=k,taps=inside))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('rec');p.add_argument('TT');p.add_argument('FF');p.add_argument('out');p.add_argument('--width',type=float,default=900.)
    a=p.parse_args();r=select(json.load(open(a.rec)),{c:json.load(open(getattr(a,c))) for c in ('TT','FF')},a.width)
    Path(a.out).write_text(json.dumps(r,indent=1)+'\n')
    print('\n'.join(f"{w['name']}: {len(w['taps'])} taps {w['box']}" for w in r))
