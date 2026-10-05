"""Finite source scheduling and model arithmetic; no hardware qualification."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('price', ROOT/'tools/hbm_accel_su_fused_model.py')
price = importlib.util.module_from_spec(spec)
spec.loader.exec_module(price)


def rf_acceptances(write, held_until=0):
    # NBA recurrence of read_pending/rsp_valid/ack_valid in actual RF service.
    pending = response = ack = False
    accepted = []
    for edge in range(12):
        go = not (pending or response or ack)
        if go:
            accepted.append(edge)
        ready = edge >= held_until
        response_next = True if pending else (response and not ready)
        ack_next = True if go and write else (ack and not ready)
        pending, response, ack = go and not write, response_next, ack_next
    return accepted


def test_source_minimum_II_and_held_debt():
    assert rf_acceptances(False) == [0, 3, 6, 9]
    assert rf_acceptances(True) == [0, 2, 4, 6, 8, 10]
    assert rf_acceptances(False, held_until=6)[:2] == [0, 7]
    assert rf_acceptances(True, held_until=6)[:2] == [0, 7]


def test_serial_cost_includes_partial_RMW_and_publication():
    rows = price.finite_rf_provider_model()['rows']
    assert [r['conservative_serial_provider_edges'] for r in rows] == [112, 88]
    for row in rows:
        assert sum(row['staged_terms_edges'].values()) == row['conservative_serial_provider_edges']
        assert row['output_partial_vector_RMW_reads'] > 0
        assert row['working_set_RF_vectors'] <= 512
        assert row['full_program_composed_delta_us'] is None


def test_no_wide_port_or_clock_adoption():
    m = price.finite_rf_provider_model()
    assert m['transfer']['read_bytes_per_transaction'] == 1024
    assert m['transfer']['write_bytes_per_transaction'] == 512
    assert m['transfer']['capacity_outstanding_transactions'] == 1
    assert m['no_native_full_width_provider']
    assert not m['SS60_FF25_qualified'] and not m['RTL_build_admitted']
    assert m['external_CDC_us'] is None and m['headline_gain_percent'] is None
    assert m['macros_per_provider'] == 4*16*2


def test_added_storage_and_area_not_double_counted():
    for r in price.finite_rf_provider_model()['rows']:
        expected = sum(r[k] for k in ('input_snapshot_FF_bits',
            'full_output_reservation_FF_bits', 'separate_quant_reservation_FF_bits',
            'proposed_packing_cuts_FF_bits', 'control_FF_reservation_bits'))
        assert expected == r['total_added_FF_bits']
        assert r['adapter_50pct_reservation_mm2_ESTIMATE'] == 2*r['adapter_cell_floor_mm2_ESTIMATE']


def test_selected_sector_composition_does_not_inherit_FIFO_throughput():
    m = price.finite_provider_tradeoff_model()
    assert m['selected_transport']['initial_outstanding_limit'] == 1
    assert [r['serial_sector_payload_floor_us'] for r in m['rows']] == [4.327, .602, .305, .483, 5.76]
    assert m['HC_transport_floor_over_original_benchmark'] > 7.99
    assert m['headline_rate_gain_percent'] is None
    assert not m['physical_SS_FF_acceptance']
    assert all(r['successful_service_upper_bound_us'] is None for r in m['rows'])
