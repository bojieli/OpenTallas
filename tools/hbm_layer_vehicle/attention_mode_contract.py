#!/usr/bin/env python3
"""Audit post-relocation command classes and expose mixed-class GO split cost."""
from __future__ import annotations
import hashlib
import math


def analyse(words, *, descriptor_mode=None, mrel=False, block_lines=64,
            calendar_extra=0, command_only_extra=0):
    assert 1 <= block_lines <= 64
    counts, segments = {}, []
    current, begin = None, 0
    literal = []
    for i, w in enumerate(words):
        w = int(w)
        literal.append(w.to_bytes(24, 'little'))
        if w == 0:
            continue
        if w >> 184 != 0xa2:
            raise ValueError(f'command {i}: invalid magic')
        mode = (w >> 181) & 7
        if mrel:
            if descriptor_mode is None:
                raise ValueError('mrel requires full descriptor mode')
            mode = descriptor_mode
        if mode == 3:
            raise ValueError(f'command {i}: decoder-invalid mode3')
        counts[mode] = counts.get(mode, 0) + 1
        cls = mode >> 2
        if current is None:
            current = cls
        elif cls != current:
            segments.append(dict(begin=begin, limit=i, attention_class=current))
            begin, current = i, cls
    if current is not None:
        segments.append(dict(begin=begin, limit=len(words), attention_class=current))
    splits = max(0, len(segments) - 1)
    physical_block_bytes = math.ceil(block_lines * 136 / 128) * 128
    return dict(words=len(words), magic_words=sum(counts.values()), mode_counts=counts,
                literal_sha256=hashlib.sha256(b''.join(literal)).hexdigest(),
                segments=segments, extra_descriptors=splits,
                extra_install_ingress_edges=2 * splits, extra_programme_words_before_dedup=0,
                extra_hbm_bytes_conservative=splits * physical_block_bytes,
                added_idle_stream_edges_lower_bound=splits * (6 + calendar_extra + command_only_extra),
                split_policy='reuse full cache block and literal command words; retire/reopen with fresh epoch per segment',
                gap_validity='recompile complete calendar at certified drained class boundaries; expose unresolved live-state dependencies',
                status='single-class' if splits == 0 else 'priced GO split required; not silently rejected or executed unchanged')
