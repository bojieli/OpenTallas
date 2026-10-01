"""Shipped first-layer ISA profile; no model weights or RTL output are implied."""
import sys
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import hdc_qwen_fullshape_program as F  # noqa: E402
import hdc_qwen_fullshape_isa as QI  # noqa: E402
from hdc_qwen_fullshape_placement import matrix  # noqa: E402


def test_first_layer_program_round_trip_and_die_order():
    before = (P.VM, P.GR, P.S_STRIDE)
    a, b = F.profile(0), F.profile(1)
    assert (P.VM, P.GR, P.S_STRIDE) == before
    assert a['program_hex'] == b['program_hex']
    assert a['program_words'] == len(a['program_hex']) == 31
    assert a['segment_count'] == 5
    assert a['allreduce_segments'] == 4
    assert a['descriptor_hex'] == b['descriptor_hex']
    assert all(len(word) == 16 for word in a['descriptor_hex'])
    assert a['vm_elems'] <= 1 << I.A
    assert a['kv_window_elems'] <= 1 << I.A
    assert a['required_token_bits'] == 18
    assert a['source_sha256']['tools/hdc_qwen_fullshape_program.py'] == hashlib.sha256(
        (ROOT / 'tools/hdc_qwen_fullshape_program.py').read_bytes()).hexdigest()
    assert a['context_capacity'] == 8192
    decoded = [I.decode(int(word, 16)) for word in a['program_hex']]
    assert decoded[0]['unit'] == I.UNIT_SU
    assert decoded[-1]['unit'] == I.UNIT_END
    assert max(f['me_wbase'] for f in decoded) < 1 << I.A
    assert all(f['me_nout'] < 1 << I.N for f in decoded)


def test_vm_regions_do_not_overlap_and_first_layer_kv_window():
    vm, total = F.vm_map()
    assert total > I.VM_ELEMS
    assert vm['S'] + 16 * 8192 <= vm['ATT']
    assert vm['GU'] + 12288 <= vm['ATTN']
    report = F.profile(0)
    assert report['kv_window_elems'] == 2 * 4 * 8192 * 128
    assert any('DYN_TTILES' in item for item in report['blockers'])


def test_lm_head_512_word_chunks_keep_independent_scale_stride():
    meta = matrix(0, 'lm_head', 75968, 4096)
    meta['scale_base'] = 0
    a, b = F.profile_lm_head(0, meta, 535041), F.profile_lm_head(1, meta, 535041)
    assert a['program_words'] == b['program_words'] == 11
    assert QI.decode_descriptor(int(b['descriptor_hex'][0], 16))['row0'] == 75968
    assert QI.decode_descriptor(int(a['descriptor_hex'][0], 16))['row0'] == 0
    assert [x['code_base'] for x in b['chunks']] == [0, 512, 1024, 1536, 2048, 2560, 3072]
    assert [x['scale_base'] for x in b['chunks']] == [0, 768, 1536, 2304, 3072, 3840, 4608]
    assert b['chunks'][-1]['first_row'] == 73728 and b['chunks'][-1]['rows'] == 2240
    decoded = [QI.decode_instruction(int(word, 16)) for word in b['program_hex']]
    chunks = [f for f in decoded if f['unit'] == I.UNIT_ME]
    assert len(chunks) == 7 and chunks[-1]['me_row0'] == 73728
    assert [f['me_amc'] for f in chunks] == [0] + [1] * 6


def test_one_segment_all_reduce_is_opt_in(monkeypatch):
    """QWEN_O4_AR_WORDS=256: each 4,096-element all-reduce is ONE 256-word segment (count 0 encodes 256)."""
    monkeypatch.setattr(F, 'AR_WORDS', 256)
    a = F.profile(0)
    assert a['program_words'] == len(a['program_hex']) == 29
    assert a['segment_count'] == 3 and a['allreduce_segments'] == 2
    assert [QI.decode_descriptor(int(w, 16))['words'] for w in a['descriptor_hex']][:2] == [256, 256]
