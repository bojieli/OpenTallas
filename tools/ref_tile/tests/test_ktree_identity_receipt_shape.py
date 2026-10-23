"""Canonical identity never replaces raw mapped provenance or typed counts."""
import copy
import json
from pathlib import Path
import pytest
import native_census as N
import pre_route_gate as P


def receipt():
    r = json.loads((Path(__file__).parent / 'fixtures/ktree_native_0330.json').read_text())
    r['netlist']['sha256'] = 'c' * 64
    r['netlist']['positive_buf_identity_sha256'] = N.KTREE_CANONICAL
    return r


def test_valid_canonical_receipt_keeps_raw_sha_and_warn():
    r = receipt()
    before = copy.deepcopy(r)
    assert N.ktree_scoped_admission(r)
    g = P.Gate()
    assert P.check_native_census(g, 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r))
    assert r == before
    assert g.items[0]['severity'] == 'WARN'


@pytest.mark.parametrize('sha', [None, '', 'c' * 63, 'z' * 64, 123, ['c' * 64]])
def test_canonical_digest_cannot_admit_missing_or_malformed_raw_identity(sha):
    r = receipt()
    r['netlist']['sha256'] = sha
    assert not N.ktree_scoped_admission(r)
    assert not P.check_native_census(P.Gate(), 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r))


@pytest.mark.parametrize('field,value', [('limit', 32.0), ('max_dynamic_loads', 34.0),
                                        ('role_errors', None), ('role_errors', '')])
def test_canonical_digest_does_not_replace_typed_report_fields(field, value):
    r = receipt()
    r[field] = value
    assert not N.ktree_scoped_admission(r)
    assert not P.check_native_census(P.Gate(), 'GATE_NATIVE_CENSUS_RESULT ' + json.dumps(r))


def test_scoped_node_loads_remain_integer_counts():
    r = receipt()
    r['violations'][0]['loads'] = 34.0
    assert not N.ktree_scoped_admission(r)
