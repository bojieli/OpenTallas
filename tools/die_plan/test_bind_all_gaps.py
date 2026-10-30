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
