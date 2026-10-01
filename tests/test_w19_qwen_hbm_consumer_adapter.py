import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import w19_qwen_hbm_consumer_adapter as A


@pytest.fixture
def exported(tmp_path):
    bundle = tmp_path / 'consumer'
    result = A.export(bundle, enabled=True)
    return bundle, result, A.load_expected(bundle)


def records(expected):
    # Synthetic checker self-test ONLY. Never an RTL runtime receipt.
    for (die, boundary), (_, words) in expected.items():
        for index, bits in enumerate(words):
            yield dict(die=die, boundary=boundary, index=index, bits=bits,
                       cycle=index, fault=0)


def test_export_default_disabled_and_real_full_head_bit_identity(exported, tmp_path):
    with pytest.raises(ValueError, match='disabled'):
        A.export(tmp_path / 'disabled')
    bundle, manifest, expected = exported
    assert manifest['strict_explicit_child_RC'] is False
    assert manifest['missing_explicit_child_RC_cases'] == 61
    assert len(expected) == 26
    assert not (bundle / 'inputs' / 'd0_post_norm_bits.hex').exists()
    assert (bundle / 'expected_only' / 'd0_post_norm_bits.hex').exists()
    result = A.check_records(expected, records(expected))
    assert result['runtime_admission'] is False and result['full_token'] is False
    assert result['elements'] == sum(len(words) for _, words in expected.values())


def test_heads_cross_actual_SM21_and_SM26_partitions():
    mapping = list(A.head_read_map())
    assert len(mapping) == 3072
    k0 = [r for r in mapping if r['projection'] == 'k' and r['head'] == 0]
    assert k0[0] == dict(die=0, projection='k', head=0, dimension=0, global_row=2048,
        global_head=0, projection_global_index=0, global_qkv_index=4096,
        sm=21, slice=2, bank=5, partition_base=2016, local_row=32)
    assert k0[64]['sm'] == 22 and k0[64]['local_row'] == 0
    v0 = [r for r in mapping if r['projection'] == 'v' and r['head'] == 0]
    assert v0[0]['sm'] == 26 and v0[0]['local_row'] == 64
    assert v0[32]['sm'] == 27 and v0[32]['local_row'] == 0
    both = list(A.head_read_map(0)) + list(A.head_read_map(1))
    assert sorted(r['global_qkv_index'] for r in both) == list(range(6144))
    assert list(A.head_read_map(1))[0]['global_head'] == 16
    with pytest.raises(ValueError):
        A.row_identity(3072)


@pytest.mark.parametrize('fault', A.FAULTS[1:])
def test_fault_controls_fail_closed(exported, fault):
    with pytest.raises(ValueError):
        A.check_records(exported[2], records(exported[2]), fault=fault)


@pytest.mark.parametrize('field,value', [('bits', 1 << 32), ('cycle', -1),
    ('fault', 1), ('index', 1), ('die', True)])
def test_observed_trace_width_order_identity_and_DUT_fault(exported, field, value):
    trace = records(exported[2])
    first = next(trace)
    first[field] = value
    def changed():
        yield first
        yield from trace
    with pytest.raises(ValueError):
        A.check_records(exported[2], changed())


def test_export_tamper_cannot_be_admitted_by_rehashing_manifest(exported):
    bundle, manifest, _ = exported
    artifact = manifest['artifacts'][0]
    path = bundle / artifact['path']
    words = path.read_text().splitlines()
    words[0] = f'{int(words[0],16)^1:08x}'
    path.write_text('\n'.join(words) + '\n')
    artifact['sha256'] = A.sha(path)
    (bundle / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='pinned NPZ'):
        A.load_expected(bundle)


def test_truncated_final_boundary_is_incomplete(exported):
    trace = list(records(exported[2]))
    with pytest.raises(ValueError, match='incomplete'):
        A.check_records(exported[2], trace[:-1])
