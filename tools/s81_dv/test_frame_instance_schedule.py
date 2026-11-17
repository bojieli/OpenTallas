"""Current physical variants select separate frame calendars without padding the plan."""
import hashlib
import json
import sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(HERE),str(HERE/'layer_prog')]
import frame_schedule_asb as F
import lower_xs as X

TOP='col_h9_l4_lp_asb_x'

def test_two_real_band_scopes_keep_their_distinct_depths(tmp_path,monkeypatch):
    parts=[dict(name=f'{f}{k}',type=f'col_h9_r{k}__variant') for f in ('a','b') for k in range(3)]
    ports=[dict(id=f,src=dict(part=f+'1'),dst=dict(part=f+'0')) for f in ('a','b')]
    plan=dict(partitions=parts,ports=ports,lanes=[dict(id='fi_'+f,ports=[f]) for f in ('a','b')],
              latency=dict(lanes={'fi_a':dict(cycles=9),'fi_b':dict(cycles=8)}))
    mapping={f'u_{f}.u_r{k}':f'{f}{k}' for f in ('a','b') for k in range(3)}
    (tmp_path/'map.json').write_text(json.dumps(dict(parts=mapping)))
    pp=tmp_path/'plan.json';pp.write_text(json.dumps(plan))
    monkeypatch.setattr(F,'SROOT',[tmp_path]);monkeypatch.setenv('OT_S81_FRAME_PLAN',str(pp))
    text=f'{TOP} u_a();\n{TOP} u_b();'
    with pytest.raises(ValueError,match='one schedule per master'):
        F.bound_seam_depths(plan,'col_h9')
    for frame,depth in [('u_a',9),('u_b',8)]:
        chosen=F.selected_frame_parts(plan,dict(map_file='map.json'),frame,TOP,text)
        assert F.bound_seam_depths(plan,'col_h9',set(chosen.values()))=={'u_s10':depth}
        assert F.plan_lanes('col_h9',set(chosen.values()))=={('r1','r0'):[depth]}
    with pytest.raises(ValueError,match='does not instantiate'):
        F.selected_frame_parts(plan,dict(map_file='map.json'),'u_missing',TOP,text)
    mapping['u_a.u_r0']='a1'
    (tmp_path/'map.json').write_text(json.dumps(dict(parts=mapping)))
    with pytest.raises(ValueError,match='wrong type'):
        F.selected_frame_parts(plan,dict(map_file='map.json'),'u_a',TOP,text)


def test_instance_and_plan_cannot_reuse_another_calendar(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir()
    (source/'leaf.sv').write_text('module pinned; endmodule\n')
    (source/'selected.json').write_text('{}')
    hashes={n:hashlib.sha256((source/n).read_bytes()).hexdigest() for n in ['leaf.sv','selected.json']}
    plan=tmp_path/'plan.json';plan.write_text('{"current":1}')
    psha=hashlib.sha256(plan.read_bytes()).hexdigest()
    schedules=tmp_path/'schedules'
    def emit(frame,selected=None):
        d=schedules/'frames'/frame;d.mkdir(parents=True,exist_ok=True)
        s=d/(TOP+'_schedule.json');s.write_text(json.dumps(dict(source_sha256=hashes,
            bound_plan=dict(frame_instance=selected or frame,plan_sha256=psha))))
        (d/(TOP+'_check.json')).write_text(json.dumps(dict(verdict='PASS',schedule_sha256=hashlib.sha256(s.read_bytes()).hexdigest())))
        return s
    a,b=emit('u_a'),emit('u_b')
    monkeypatch.setenv('OT_XS_ASB_SCHEDULE_DIR',str(schedules))
    monkeypatch.setenv('OT_S81_FRAME_SOURCE_ROOT',str(source))
    monkeypatch.setenv('OT_S81_FRAME_ASBUILT_MANIFEST','selected.json')
    monkeypatch.setenv('OT_S81_FRAME_PLAN',str(plan))
    assert X.source_frame_schedule(TOP,'u_a')==a
    assert X.source_frame_schedule(TOP,'u_b')==b
    emit('u_b',selected='u_a')
    with pytest.raises(ValueError,match='another actual instance'):
        X.source_frame_schedule(TOP,'u_b')
    emit('u_b')
    plan.write_text('{"current":2}')
    with pytest.raises(ValueError,match='another bound plan'):
        X.source_frame_schedule(TOP,'u_b')
    with pytest.raises(ValueError,match='invalid frame schedule'):
        X.source_frame_schedule(TOP,'../u_a')
