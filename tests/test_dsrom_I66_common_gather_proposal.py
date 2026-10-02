import copy
import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('common', Path(__file__).resolve().parents[1] / 'tools/dsrom_I66_common_gather_proposal.py')
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def test_all576_source_owners_and_boundaries():
    rows = [M.route(r) for r in range(576)]
    assert M.validate_itinerary(rows) == [320, 256]
    assert [rows[r]['physical_shard'] for r in (127, 128, 255, 256, 383, 384, 511, 512, 575)] == [0, 1, 1, 0, 0, 1, 1, 0, 0]


@pytest.mark.parametrize('mutation', ['alias_shard', 'wrong_root', 'reorder', 'missing', 'bool'])
def test_bad_owned_itinerary(mutation):
    rows = [M.route(r) for r in range(576)]
    if mutation == 'alias_shard': rows[128]['physical_shard'] = 0
    if mutation == 'wrong_root': rows[512]['root'] = 64
    if mutation == 'reorder': rows[0], rows[1] = rows[1], rows[0]
    if mutation == 'missing': rows.pop()
    if mutation == 'bool': rows[0]['physical_shard'] = False
    with pytest.raises(ValueError): M.validate_itinerary(rows)


@pytest.mark.parametrize('value', [-1, 65536, 2**32-1, True, 1.0])
def test_header_truncation_rejected(value):
    with pytest.raises(ValueError): M.source_wire_user(value, domain_qualified=True)


def test_unqualified_domain_not_admitted_even_if_value_fits():
    with pytest.raises(ValueError): M.source_wire_user(17)
    assert M.source_wire_user(65535, domain_qualified=True) == 65535


def test_no_calendar_or_current_journal_invented():
    p = M.proposal()
    assert p['capacity_and_register_gate']['C'] is None
    assert p['capacity_and_register_gate']['calendar'] is None
    assert p['accepted_consumer_endpoints']['actual_current_journal'] is None
    assert p['state_accounting']['union'] == p['state_accounting']['core_gross'] + p['state_accounting']['disjoint_transport']
    assert p['wire_identity_gap']['fff6_packet_header_user_bits'] == 16
    assert not p['RTL_GO'] and not p['new_jobs']
