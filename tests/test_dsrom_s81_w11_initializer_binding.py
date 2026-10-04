import importlib.util
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('init_binding', ROOT / 'tools/dsrom_s81_w11_initializer_binding.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_finite_init_and_field_service():
    d = m.build()
    assert d['field_service']['local_slow_edges'] == 19
    assert d['field_service']['bank_service_II_slow_edges'] == 35
    assert d['initializer_service']['local_slow_edges'] == 11
    assert d['initializer_service']['bank_service_II_slow_edges'] == 27
    assert d['initializer_service']['active_capacity_per_bank'] == 1
    assert d['startup']['one_group_eight_rows_ns_bound'] == pytest.approx(144.44444444444446)


def test_operation_namespace_has_cost_and_no_free_credits():
    d = m.build()
    assert d['interface']['receipt_raw_bits'] == 105
    assert d['interface']['receipt_coded_bits'] == 144
    assert d['cost']['added_logic50_mm2'] > 0
    assert d['startup']['received_mask_unchanged_by_initialization']
    assert d['startup']['existing_live_row_must_not_be_zeroed']
    assert d['limits']['physical_fit'] is None
