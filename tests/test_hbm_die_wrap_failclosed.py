"""SYS-1 (tieoff audit 2026-10-08): tools/hbm_die_wrap.py fails closed on every unclassed tie / unnamed RTL port."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_die_wrap as W  # noqa: E402

VIEWS = ROOT / 'physical/hbm_accel_die_views'


def spec(rel):
    return json.loads((VIEWS / rel).read_text())


def test_classed_barrier_generates_unchanged():
    sv, st = W.gen(spec('barrier/rtl/spec.json'))
    assert sv == (VIEWS / 'barrier/rtl/hfd_barrier.sv').read_text()
    assert st['tied_off_bits'] == 0 and st['classed_tie_bits']['by_design'] == 4


def test_unclassed_tie_refused():
    s = spec('barrier/rtl/spec.json')
    del s['ties']['n0.up']
    with pytest.raises(W.TieError) as e:
        W.gen(s)
    assert any('n0.up' in x for x in e.value.errors)
    assert any(r['where'] == 'n0.up' and r['gap'] == 'TIED_OFF' for r in e.value.rows)


def test_unnamed_port_refused_even_if_classed():
    s = spec('barrier/rtl/spec.json')
    del s['instances'][0]['bind']['up']          # would silently become 'fold' before SYS-1
    with pytest.raises(W.TieError) as e:
        W.gen(s)
    assert any('n0.up' in x and 'not named in bind' in x for x in e.value.errors)


def test_bad_class_or_empty_reason_refused():
    for t in ({'class': 'functional', 'reason': 'x'}, {'class': 'debug', 'reason': ' '}):
        s = spec('barrier/rtl/spec.json')
        s['ties']['n0.up'] = t
        with pytest.raises(W.TieError):
            W.gen(s)


def test_spare_die_bits_refused():
    s = spec('barrier/rtl/spec.json')
    s['instances'][1]['bind']['rel'] = 'die:t_cmdproc[32:63]'   # leaves t_cmdproc[63] an undriven (const-0) die output
    s['instances'][1]['params'] = dict(s['instances'][1]['params'])
    with pytest.raises(W.TieError) as e:
        W.gen(s)
    assert any('die:t_cmdproc[63:64]' in x for x in e.value.errors) or any('n1.rel' in x for x in e.value.errors)


def test_spare_die_bits_classed_by_range():
    s = spec('barrier/rtl/spec.json')
    s['instances'][1]['bind']['arr'] = 'die:f_cmdproc[32:63]'   # die input bit 63 dropped
    with pytest.raises(W.TieError) as e:
        W.gen(s)
    assert any(x.startswith('die:f_cmdproc[63:64]') for x in e.value.errors)
    s['ties']['die:f_cmdproc[63:64]'] = {'class': 'test', 'reason': 'unit test'}
    with pytest.raises(W.TieError) as e:
        W.gen(s)
    assert any('n1.arr' in x and 'die_input_zero_padding' in x for x in e.value.errors)
    s['ties']['n1.arr'] = {'class': 'test', 'reason': 'unit test pads one core input bit'}
    sv, st = W.gen(s)
    assert st['tied_off_bits'] == 0


def test_ledger_never_fails_and_lists_cmdproc_ties():
    sv, st = W.gen(spec('cmdproc/rtl/spec_n.json'), strict=False)
    assert st['errors'] and st['tied_off_bits'] > 0
    classed = {r['where']: r['cls'] for r in st['ties'] if r['cls']}
    assert classed.get('cpN.st_kernels') == 'debug'

@pytest.fixture
def narrow_die(monkeypatch):
    """Both edges carry 32 bits while the core carries 64: no unused die pin exposes the loss."""
    record = {'ports': {
        'ck': {'bits': 1, 'direction': 'input', 'dir_segments': [[0, 1, 'in']]},
        'rst': {'bits': 1, 'direction': 'input', 'dir_segments': [[0, 1, 'in']]},
        'd': {'bits': 32, 'direction': 'input', 'dir_segments': [[0, 32, 'in']]},
        'q': {'bits': 32, 'direction': 'output', 'dir_segments': [[0, 32, 'out']]},
    }}
    monkeypatch.setattr(W.V, 'master_record', lambda _: record)
    monkeypatch.setattr(W, 'fclk_bits', lambda _: {})
    monkeypatch.setattr(W.L, 'parse_module', lambda *args: {'ports': {'d': ('input', 64), 'q': ('output', 64)}})
    return {'master': 'narrow', 'instances': [{'name': 'core', 'module': 'core', 'file': 'unused',
            'bind': {'d': 'die:d[0:32]', 'q': 'die:q[0:32]'}}]}


def test_partial_rtl_die_bind_refused_without_class(narrow_die):
    with pytest.raises(W.TieError) as exc:
        W.gen(narrow_die)
    rows = {r['where']: r for r in exc.value.rows}
    assert rows['core.d']['kind'] == 'die_input_zero_padding'
    assert rows['core.q']['kind'] == 'die_output_truncation'
    assert rows['core.d']['bits'] == rows['core.q']['bits'] == 32
    assert rows['core.d']['gap'] == rows['core.q']['gap'] == 'TIED_OFF'


def test_classed_partial_binds_account_for_lost_bits(narrow_die):
    narrow_die['ties'] = {key: {'class': 'by_design', 'reason': 'upper diagnostic bits omitted'}
                         for key in ('core.d', 'core.q')}
    _, stats = W.gen(narrow_die)
    assert stats['classed_tie_bits']['by_design'] == 64
    assert stats['tied_off_bits'] == 0


def test_ledger_exposes_partial_rtl_bind_without_failing(narrow_die):
    _, stats = W.gen(narrow_die, strict=False)
    assert stats['tied_off_bits'] == 64
    assert len(stats['errors']) == 2
