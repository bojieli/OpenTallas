#!/usr/bin/env python3
"""Qwen fullshape 18-bit row offsets in unused legacy ISA/descriptor bits.

The 1024-bit instruction and 64-bit TP descriptor widths stay unchanged.
RTL must opt into decoding the high bits when NW=18; legacy words have zeros
there and retain their original meaning.
"""
import hdc_isa as I
import hdc_program as P

ROW_OFFSET, ROW_WIDTH = I.LAYOUT['me_row0']
ROW_HIGH_OFFSET = ROW_OFFSET + ROW_WIDTH
DESC_ROW_HIGH_OFFSET = 18
assert ROW_WIDTH == 16 and ROW_HIGH_OFFSET + 2 <= I.INSTR_BITS


def encode_instruction(fields):
    row0 = int(fields.get('me_row0', 0))
    if not 0 <= row0 < (1 << 18):
        raise ValueError('me_row0 needs 18 bits')
    legacy = {k: v for k, v in fields.items() if not k.startswith('_')}
    legacy['me_row0'] = row0 & 0xFFFF
    return I.encode(**legacy) | ((row0 >> 16) << ROW_HIGH_OFFSET)


def decode_instruction(word):
    fields = I.decode(word)
    fields['me_row0'] |= ((word >> ROW_HIGH_OFFSET) & 3) << 16
    return fields


def encode_descriptor(kind, vm_word, words, program_base, row0):
    if not (0 <= kind < 4 and 0 <= vm_word < 256 and 0 <= words < 256
            and 0 <= program_base < (1 << 16) and 0 <= row0 < (1 << 18)):
        raise ValueError('TP descriptor field exceeds fullshape layout')
    return (kind | (vm_word << 2) | (words << 10)
            | ((row0 >> 16) << DESC_ROW_HIGH_OFFSET)
            | (program_base << 32) | ((row0 & 0xFFFF) << 48))


def decode_descriptor(word):
    return {'kind': word & 3, 'vm_word': (word >> 2) & 255,
            'words': (word >> 10) & 255, 'program_base': (word >> 32) & 0xFFFF,
            'row0': ((word >> 48) & 0xFFFF) | (((word >> DESC_ROW_HIGH_OFFSET) & 3) << 16)}


def encode_segments(program):
    words, desc = [], []
    for instructions, (kind, vm_word, count, row0) in P.segments(program):
        desc.append(encode_descriptor(kind, vm_word, count, len(words), row0))
        words.extend(encode_instruction(f) for f in instructions)
    return words, desc
