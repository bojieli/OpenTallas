"""All-gap diagnostics retain default fail-fast and never emit an incomplete top."""
import pytest
import bind
from test_bind_wavefront import emitter, plan


def broken_plan():
    raw = plan()
    raw['partition_types']['src']['hard_cores'] = [dict(
        inst=name, module='absent_core', origin_um=[50+100*i,50],
        outline_um=[80,100], pins=[dict(name='rst_n',layer='M4',xy=[0,50])])
        for i,name in enumerate(('u_missing_a','u_missing_b'))]
    return raw


def test_all_gaps_collects_both_missing_core_resets_without_top(tmp_path):
    b = emitter(broken_plan())
    b.collect_gaps = True
    files = b.emit(tmp_path)
    assert len(b.emit_gaps) == 2
    assert 'u_missing_a.rst_n' in b.emit_gaps[0]
    assert 'u_missing_b.rst_n' in b.emit_gaps[1]
    assert all('expected one bound leaf, found 0' in g for g in b.emit_gaps)
    assert not (tmp_path/'rtl/tiny_bound_top.sv').exists()
    assert all('bound_top' not in str(f) for f in files)


def test_default_still_fails_first_missing_reset(tmp_path):
    b = emitter(broken_plan())
    with pytest.raises(bind.BindError, match='u_missing_a.rst_n'):
        b.emit(tmp_path)
    assert not getattr(b,'emit_gaps',[])


def test_all_gaps_clean_fixture_matches_default_bytes(tmp_path):
    regular = emitter(plan()).emit(tmp_path/'regular')
    b = emitter(plan())
    b.collect_gaps = True
    collected = b.emit(tmp_path/'collected')
    assert not getattr(b,'emit_gaps',[])
    assert [(p.name,p.read_bytes()) for p in regular] == [(p.name,p.read_bytes()) for p in collected]


def test_invalid_parent_id_skips_leaf_and_reports_without_keyerror(tmp_path):
    from types import SimpleNamespace
    raw = plan()
    raw['partition_types']['src']['contents'] = [dict(inst='u_bad', module='leaf',
        parent_id_straps={'lane_lane_id':dict(width=2,value=1)})]
    b = emitter(raw)
    part = next(p for p in b.parts if b.parts[p]['type']=='src')
    b.F.cells = [SimpleNamespace(path='p.u_bad',ports={'lane_lane_id':[1,2]},module='leaf',params={})]
    b.G.dirs = {0:{'lane_lane_id':'input'}}
    b.G.kind = ['leaf']
    b.members[part] = [0]
    b.rel_of = lambda ci:'u_bad'
    b.tparams['src'] = {('strap','u_bad','lane_lane_id',i):['0'] for i in range(2)}
    b.sinks = {(0,'lane_lane_id',i):('strap',) for i in range(2)}
    b.collect_gaps = True
    files=b.emit(tmp_path)
    assert any('parent ID src.u_bad.lane_lane_id' in g for g in b.emit_gaps)
    assert not (tmp_path/'rtl/tiny_bound_top.sv').exists()
    assert 'leaf u_u_bad' not in (tmp_path/'rtl'/(raw['partition_types']['src']['module']+'.sv')).read_text()
