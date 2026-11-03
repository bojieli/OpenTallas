"""Repair only native FF sites crossed by the normal macro pin-grid snap."""
import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/die_trial'))
from legal_sites import RowAllocator


def hit(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8


def main():
    p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--original-rows',type=Path,required=True);p.add_argument('--original-ingress',type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();a.out.mkdir();d=a.candidate;m=json.loads((d/'model.json').read_text())
    rows={r['cell']:r for r in csv.DictReader((d/'actual_FF_rows.csv').open())}
    blocked=[[x-4.32,y-4.32,X+4.32,Y+4.32]for x,y,X,Y in [q['rect_um']for q in m['macros']]]
    W,H=m['outline_um'];allocator=RowAllocator([4.32,4.32,W-4.32,H-4.32],blocked,cell_size=(1.08,.27),column_pitch=2.16,row_pitch=.27)
    def reserve(x,y,cw):
        # Exact lattice reservations avoid float roundoff expanding an abutting
        # .27-row rectangle into its neighbouring (physically free) row.
        ix=round((x-cw/2)/2.16);iy=round((y-.135)/.27)
        assert abs(x-cw/2-ix*2.16)<1e-6 and abs(y-.135-iy*.27)<1e-6
        key=(iy-allocator.iy0)*allocator.nx+ix-allocator.ix0
        assert key not in allocator.used
        allocator.used.add(key)
    bad=[]
    for name,r in rows.items():
        x,y=float(r['x_um']),float(r['y_um']);box=[x-.54,y-.135,x+.54,y+.135]
        if any(hit(box,b)for b in blocked):bad.append(name)
        else:reserve(x,y,1.08)
    old={r['cell']:r for r in csv.DictReader(a.original_rows.open())}
    absent=json.loads(a.original_ingress.read_text())['reserved_row_FF_absent_from_post_SYNTH_ODB']['names']
    assert len(absent)==1088 and not(set(absent)&set(rows))
    for name in absent:
        r=old[name];x,y=float(r['x_um']),float(r['y_um']);reserve(x,y,1.404)
    (d/'FAIL_macro_snap_halo_rows.json').write_text(json.dumps(dict(status='FAIL_ACTUAL_MACRO_SNAP_HALO',violating_FF=len(bad),names=sorted(bad)),indent=2)+'\n')
    changes=[]
    for name in sorted(bad):
        r=rows[name];oldxy=[float(r['x_um']),float(r['y_um'])];points,_=allocator.allocate(oldxy,1,160.)
        newxy=list(map(float,points[0]));r['x_um'],r['y_um']=newxy
        changes.append(dict(cell=name,old_um=oldxy,new_um=newxy,move_um=sum(abs(x-y)for x,y in zip(oldxy,newxy))))
    m['actual_macro_snap_row_repair']=dict(status='NEAREST_FREE_NATIVE_ROWS_REQUIRES_CHANGED_GEOMETRY_AUDIT',
        repaired_FF=len(changes),max_move_um=max(q['move_um']for q in changes),changes=changes,
        conservative_extra1088_rows_reserved=True,added_FF=0,added_cycles=0)
    header=list(next(iter(rows.values())).keys())
    with(a.out/'actual_FF_rows.csv').open('w')as f:
        w=csv.DictWriter(f,header);w.writeheader();w.writerows(rows[k]for k in sorted(rows))
    (a.out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
    (d/'FAIL_macro_snap_halo_rows.json').write_text(json.dumps(dict(status='FAIL_ACTUAL_MACRO_SNAP_HALO',violating_FF=len(bad),names=sorted(bad)),indent=2)+'\n')
    for f in ('native_pins.json','native_pins_clock_entry.json','source_clock_sink_map.json'):
        shutil.copyfile(d/f,a.out/f)
    print('REPAIRED_EXISTING_NATIVE_FF',len(changes),'maxmove',m['actual_macro_snap_row_repair']['max_move_um'],'no state/cycle change',flush=True)


if __name__=='__main__':main()
