import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import w16_w19_hardware_formats as F


def test_eight_scales_require_per_block_transport():
    assert F.uniform_scale_compatible([127] * 8)
    assert not F.uniform_scale_compatible(list(range(127, 135)))
    # E4M3 0x38 is exactly 1.0. All powers here are exactly representable in BF16.
    source = [2 ** (scale - 127) for scale in range(127, 135)]
    latched = [1] * 8
    assert source != latched and source == [1, 2, 4, 8, 16, 32, 64, 128]


@pytest.mark.parametrize('scales', [[127] * 7, [127] * 9, [-1] * 8, [256] * 8, [True] * 8])
def test_bad_scale_rows_refused(scales):
    with pytest.raises(F.B.Refusal):
        F.uniform_scale_compatible(scales)


def test_full_matrix_bound_is_not_reduced_window_credit():
    bound = F.fp32_bank_bound(24 * 20480)
    assert bound['source_fp32_bytes'] == 1966080
    assert bound['minimum_words_per_bank'] == 7680
    assert bound['minimum_bank_bytes'] == 245760
    assert bound['minimum_total_bank_bytes'] == 1966080
    assert bound['existing_default_window_bytes'] == 65536
    assert not bound['source_fits_default_window']


@pytest.mark.parametrize('elements', [0, -1, True])
def test_invalid_bank_bounds_refused(elements):
    with pytest.raises(F.B.Refusal):
        F.fp32_bank_bound(elements)


def test_no_source_dtype_or_software_replica_credit():
    for contract in (None, {}, {'format': 'F32', 'reference_ranks': 'all'},
                     dict(format='F32', read_port='fiction', resident_owner=0, deployed_bytes=0, region={} ),
                     dict(format='F32', read_port='fiction', resident_owner=0, deployed_bytes=32, region={} )):
        with pytest.raises(F.B.Refusal):
            F.require_deployment(contract)


def test_actual_port_and_scope_boundaries():
    result = F.build()
    assert result['Engram']['source_scale_granularity_columns'] == 32
    assert result['Engram']['existing_gather_scale_granularity_columns'] == 256
    assert result['HC']['ports']['rom_q']['packed_range'] == '[8*HW*32-1:0]'
    assert result['HC']['ports']['hr_data']['packed_range'] == '[8*256-1:0]'
    assert result['HC']['source_matrix_aggregate_bytes'] == 157286400
    assert result['KV']['existing_component_ports']['blk_scale']['packed_range'] == '[7:0]'
    assert len(result['deployment_refusals']) == 5
    assert not result['full_fit'] and not result['adopted']
    assert result['measured_service_cycles'] is None


def test_json_roundtrip_and_drift():
    result = json.loads(json.dumps(F.build()))
    F.check(result)
    result['pins'][F.GATHER] = '0' * 64
    with pytest.raises(F.B.Refusal, match='pin drift'):
        F.check(result)
