"""Bounded all-stage Qwen source and ISA binding checks."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_isa as I  # noqa: E402
import hdc_qwen_fullshape_isa as QI  # noqa: E402
import hdc_qwen_fullshape_program as FP  # noqa: E402
import qwen_o4_fulltoken_binding as B  # noqa: E402


SNAPSHOT = Path('/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/'
                'snapshots/b968826d9c46dd6066d109eabc6255188de91218')


def test_compact_bank_geometry_and_head_offsets():
    rows = B.compact_rows()
    assert [(r['name'], r['base'], r['scale_base']) for r in rows] == [
        ('qkv', 0, 0), ('o', 128, 192), ('gu', 216, 456), ('down', 728, 1224)]
    head = B.matrix(0, 'lm_head', 75968, 4096)
    head['scale_base'] = 0
    profiles = [FP.profile_lm_head(die, head, 0) for die in (0, 1)]
    assert [QI.decode_descriptor(int(p['descriptor_hex'][0], 16))['row0']
            for p in profiles] == [0, 75968]
    for profile in profiles:
        assert [chunk['code_base'] for chunk in profile['chunks']] == list(range(0, 3584, 512))
        assert [chunk['scale_base'] for chunk in profile['chunks']] == list(range(0, 5376, 768))
        chunks = [QI.decode_instruction(int(word, 16)) for word in profile['program_hex']
                  if QI.decode_instruction(int(word, 16))['unit'] == I.UNIT_ME]
        assert [(x['me_row0'], x['me_amc']) for x in chunks] == [
            (0, 0), (12288, 1), (24576, 1), (36864, 1),
            (49152, 1), (61440, 1), (73728, 1)]


@pytest.mark.skipif(not SNAPSHOT.is_dir(), reason='pinned checkpoint unavailable')
def test_all_stage_source_and_program_binding(tmp_path):
    manifest = B.binding(SNAPSHOT, tmp_path)
    assert manifest['stage_count'] == 38
    assert manifest['source_tensor_shapes_checked'] == 399
    assert manifest['status'] == 'source_and_program_preflight'
    assert manifest['vm_elems'] == 177808
    assert manifest['kv_window_elems'] == 8388608
    assert manifest['requirements']['me_row0_high_bits'] == [899, 898]
    assert manifest['requirements']['independent_scale_base'] == 'INT8_SCALE_WCS_BASE=1'
    assert manifest['stages'][0]['code_word_count'] == 151936 * 64
    assert all(stage['code_words_per_die'] == 992 for stage in manifest['stages'][1:37])
    assert manifest['stages'][-1]['code_words_per_die'] == 3168
    assert manifest['stages'][-1]['chunks_per_die'] == 7
    assert len((tmp_path / 'layer_program.hex').read_text().splitlines()) == 33
    assert len((tmp_path / 'head_program_d1.hex').read_text().splitlines()) == 11
    assert len((tmp_path / 'head_final_norm_crom.hex').read_text().splitlines()) == 4096
    on_disk = json.loads((tmp_path / 'fulltoken_binding.json').read_text())
    assert on_disk['program_sha256'] == manifest['program_sha256']
