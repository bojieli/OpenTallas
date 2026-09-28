"""Shipped TP2 address geometry, without allocating checkpoint-sized arrays."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_qwen_fullshape_placement as placement  # noqa: E402


def test_shipped_tp2_addresses_are_contiguous_and_scales_independent():
    report = placement.placement()
    rows = report['matrices_per_die']
    assert len(rows) == 36 * 4 + 1
    assert report['status'] == 'blocked'
    assert rows[0]['base'] == rows[0]['scale_base'] == 0
    for before, after in zip(rows, rows[1:]):
        assert before['end'] == after['base']
        assert before['scale_end'] == after['scale_base']
    assert rows[-1]['end'] == report['matrix_code_words_per_die']
    assert rows[-1]['scale_end'] == report['matrix_scale_words_per_die']
    # QKV's scale table is longer than its code ROM placement; sharing code
    # bases would collide with the following matrix's scales.
    assert rows[0]['scale_end'] > rows[1]['base']
    assert rows[0]['rows'] == 3072 and rows[0]['columns'] == 4096
    assert rows[-1]['rows'] == 75968
    assert report['embedding_scale_rows_per_die'] == 151936
    assert report['embedding_codes_per_word'] == 64
    assert report['embedding_code_words_per_die'] == 151936 * 4096 // 64
    assert any('me_nout' in x for x in report['blockers'])


def test_matrix_rounding_and_split_divisibility():
    row = placement.matrix(7, 'test', 129, 256, groups=4)
    assert row['split'] == 2
    assert row['rounds'] == 1
    assert row['end'] == 7 + row['rounds'] * row['k_per_split'] * placement.IL
    with pytest.raises(ValueError, match='invalid'):
        placement.matrix(0, 'bad', 10, 15)


def test_wrong_model_shape_rejected():
    import json
    config = json.loads(placement.CONFIG.read_text())
    config['num_hidden_layers'] = 35
    with pytest.raises(ValueError, match='not shipped'):
        placement.placement(config)
