"""Place failed data capture cells using exact all-corner native hop constraints."""
import argparse
import csv
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_trial'))
from legal_sites import RowAllocator


def plain(n):return n.replace('\\[','[').replace('\\]',']')
SIGNS=[(1,1),(1,-1),(-1,1),(-1,-1)]
def support(rects):return [max(sx*x+sy*y for u,v,U,V in rects for x,y in [(u,v),(u,V),(U,v),(U,V)])for sx,sy in SIGNS]


def main():
    p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--macro-lef',type=Path,required=True);p.add_argument('--original-rows',type=Path,required=True)
    p.add_argument('--original-ingress',type=Path,required=True);a=p.parse_args();assert not a.out.exists();a.out.mkdir()
    d=a.candidate;m=json.loads((d/'model.json').read_text());rows={r['cell']:r for r in csv.DictReader((d/'actual_FF_rows.csv').open())}
    fail=json.loads((d/'adjacent_all_orientations/adjacent_model.json').read_text())
    bad={plain(q['launch_owner'])for q in fail['worst_bad_edges']if q['launch_kind']=='ff'and q['capture_kind']=='macro'}
    assert len(bad)==10 and all(re.fullmatch(r'g_leaf\[\d+\]\.u_leaf\.data_q\[\d+\]\$_DFF_P_',n)for n in bad)
    masters=json.loads(a.original_ingress.read_text())['FF_native_pin_masters'];macros={q['name']:q for q in m['macros']};lp={}
    for z in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',a.macro_lef.read_text(),re.S):
        rects=[list(map(float,v))for v in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;',z[2])]
        if rects:lp[z[1]]=rects
    offsets={}
    def offset(name,pin):
        key=rows[name]['master'],plain(pin)
        if key not in offsets:
            mm=masters[key[0]];ww,hh=mm['w'],mm['h'];rs=mm['pins'][key[1]]
            offsets[key]=support([[u-ww/2,v-hh/2,U-ww/2,V-hh/2]for u,v,U,V in rs]+[[u-ww/2,hh/2-V,U-ww/2,hh/2-v]for u,v,U,V in rs])
        return offsets[key]
    def actual(kind,name,pin):
        name,pin=plain(name),plain(pin)
        if kind=='ff':
            x,y=float(rows[name]['x_um']),float(rows[name]['y_um']);ss=offset(name,pin)
            return [ss[i]+sx*x+sy*y for i,(sx,sy)in enumerate(SIGNS)]
        x,y,_,_=macros[name]['rect_um'];return support([[x+u,y+v,x+U,y+V]for u,v,U,V in lp[pin]])
    incident=defaultdict(list)
    for e in csv.DictReader((d/'adjacent_all_orientations/adjacent_sequential_edges.csv').open()):
        s,t=plain(e['launch_owner']),plain(e['capture_owner'])
        if s==t:continue
        if s in bad:incident[s].append((e['launch_pin'],e['capture_kind'],t,e['capture_pin']))
        if t in bad:incident[t].append((e['capture_pin'],e['launch_kind'],s,e['launch_pin']))
    W,H=m['outline_um'];blocked=[[x-4.32,y-4.32,X+4.32,Y+4.32]for x,y,X,Y in [q['rect_um']for q in macros.values()]]
    allocator=RowAllocator([4.32,4.32,W-4.32,H-4.32],blocked,cell_size=(1.08,.27),column_pitch=2.16,row_pitch=.27)
    def reserve(x,y,cw):
        ix=round((x-cw/2)/2.16);iy=round((y-.135)/.27);key=(iy-allocator.iy0)*allocator.nx+ix-allocator.ix0
        assert key not in allocator.used;allocator.used.add(key)
    for n,r in rows.items():
        if n not in bad:reserve(float(r['x_um']),float(r['y_um']),1.08)
    old={r['cell']:r for r in csv.DictReader(a.original_rows.open())};absent=json.loads(a.original_ingress.read_text())['reserved_row_FF_absent_from_post_SYNTH_ODB']['names']
    for n in absent:reserve(float(old[n]['x_um']),float(old[n]['y_um']),1.404)
    changes=[]
    for n in sorted(bad):
        assert not rows[n]['planned_output_pin_x_um']
        hi=[float('inf')]*4
        for ownpin,kind,target,pin in incident[n]:
            own=offset(n,ownpin);goal=actual(kind,target,pin)
            for i in range(4):hi[i]=min(hi[i],404.-own[i]-goal[3-i])
        loU,hiU,loV,hiV=-hi[3],hi[0],-hi[2],hi[1]
        assert loU<=hiU and loV<=hiV,(n,hi)
        ix,iy=np.meshgrid(np.arange(allocator.ix0,allocator.ix1+1),np.arange(allocator.iy0,allocator.iy1+1));ix=ix.ravel();iy=iy.ravel()
        xs,ys=ix*2.16+.54,iy*.27+.135;ids=(iy-allocator.iy0)*allocator.nx+ix-allocator.ix0
        ok=(xs+ys<=hiU+1e-8)&(xs+ys>=loU-1e-8)&(xs-ys<=hiV+1e-8)&(xs-ys>=loV-1e-8)
        for u,v,U,V in blocked:ok&=~((xs-.54<U-1e-8)&(xs+.54>u+1e-8)&(ys-.135<V-1e-8)&(ys+.135>v+1e-8))
        valid=np.flatnonzero(ok);valid=valid[np.fromiter((int(ids[k])not in allocator.used for k in valid),bool,count=len(valid))]
        assert len(valid),(n,'No legal native row under exact404um all-corner constraints')
        x,y=float(rows[n]['x_um']),float(rows[n]['y_um']);cost=np.abs(xs[valid]-x)+np.abs(ys[valid]-y);k=valid[np.lexsort((ids[valid],cost))[0]]
        point=[float(xs[k]),float(ys[k])];reserve(*point,1.08);rows[n]['x_um'],rows[n]['y_um']=point
        changes.append(dict(cell=n,from_um=[x,y],to_um=point,move_um=abs(x-point[0])+abs(y-point[1]),incident_constraints=len(incident[n]),all_corner_limit_um=404,uv_bounds_um=[loU,hiU,loV,hiV]))
    m['native_data_capture_constraint_repair']=dict(status='EXACT_NATIVE_ALL_CORNER_ROW_CANDIDATE',changes=changes,added_FF=0,added_cycles=0)
    with(a.out/'actual_FF_rows.csv').open('w')as f:
        writer=csv.DictWriter(f,list(next(iter(rows.values())).keys()));writer.writeheader();writer.writerows(rows[n]for n in sorted(rows))
    (a.out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
    for f in ('native_pins.json','native_pins_clock_entry.json','source_clock_sink_map.json'):shutil.copyfile(d/f,a.out/f)
    print('REPAIRED_EXACT_NATIVE_DATA_CAPTURE_CONSTRAINTS',len(changes),'maxmove',max(q['move_um']for q in changes),flush=True)


if __name__=='__main__':main()
