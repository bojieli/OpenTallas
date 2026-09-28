"""Shipped first-layer ISA profile; no model weights or RTL output are implied."""
import sys
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import hdc_qwen_fullshape_program as F  # noqa: E402


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
