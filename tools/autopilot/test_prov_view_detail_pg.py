"""detail_pg_layer: narrow PG-layer form of the routed detailed abstract (DIE-HBM-97 11-09, DRT-0073 bank128 class)."""
import importlib.util
import json
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    s = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


P = load('prov_detail_pg_test', HERE / 'prov_view.py')
A = load('abstract_detail_pg_test', ROOT / 'tools/die_plan/abstract_detail.py')


def pg_on(base, layer):
    """contract_lef puts PG on M5; move the PG pins (not OBS) to `layer`."""
    head, obs = base.split('  OBS\n', 1)
    return head.replace('LAYER M5 ;', 'LAYER %s ;' % layer) + '  OBS\n' + obs


def write(d, base, detail_obs, layers, bloat=1, pg=True, receipt_layers=None):
    (d / 'core.lef').write_text(base)
    new = ''.join(A.splice(base.splitlines(True), detail_obs, layers))
    (d / 'detail_view.lef').write_text(new)
    r = dict(base_sha256=P.sha256(d / 'core.lef'), out_sha256=P.sha256(d / 'detail_view.lef'),
             layers_detailed=receipt_layers or layers, check_ok=True, detail_pins_equal_base=True, bloat_factor=bloat)
    (d / 'detail_receipt.json').write_text(json.dumps(r))
    m = dict(detailed_lef='detail_view.lef', detailed_receipt='detail_receipt.json', detail_bloat_factor=bloat)
    if pg:
        m['detail_pg_layer'] = True
    return m


def bank_like():
    """PG pins on M6 = top OBS layer, like ot_hbm_hc_bank128_pair_core (OBS M1..M6, VDD/VSS on M6)."""
    return pg_on(P.contract_lef('core', 100, 50, [dict(name='a', x=.1, y=5., layer='M4')], {'a': 'INPUT'}, 6), 'M6')


M6_DETAIL = {'M6': ['      RECT 20 20 30 20.1 ;\n', '      RECT 40 0 41 50 ;\n']}


def test_bank_like_accepted_only_with_opt_in(tmp_path):
    m = write(tmp_path, bank_like(), M6_DETAIL, ['M6'])
    p, out = P.routed_detail(str(tmp_path), 'core', m, str(ROOT))
    assert p == str(tmp_path / 'detail_view.lef') and out['layers_detailed'] == ['M6'] and out['pg_layer_detail']
    ok, _ = A.check((tmp_path / 'core.lef').read_text().splitlines(True), Path(p).read_text().splitlines(True), ['M6'])
    assert ok


def test_bank_like_refused_without_opt_in(tmp_path):
    m = write(tmp_path, bank_like(), M6_DETAIL, ['M6'], pg=False)
    with pytest.raises(ValueError):
        P.routed_detail(str(tmp_path), 'core', m, str(ROOT))


def test_opt_in_false_or_string_is_not_opt_in(tmp_path):
    for v in (False, 'true', 1):
        m = write(tmp_path, bank_like(), M6_DETAIL, ['M6'], pg=False)
        m['detail_pg_layer'] = v
        with pytest.raises(ValueError):
            P.routed_detail(str(tmp_path), 'core', m, str(ROOT))


def test_bloat_zero_refused(tmp_path):
    m = write(tmp_path, bank_like(), M6_DETAIL, ['M6'], bloat=0)
    with pytest.raises(ValueError):
        P.routed_detail(str(tmp_path), 'core', m, str(ROOT))


def test_removal_refused(tmp_path):
    m = write(tmp_path, bank_like(), {}, ['M6'])
    with pytest.raises(ValueError):
        P.routed_detail(str(tmp_path), 'core', m, str(ROOT))


def test_core_with_layers_above_pg_keeps_normal_form(tmp_path):
    """PG on M5 with M6/M7 OBS: the normal form applies; opting in is refused, no M5 detail through this path."""
    base = P.contract_lef('core', 100, 50, [dict(name='a', x=.1, y=5., layer='M4')], {'a': 'INPUT'}, 7)
    m = write(tmp_path, base, {'M5': ['      RECT 1 1 2 2 ;\n']}, ['M5'])
    with pytest.raises(ValueError):
        P.routed_detail(str(tmp_path), 'core', m, str(ROOT))


@pytest.mark.parametrize('layers', [['M5'], ['M5', 'M6']])
def test_lower_or_extra_layer_refused(tmp_path, layers):
    det = {'M5': ['      RECT 1 1 2 2 ;\n'], 'M6': M6_DETAIL['M6']}
    m = write(tmp_path, bank_like(), det, layers)
    with pytest.raises(ValueError):
        P.routed_detail(str(tmp_path), 'core', m, str(ROOT))


def test_receipt_layers_must_match(tmp_path):
    m = write(tmp_path, bank_like(), M6_DETAIL, ['M6'], receipt_layers=['M6', 'M7'])
    with pytest.raises(ValueError):
        P.routed_detail(str(tmp_path), 'core', m, str(ROOT))


@pytest.mark.parametrize('change', ['pgpin', 'sigpin', 'lower'])
def test_protected_geometry_still_checked(tmp_path, change):
    m = write(tmp_path, bank_like(), M6_DETAIL, ['M6'])
    p = tmp_path / 'detail_view.lef'
    s = p.read_text()
    if change == 'pgpin':
        s = s.replace('RECT 10.9671 0.0000 11.2551 50.0000', 'RECT 10.9671 0.0000 11.2551 49.0000')
    elif change == 'sigpin':
        s = s.replace('PIN a\n', 'PIN bad_a\n')
    else:
        s = s.replace('LAYER M1 ;', 'LAYER M0 ;')
    p.write_text(s)
    r = json.loads((tmp_path / 'detail_receipt.json').read_text())
    r['out_sha256'] = P.sha256(p)
    (tmp_path / 'detail_receipt.json').write_text(json.dumps(r))
    with pytest.raises(ValueError):
        P.routed_detail(str(tmp_path), 'core', m, str(ROOT))
