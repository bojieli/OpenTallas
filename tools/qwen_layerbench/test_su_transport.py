"""DV_SU_TRANSPORT (QC SU parent transport, QC-MEM9 11-08): default off, read age +extra, VM dependency + (gap - 3)."""
import pytest
import dv_lower as D
import dv_lower_vec as V


def test_default_off_keeps_profile_and_ages(monkeypatch):
    monkeypatch.delenv('DV_SU_TRANSPORT', raising=False)
    monkeypatch.setenv('DV_LOWER_VFLAGS', '')
    assert D.memory_profile() == dict(sram_if_mif=0, relative_memory_alignment=0)
    ages = dict(xs_out=[34], d2d={'gur': [57]}, red_vm=83, root_cfg_lead=4)
    assert D.apply_su_transport(ages) is ages
    assert D.su_dep_extra(ages) == 0


@pytest.mark.parametrize('spec', ['extra=9', 'extra=x,gap_l0=16,gap_l1=17', 'extra=9,gap_l0=2,gap_l1=17',
                                  'extra=-1,gap_l0=16,gap_l1=17', 'extra=9,gap_l0=16,gap_l1=17,bogus=1'])
def test_bad_spec_refused(monkeypatch, spec):
    monkeypatch.setenv('DV_SU_TRANSPORT', spec)
    with pytest.raises(D.LowerError, match='DV_SU_TRANSPORT'):
        D.su_transport()


def test_shift_only_su_ages(monkeypatch):
    monkeypatch.setenv('DV_SU_TRANSPORT', 'extra=9,gap_l0=16,gap_l1=17')
    a = D.apply_su_transport(dict(xs_out=[34, 42], silu_out=[114], red_vm=83, d2d={'gur': [26, 57]}, root_cfg_lead=4, ignored='x'))
    assert a['xs_out'] == [43, 51] and a['silu_out'] == [123] and a['red_vm'] == 92 and a['d2d'] == {'gur': [35, 66]}
    assert a['root_cfg_lead'] == 4 and a['ignored'] == 'x'
    assert a['su_parent_transport'] == dict(read_extra=9, vm_write_read_gap_l0=16, vm_write_read_gap_l1=17)
    assert D.su_dep_extra(a) == 14
    assert D.memory_profile()['su_parent_transport'] == a['su_parent_transport']


def test_check_memory_profile_ignores_transport_key(monkeypatch):
    monkeypatch.setenv('DV_LOWER_VFLAGS', '')
    monkeypatch.setenv('DV_SU_TRANSPORT', 'extra=9,gap_l0=16,gap_l1=17')
    D.check_memory_profile(dict(), 'ages.json')   # zero-transport untagged ages stay usable; the transport is additive


@pytest.mark.parametrize('spec,extra,dep', [('extra=9,gap_l0=16,gap_l1=17', 9, 14), ('extra=12,gap_l0=16,gap_l1=17', 12, 14)])
def test_silu_after_gur_dependency_grows(monkeypatch, spec, extra, dep):
    monkeypatch.delenv('DV_SU_TRANSPORT', raising=False)
    base = {c['label']: c['edge'] for c in V.lower_vec('silu')['commands']}
    monkeypatch.setenv('DV_SU_TRANSPORT', spec)
    out = {c['label']: c['edge'] for c in V.lower_vec('silu')['commands']}
    assert out['SILU s0'] - out['GU*r s0'] == base['SILU s0'] - base['GU*r s0'] + extra + dep


@pytest.mark.parametrize('spec,extra,tail', [('extra=9,gap_l0=17,gap_l1=17,ready=23', 9, 23), ('extra=9,gap_l0=17,gap_l1=17', 9, 14)])
def test_silu_after_gur_busy_tail(monkeypatch, spec, extra, tail):
    monkeypatch.delenv('DV_SU_TRANSPORT', raising=False)
    base = {c['label']: c['edge'] for c in V.lower_vec('silu')['commands']}
    monkeypatch.setenv('DV_SU_TRANSPORT', spec)
    out = {c['label']: c['edge'] for c in V.lower_vec('silu')['commands']}
    assert out['SILU s0'] - out['GU*r s0'] == base['SILU s0'] - base['GU*r s0'] + extra + tail
