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


def test_ordered_seam_join_rejects_bit_permutation():
    import copy
    import pytest
    import hbm_sm_retile_vm8 as V
    masters={}
    for q in ('sw','se','nw','ne'):
        for half in ('s','n'):
            ports={};pins={}
            for index,bus in enumerate(('s2n','n2s')):
                ports[bus]=dict(bits=2,direction='output' if (half=='s')==(bus=='s2n') else 'input')
                for bit in range(2):
                    pins[f'{bus}[{bit}]']=['M5',100+index+bit*.048,499.944 if half=='s' else .096,.024,.192]
            masters[f'hfd_vm_{q}_{half}']=dict(height_um=500.04,ports=ports,pins=pins)
    contract=dict(masters=masters)
    rows=V.seam_pin_join(contract)
    assert len(rows)==8 and all(r['requested_pin_center_gap_um']==[.192,.192] for r in rows)
    bad=copy.deepcopy(contract)
    pins=bad['masters']['hfd_vm_sw_n']['pins']
    pins['s2n[0]'],pins['s2n[1]']=pins['s2n[1]'],pins['s2n[0]']
    with pytest.raises(ValueError,match='do not align'):
        V.seam_pin_join(bad)


def test_exact_vm8_requested_pins_preserve_scalar_face_and_seam_origin():
    import pytest
    from budgets.extract_die import anchor
    m=H.build(H.R24SM3V,network_probe=True);masters=H.masters(m);widths=H.port_widths(m,1)
    count=0
    for name in (f'hfd_vm_{q}_{h}' for q in ('sw','se','nw','ne') for h in ('s','n')):
        master=masters[name]
        rects=H.S.pin_rects(master,1,{p:widths.get((name,p),0) for p in master.order})
        count+=len(rects)
        assert all(spec[0]=='rects' for spec in master.ports.values())
        assert len({r[0] for r in rects})==len(rects)
        for _,_,(x0,y0,x1,y1) in rects:
            assert -1e-6<=x0<x1<=master.w+1e-6
            assert -1e-6<=y0<y1<=master.h+1e-6
        with pytest.raises(ValueError,match='full width'):
            H.S.pin_rects(master,2,{p:widths.get((name,p),0) for p in master.order})
    assert count==146558
    master=masters['hfd_vm_sw_s']
    assert anchor(master,'rst')==pytest.approx([386.412,.096])
    rects={p:r for p,_,r in H.S.pin_rects(master,1,{p:widths.get((master.name,p),0) for p in master.order})}
    x0,y0,x1,y1=rects['s2n[0]']
    assert (x0+x1)/2==pytest.approx(152.688)
    assert (y0+y1)/2==pytest.approx(499.944)
