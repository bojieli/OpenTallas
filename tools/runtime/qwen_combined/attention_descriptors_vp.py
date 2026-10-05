"""Opt-in near images from actual owner op-major VPOS decoder words.

Reuses the single-position structural decoder. No numerical operands, inference
or expected layer state. The owner POS_OFF field and all collective counts stay
unchanged; only attention removal and the drained near split are additive.
"""
import argparse
import json
import os
from pathlib import Path

from . import attention_descriptors as base
from tools import hdc_isa as I


def derive(words, descriptors, *, npos, enable=False):
    base.require(enable and type(npos) is int and 1 <= npos <= 4,
                 'opt-in actual owner VPMAX4 block required')
    bases = [(d >> 32) & 0xffff for d in descriptors]
    ops = [I.decode(word) for word in words]
    base.require(all(op['unit'] == I.UNIT_END or ((word >> 900) & 7) < npos
                     for word, op in zip(words, ops)), 'instruction outside actual position block')
    removed, projections, slots = set(), [], []
    for slot in range(npos):
        pcs = [pc for pc, (word, op) in enumerate(zip(words, ops))
               if op['unit'] == I.UNIT_END or ((word >> 900) & 7) == slot]
        source = [words[pc] for pc in pcs]
        desc = [(d & ~(0xffff << 32)) | (sum(pc < old for pc in pcs) << 32)
                for d, old in zip(descriptors, bases)]
        _, _, record = base.derive(source, desc, enable=True)
        removed.update(pcs[pc] for pc in record['source_removed_attention_pcs'])
        projections.append(pcs[record['source_suffix_pc']])
        slots.append(dict(qr_base=record['qr_base'], attn_base=record['attn_base']))
    first, last = min(removed), max(removed)
    base.require(removed == set(range(first, last + 1)) and len(removed) == 5 * npos,
                 'actual attention groups must be contiguous and op-major')
    base.require(projections == list(range(last + 1, last + 1 + npos)),
                 'actual per-position O projections must immediately follow attention')
    end = words[bases[1] - 1]
    result = words[:first] + [end] + words[last + 1:]
    suffix_base = first + 1
    for slot in range(npos):
        result[suffix_base + slot] = base.control_patch(result[suffix_base + slot])
    delta = 1 - len(removed)
    new_desc = [base.encode_near(slots[0]['qr_base'], slots[0]['attn_base'], 0)]
    for i, (d, old) in enumerate(zip(descriptors, bases)):
        new_base = suffix_base if i == 0 else old + delta
        base.require(0 <= new_base < 4096, 'rebased actual PAW12 program')
        new_desc.append((d & ~(0xffff << 32)) | (new_base << 32))
    return result, new_desc, slots


def emit(source, output, *, npos, enable=False):
    source, output = Path(source).resolve(strict=True), Path(output)
    pins = {name: base.sha(source / name) for name in ('program.hex', 'segments.hex')}
    words = [int(x, 16) for x in (source / 'program.hex').read_text().split()]
    desc = [int(x, 16) for x in (source / 'segments.hex').read_text().split()]
    words, desc, slots = derive(words, desc, npos=npos, enable=enable)
    payloads = ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex')
    base.require(all((source / name).is_file() for name in payloads), 'actual owner payloads required')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'program.hex').write_text(''.join(f'{w:0256x}\n' for w in words))
    (output / 'segments.hex').write_text(''.join(f'{d:016x}\n' for d in desc))
    # Each control word is {actual ATTN base[23:0], actual QR base[23:0]}.
    (output / 'near_slot_bases.hex').write_text(''.join(
        f'{((s["attn_base"] << 24) | s["qr_base"]):012x}\n' for s in slots))
    for name in payloads:
        os.symlink((source / name).resolve(), output / name)
    base.require(pins == {name: base.sha(source / name) for name in pins}, 'owner source changed')
    return slots


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--npos', type=int, required=True)
    p.add_argument('--enable', action='store_true')
    a = p.parse_args()
    print(json.dumps(emit(a.source, a.output, npos=a.npos, enable=a.enable)))
