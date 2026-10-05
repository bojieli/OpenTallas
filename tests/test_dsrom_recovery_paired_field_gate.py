import hashlib
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'results/rtl/dsrom_recovery_20261004/paired_field_gate/model.json'


def test_all_regions_and_actual_retirement_not_historical_gain():
    d=json.loads(P.read_text())
    expected={'L20.attn.wo_a.st37':(871,705), 'L20.ffn.down.st37':(1274,831),
        'L20.ffn.down.st38':(521,394), 'L20.ffn.experts_gu.st37':(1483,988),
        'L20.ffn.experts_gu.st38':(741,576)}
    for group,(s,o) in expected.items():
        r=d['groups'][group]
        assert r['serial']['regions']==128
        assert r['overlap']['regions']==128
        assert r['serial']['accepted_to_source_idle_bound_edges']==s
        assert r['overlap']['accepted_to_source_idle_bound_edges']==o
        assert r['overlap']['downstream_accepted_lease'] is None
    assert d['matched_L20_AR_saved_us']==pytest.approx(.920,abs=.001)
    assert d['adoption'] is False
    assert d['physical']['verdict']=='REJECT_CURRENT_FIELD_SCREEN'


def test_shared_weight_route_and_quant_not_double_charged():
    d=json.loads(P.read_text())
    cover=d['swiglu_route_accounting']['covered_nodes']
    assert cover['L20.ffn.route_w']=='L20.ffn.swiglu'
    assert cover['L20.ffn.quant2']=='L20.ffn.swiglu'
    assert cover['L20.ffn.shared_quant']=='L20.ffn.shared_swiglu'
    assert d['combined_complete_SU'] is False
    assert d['combined_adoption'] is False
    assert d['cold_norm']['cold_cycles']==288
    assert d['repair_direction']['token_gain_credit']==0


def test_current_source_pins():
    d=json.loads(P.read_text())
    for path,expected in d['inputs'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
