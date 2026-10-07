import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import hbm_accel_die_fp as H


def test_vm8_candidate_repairs_only_north_offsets_and_keeps_full_seams():
    old=H.build(dict(H.R24SM3,vm_split8=True),network_probe=True)
    new=H.build(H.R24SM3V,network_probe=True)
    assert H.legality(old)['overlaps']==4
    assert H.legality(new)['overlaps']==H.legality(new)['outside']==0
    by={i.name:i for i in old['insts']}
    moved=[]
    for i in new['insts']:
        before=by[i.name]
        assert (i.w,i.h,i.x,i.orient)==(before.w,before.h,before.x,before.orient)
        if abs(i.y-before.y)>1e-9:
            assert abs(i.y-before.y-.024)<1e-9
            moved.append(i.name)
    assert set(moved)=={f'hb_vm_{q}_n' for q in ('sw','se','nw','ne')}
    assert old['buses']==new['buses']
    seams=[b for b in new['buses'] if '_seam_' in b[0]]
    assert len(seams)==8 and all(b[2]>0 and len(b[3])==2 for b in seams)
