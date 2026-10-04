#!/usr/bin/env python3
"""Bind Dewey's existing initialized runtime to the actual stream4 root.

Only the selected top identifier changes. The original macro/HBM member
resolver remains authoritative; no model, preload, clock or arithmetic changes.
"""
from pathlib import Path
import tempfile
import qwen_rom_combined_access as predecessor

BASE_EMIT = predecessor.emit
TOP = 'ot_qwen_rom_combined_stream4_die'
BASE_TOP = 'ot_qwen_rom_combined_die'


def emit(die_header, tile_header, hbm_header, out, *, top=TOP, **parameters):
    if top not in (TOP,'ot_qwen_rom_combined_dspark_die'):
        raise ValueError('unknown actual STREAM4 top')
    hbm = Path(hbm_header).read_text()
    if 'ot_qwen_hbm_stream4_tagged__DOT__' not in hbm:
        raise ValueError('actual Claude STREAM4 generated HBM root required')
    actual = Path(die_header).read_text()
    if top + '__DOT__' not in actual:
        raise ValueError('actual stream4 generated root header required')
    with tempfile.TemporaryDirectory() as temporary:
        normalized = Path(temporary) / 'Vdie___024root.h'
        normalized.write_text(actual.replace(top, BASE_TOP))
        BASE_EMIT(normalized, tile_header, hbm_header, out, **parameters)
    target = Path(out) / 'combined_access.hpp'
    generated = target.read_text()
    if BASE_TOP + '__DOT__' not in generated:
        raise ValueError('predecessor generated no actual die members')
    target.write_text(generated.replace(BASE_TOP, top))
