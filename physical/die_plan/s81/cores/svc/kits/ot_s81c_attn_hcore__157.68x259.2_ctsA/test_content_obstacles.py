"""Real native59 eight-bank shape must participate in station/tap geometry."""
import copy
import json
import sys
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import schema as S
import check
import gen_phys
import ft_sites


def native59():
    # Physical existing native59 writer bank layout from b5a340662e.
    contents=[]
    for i in range(8):
        contents.append(dict(inst=f'u_bound.u_core.u_qb.u_qseat.g_writer[{i}].u_mem',
            module='ot_sram_1r1w_32x512_m1',status='reuse',origin_um=[80. if i<4 else 530.,40.+110.*(i%4)],
            outline_um=[167.4,76.14],orient='R0' if i<4 else 'MY',lef='physical/native59_bank.lef'))
    return dict(outline_um=[777.6,518.4],contents=contents,ft_slots=[dict(name='ft0',width=1,stations=3,
                in_face='W',out_face='E')])


def plan(t):
    raw=json.loads((HERE/'examples/tiny_plan.json').read_text())
    raw['partition_types']['native59']=t
    return raw


def pins(_p, tn):
    return [('ft0_i',i,'M6',0.,80.+i*.1,'W') for i in range(2)]+[
            ('ft0_o',i,'M6',777.6,80.+i*.1,'E') for i in range(2)] if tn=='native59' else []


def test_native59_taps_avoid_physical_contents_without_hard_core():
    t=native59();boxes=S.placed_macro_boxes(t)
    assert len(boxes)==8 and boxes[t['contents'][0]['inst']]==(80.,40.,247.4,116.14)
    x,y=S.tap_clear(t,100.,80.)
    assert (x,y)!=(100.,80.)
    assert all(not (a-8.64<x<c+8.64 and b-8.64<y<d+8.64) for a,b,c,d in boxes.values())


def test_core_duplicate_uses_actual_track_offset_once():
    t=native59();c=copy.deepcopy(t['contents'][0]);c['origin_um']=[90.,50.];c['track_offset_um']=[.216,.012]
    t['hard_cores']=[c]
    boxes=S.placed_macro_boxes(t)
    assert len(boxes)==8
    assert boxes[c['inst']]==pytest.approx((90.216,50.012,257.616,126.152))


def test_physical_content_without_footprint_fails_closed():
    t=native59();del t['contents'][0]['outline_um']
    with pytest.raises(ValueError,match='outline_um required'):S.placed_macro_boxes(t)


def test_g0_rejects_whole_cell_edge_intersection_and_mutant(monkeypatch):
    t=native59();s=t['ft_slots'][0];s.update(stations=2,bit_site_cell_um=[1.404,.27],
        bit_sites_um=[[[79.,60.],[79.,60.27]]])
    monkeypatch.setattr(gen_phys,'type_pins',pins)
    p=S.Plan(plan(t));r=check.Report()
    assert check.check_ft_macro_sites(p,r)==2
    assert any('actual-bit station' in e['msg'] for e in r.errors())
    # Omitting physical contents recreates the bug: this crossing would pass.
    monkeypatch.setattr(S,'placed_macro_boxes',lambda *_a,**_k:{})
    mutant=check.Report();assert check.check_ft_macro_sites(p,mutant)==0 and not mutant.errors()


def test_siting_processes_contents_only_native59(monkeypatch):
    # Exercise the real bulk row allocator, not an implementation-mirroring stub.
    from tools.die_trial.legal_sites import RowAllocator
    t=native59();raw=plan(t)
    monkeypatch.setattr(ft_sites,'type_pins',pins)
    ledger,_=ft_sites.place(raw,RowAllocator,types=['native59'],max_radius_um=2.)
    assert len(ledger)==1 and ledger[0]['worst_paired_bit_um']<=405
    boxes=list(S.placed_macro_boxes(t,halo=8.64).values())
    for stage in t['ft_slots'][0]['bit_sites_um']:
        for x,y in stage:
            assert all(not(min(x+1.404,c)>max(x,a) and min(y+.27,d)>max(y,b)) for a,b,c,d in boxes)
    pts=[np.array([0.,80.])]+[np.mean(np.array(v)+[.702,.135],axis=0) for v in t['ft_slots'][0]['bit_sites_um']]+[np.array([777.6,80.])]
    assert all(bool(ft_sites._visible(a,b,boxes)) for a,b in zip(pts,pts[1:]))


def test_independent_envelope_audit_uses_physical_contents():
    import subprocess
    d=HERE.parents[1]/'results/proto_codex_1025/corrected'
    if not (d/'audit_one.py').is_file():
        # absent on disk: skip ONLY when HEAD tracks it (sparse checkout without results/); a deleted tool still fails
        r=subprocess.run(['git','-C',str(HERE),'ls-tree','--full-tree','--name-only','HEAD','--','results/proto_codex_1025/corrected/audit_one.py'],
                         capture_output=True,text=True)
        assert r.returncode==0 and r.stdout.strip(), 'audit_one.py is neither checked out nor tracked in HEAD'
        pytest.skip('sparse checkout: results/proto_codex_1025/corrected not checked out (tracked in HEAD)')
    sys.path.insert(0,str(d))
    import audit_one
    t=native59();t['ft_slots'][0].update(stations=2,bit_site_cell_um=[1.404,.27],
        bit_sites_um=[[[79.,60.],[79.,60.27]]])
    result=audit_one.footprints(S.Plan(plan(t)),'native59')
    assert result['cells']==2 and result['core_intersections']==2
