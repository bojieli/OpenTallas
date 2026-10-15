#!/usr/bin/env python3
"""Native sequencer descriptor ABI: source producer and regeneration checks."""
from pathlib import Path
import sys
sys.path[:0] = [str(Path(__file__).resolve().parents[3] / 'tools'),
                str(Path(__file__).resolve().parents[3] / 'tools/redesign_qwen')]
import hdc_qwen_fullshape_isa_w12 as isa
import split_ctrl

for row in [0, 16, 255, 256, 4096, 0x123ff, 0xfffff]:
    count = 1 if row == 0xfffff else 256
    word = isa.encode_descriptor(1, row, count, 0xabc, 0x23456, vm_addr_ext=True)
    assert isa.decode_descriptor(word, vm_addr_ext=True) == dict(
        kind=1, vm_word=row, words=count, program_base=0xabc, row0=0x23456)
    if row < 256:
        assert isa.encode_descriptor(1, row, count, 0xabc, 0x23456) == word
for row, count in [(0xfffff, 2), (1 << 20, 1), (-1, 1), (256, 0)]:
    try:
        isa.encode_descriptor(1, row, count, 0, 0, vm_addr_ext=True)
    except ValueError:
        pass
    else:
        raise AssertionError((row, count))
for encoder in [lambda: isa.encode_descriptor(1, 256, 1, 0, 0)]:
    try:
        encoder()
    except ValueError:
        pass
    else:
        raise AssertionError('legacy encoder silently accepted a native row')
vrl = split_ctrl.tp_seq_vrl(cred=True)
assert 'parameter integer VM_ADDR_EXT = 0' in vrl
assert 'vw <= descriptor_vw;' in vrl and 'descriptor_end >' in vrl
body = split_ctrl.emit_seq_su_bi()
assert '[VWA-1:0] vm_raddr' in body and '.VWA(VWA), .VM_ADDR_EXT(VWA > 8)' in body
print('PASS encoder native20 roundtrip, legacy exact bytes, rejecting fences, regenerated source')
