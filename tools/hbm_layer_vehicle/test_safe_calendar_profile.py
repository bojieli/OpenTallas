"""Fleet-only decoded-profile checks against the original record23 fixture."""
import argparse
import importlib.util
from pathlib import Path
import sys



def main():
    ap=argparse.ArgumentParser();ap.add_argument('--compiler',type=Path,required=True)
    ap.add_argument('--fixture',type=Path,required=True);ap.add_argument('--original',type=Path,required=True)
    a=ap.parse_args()
    spec=importlib.util.spec_from_file_location('candidate_calendar',a.compiler)
    LI=importlib.util.module_from_spec(spec);spec.loader.exec_module(LI)
    import su_bench as SB
    from hbm_layer_vehicle.native_profile import NativeTiming
    records=LI.ds_dispatches_image(a.fixture/'images/ds_v41_1M_L00_per_die.json')
    fr=LI.load_fixture(a.fixture)[23];raw=SB.pack_rec(records[23][1])
    def run(value,safe=True):
     p=LI.Placement(0);p.nxt=[33]*8
     return LI.su_record(value,data=dict(fr['vm_in']),place=p,pad_zero=True,
                         timing=NativeTiming(18,15),safe_calendar=safe)
    r=run(raw);LI.fixture_check(r,fr)
    assert r['fixture']['checked_words']==128 and not r['fixture']['mismatched_words']
    assert r['lines']==[int(s,16) for s in a.original.read_text().split()]
    print('ORIGINAL_RECORD23_SAFE_BYTES_AND_128_GOLD PASS')
    spec=importlib.util.spec_from_file_location('old_calendar',a.compiler.with_name('layer_images_before_guard.py'))
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    candidate=run(raw,False)
    p=old.Placement(0);p.nxt=[33]*8
    baseline=old.su_record(raw,data=dict(fr['vm_in']),place=p,pad_zero=True,timing=NativeTiming(18,15))
    assert candidate['lines']==baseline['lines'] and candidate['expect']==baseline['expect']
    print('DEFAULT_BYTES_AND_CHECKS_IDENTICAL PASS')
    def refuse(label,value):
     try:run(value)
     except (ValueError,AssertionError) as e:print('REFUSED',label,str(e))
     else:raise AssertionError('UNPROVED_PROFILE_ADMITTED '+label)
    positions={n:(lo,w) for n,lo,w in SB.SUTL}
    for name,(lo,width) in positions.items():
     current=(raw>>(128+lo))&((1<<width)-1)
     value=(raw&~(((1<<width)-1)<<(128+lo)))|((0 if current else 1)<<(128+lo))
     refuse('control_'+name,value)
    oplo,opwidth=SB.C.UOP['opnd']
    for role in 'AO':refuse('absent_'+role,raw&~(1<<(oplo+'ABCDORI'.index(role))))
    for role in 'BCDRI':
     shift=384+256*'ABCDORI'.index(role)
     md=(raw>>384)&((1<<256)-1)
     refuse('extra_'+role,raw|(1<<(oplo+'ABCDORI'.index(role)))|(md<<shift))
    redlo,redwidth=positions['red'];dstlo,dstwidth=positions['dst']
    with_r=raw|(1<<(oplo+5))|(((raw>>384)&((1<<256)-1))<<(384+256*5))
    with_r|=1<<(128+redlo)
    refuse('single_group_R_reducer_with_O',with_r)
    without_o=with_r&~(1<<(oplo+4))&~(((1<<dstwidth)-1)<<(128+dstlo))
    refuse('single_group_Oless_R_reducer',without_o)
    for k in [6,11,33,50]:refuse('HGI_index_'+str(k)+'_'+records[k][0].tag,SB.pack_rec(records[k][1]))
    print('SAFE_CALENDAR_PROFILE_GUARDS PASS')


if __name__ == "__main__":
    main()
