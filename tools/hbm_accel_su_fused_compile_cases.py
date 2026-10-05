#!/usr/bin/env python3
"""Read existing SU case pickles without importing a lowering or numerical oracle."""
from __future__ import annotations

import ast
import hashlib
import io
import pickle
from pathlib import Path

import numpy as np


class CaseUnpickler(pickle.Unpickler):
    """The saved case format is plain containers and NumPy arrays, never engines."""

    def find_class(self, module, name):
        allowed = {
            ('numpy', 'ndarray'), ('numpy', 'dtype'),
            ('numpy.core.multiarray', '_reconstruct'), ('numpy.core.multiarray', 'scalar'),
            ('numpy._core.multiarray', '_reconstruct'), ('numpy._core.multiarray', 'scalar'),
            ('numpy.core.numeric', '_frombuffer'), ('numpy._core.numeric', '_frombuffer'),
        }
        if (module, name) not in allowed:
            raise ValueError(f'Not a saved plain SU case object: {module}.{name}')
        return super().find_class(module, name)


def load_cases(path: Path):
    data = path.read_bytes()
    blob = CaseUnpickler(io.BytesIO(data)).load()
    if not isinstance(blob, dict) or not isinstance(blob.get('cases'), list):
        raise ValueError('Expected saved SU cases pickle, not raw executor snapshots')
    for case in blob['cases']:
        if not isinstance(case, dict) or not all(
                key in case for key in ('name', 'meta', 'ops', 'init', 'cr_lo', 'cr_hi', 'checks')):
            raise ValueError('Incomplete saved SU case')
        if not isinstance(case['ops'], list) or any(
                not isinstance(op, dict) or any(not isinstance(key, str) or
                    not isinstance(value, (int, np.integer)) for key, value in op.items())
                for op in case['ops']):
            raise ValueError('Saved opcode fields must be literal integers, never coerced values')
    return blob, hashlib.sha256(data).hexdigest()


def field_widths(root: Path):
    """Read the literal bench-word schema; do not execute the campaign module."""
    path = root / 'tools/rtl_hdc_v41x_vec_campaign.py'
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == 'PFIELDS' for target in node.targets):
            return dict(ast.literal_eval(node.value))
    raise ValueError('No literal PFIELDS contract')


def _encode_instruction(op, widths):
    offsets = {}
    offset = 0
    for name, width in widths.items():
        offsets[name] = (offset, width)
        offset += width
    word = 0
    for name, value in op.items():
        if name.startswith('_'):
            continue
        if name not in offsets:
            raise ValueError(f'Unknown saved instruction field: {name}')
        start, width = offsets[name]
        if not isinstance(value, (int, np.integer)) or not 0 <= int(value) < (1 << width):
            raise ValueError(f'Invalid saved instruction field: {name}={value!r}')
        word |= int(value) << start
    return word


def encode_instruction(op, root: Path):
    """Pack literal fields using root's PFIELDS; preserve supplied waits unchanged.

    This is the integer-only equivalent of campaign.encode, with explicit integer
    validation. It does not schedule operations or infer dependencies/credit waits.
    Pass the selected executable's retained source root, not an unrelated checkout.
    """
    return _encode_instruction(op, field_widths(root))


def serialize_program(ops, root: Path):
    """Return prog.hex text equivalent to write_case, without importing its oracle.

    The caller owns ordering, wait fields, nprog and VM/CR images. An empty program
    has the bench's zero-word placeholder; its nprog must still be zero.
    """
    widths = field_widths(root)
    digits = (sum(widths.values()) + 3) // 4
    words = [_encode_instruction(op, widths) for op in ops] or [0]
    return ''.join(f'{word:0{digits}x}\n' for word in words)


def words_record(values):
    array = np.asarray(values)
    if array.dtype not in (np.dtype('float32'), np.dtype('uint32')) or array.ndim != 1:
        raise ValueError('Saved operands/checks must be one-dimensional binary32 words')
    raw = array.view(np.uint32).astype('<u4', copy=False).tobytes()
    return {'words': int(array.size), 'encoding': 'little-endian uint32 raw bits',
            'sha256': hashlib.sha256(raw).hexdigest()}


def input_records(case):
    return [{'address_words': int(address), **words_record(values)}
            for address, values in case['init']]


def check_records(case, pickle_sha256):
    return [{'original_check_index': index, 'label': str(label),
             'address_words': int(address), **words_record(values), 'kind': str(kind),
             'expected_source_sha256': pickle_sha256}
            for index, (label, address, values, kind) in enumerate(case['checks'])]
