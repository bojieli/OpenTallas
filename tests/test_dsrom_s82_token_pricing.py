import ast
import importlib.util
import json
from pathlib import Path
import pytest
import subprocess

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('s82', ROOT / 'tools/dsrom_s82_token_pricing.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def inputs():
    p = ROOT / s.BASE
    return [json.loads((ROOT / 'results/uarch/dsrom_return_storage_hbm_20261003/model.json').read_text())['baseline_at_model']] + [
        json.loads((p / f).read_text()) for f in ['inventory.json', 'return_baseline.json', 'physical_contract.json', 'indexer_multicast_model.json']]


def test_actual_inventory_hops_and_wire_are_composed_once():
    x = s.build()
    assert (x['stages'], x['total_dies'], x['return_RD']) == (82, 372, 64)
    assert x['return_FF50_mm2'] == pytest.approx(52.89758742528)
    h = x['stage_hops']
    assert (h['total'], h['inherited'], h['added_vs_S58']) == (81, 57, 24)
    assert h['total_endpoint_wire_us'] == pytest.approx(6.075)
    assert h['added_stage_hops_us_vs_S73'] == pytest.approx(4.338157894736842)
    assert h['added_stage_hops_us_vs_S58'] == pytest.approx(11.56842105263158)


def test_multicast_and_draft_pay_positive_serial_cost():
    x = s.build()
    assert len(x['scenarios']) == 8
    for r in x['scenarios']:
        assert r['indexer_multicast_AR_us'] == pytest.approx(29.48 if r['link_assumption'] == 'parallel_ports' else 85.37333333333333)
        assert r['conditional_draft_us'] == pytest.approx(.1173 * r['conditional_AR_us'])
        assert r['conditional_MTP_step_us'] == pytest.approx(r['conditional_verify_us'] + r['conditional_draft_us'])
        assert r['conditional_AR_us'] > r['baseline_AR_us'] + r['added_stage_hops_us']
        assert r['conditional_MTP_tokens_s'] < 7147
    assert x['headline_rate'] is None and not x['adopted'] and not x['physical_fit']
    assert x['full_token_AR_us'] is None and x['full_token_MTP_us'] is None


@pytest.mark.parametrize('kind', ['RD4', 'credit', 'PAR2', 'missingwire', 'missingCDC', 'missingdest', 'S73'])
def test_reject_missing_serial_terms_or_wrong_source(kind):
    args = inputs()
    if kind == 'RD4': args[2]['RD'] = 4
    if kind == 'credit': args[2]['latency_credit_cycles'] = -1
    if kind == 'PAR2': args[3]['UCIe_owner_crossings'] = 1
    if kind == 'missingwire': args[0]['hop_us'] -= .075
    if kind == 'missingCDC': args[4]['calls'][0]['lower_model_us'] -= 2 / 1200
    if kind == 'missingdest': args[4]['calls'][0]['shared_link_model_us'] = args[4]['calls'][0]['lower_model_us']
    if kind == 'S73': args[1]['stages'] = 73
    with pytest.raises(ValueError): s.compose(*args)


def test_byteexact_record():
    assert json.loads((ROOT / s.OUT).read_text()) == s.build()


def test_existing_model_calculation_bodies_byteinverse():
    original = subprocess.check_output(['git', 'show', '717a32dcf35c09ccff432068691a3da40b610863:tools/uarch_model.py'], cwd=ROOT, text=True)
    current = (ROOT / 'tools/uarch_model.py').read_text()
    old = {n.name: ast.dump(n) for n in ast.parse(original).body if isinstance(n, ast.FunctionDef)}
    new = {n.name: ast.dump(n) for n in ast.parse(current).body if isinstance(n, ast.FunctionDef)}
    assert set(new) - set(old) == {'dsrom_s82_rows'}
    assert all(new[name] == body for name, body in old.items() if name != 'main')
