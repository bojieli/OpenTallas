import json
from pathlib import Path

import pytest
from tools.die_plan import bind_smoke as S


def fixture(tmp_path, parts, **kwargs):
    rtl = tmp_path / 'rtl'
    rtl.mkdir()
    top = rtl / 'qwen_compute_bound_top.sv'
    top.write_text('')
    w = dict(release='wavefront', max_release=40, root='root', parts=parts,
             unreachable=[], long_hops=[])
    w.update(kwargs)
    (tmp_path / 'bind_reset.json').write_text(json.dumps(w))
    return top


def part(parent, release, entry=1, depth=3, **extra):
    return dict(parent=parent, release=release, entry_stages=entry, depth_K=depth, **extra)


def instance(name, reset):
    return dict(name=name, conns=[('arst_n', reset)])


def test_boundary_ages_and_live_internal_reset(tmp_path):
    top = fixture(tmp_path, dict(a=part('omitted', 13), b=part('a', 17),
                                later=part('elsewhere', 40, core_release={'u_core.rst_n': 41})))
    c = S.qc_reset_contract(top, [instance('a', 'rstw_omitted'), instance('b', 'rstw_a')])
    assert c['boundary_prefixes'] == {'rstw_omitted': 9}
    assert c['calendar_start_delay'] == 42
    assert c['latest_published_core_pin_release'] == 41


def test_shared_boundary_must_have_same_physical_age(tmp_path):
    top = fixture(tmp_path, dict(a=part('omitted', 13), b=part('omitted', 14)))
    with pytest.raises(SystemExit, match='inconsistent reset boundary age'):
        S.qc_reset_contract(top, [instance('a', 'rstw_shared'), instance('b', 'rstw_shared')])


def test_missing_metadata_refuses_to_tie_reset_low(tmp_path):
    top = tmp_path / 'rtl' / 'top.sv'
    with pytest.raises(SystemExit, match='refuse idle-zero reset'):
        S.qc_reset_contract(top, [instance('a', 'rstw_external')])


def test_legacy_raw_reset_has_no_added_boot_cycles(tmp_path):
    c = S.qc_reset_contract(tmp_path / 'rtl' / 'top.sv', [instance('a', 'rst_n')])
    assert c == dict(release='legacy', calendar_start_delay=0, boundary_prefixes={})


def test_unreachable_wavefront_is_rejected(tmp_path):
    top = fixture(tmp_path, dict(a=part('omitted', 13)), unreachable=['a'])
    with pytest.raises(SystemExit, match='invalid wavefront reset metadata'):
        S.qc_reset_contract(top, [instance('a', 'rstw_omitted')])
