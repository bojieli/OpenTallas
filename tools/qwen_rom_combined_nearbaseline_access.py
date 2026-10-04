#!/usr/bin/env python3
"""Bind Dewey's existing initialized runtime to the actual nearbaseline root.

Only the selected top identifier changes. The original macro/HBM member
resolver remains authoritative; no model, preload, clock or arithmetic changes.
"""
from pathlib import Path
import tempfile
import qwen_rom_combined_access as predecessor

BASE_EMIT = predecessor.emit
TOP = 'ot_qwen_rom_combined_nearbaseline_die'
BASE_TOP = 'ot_qwen_rom_combined_die'


def emit(die_header, tile_header, hbm_header, out, **parameters):
    actual = Path(die_header).read_text()
    if TOP + '__DOT__' not in actual:
        raise ValueError('actual nearbaseline generated root header required')
    with tempfile.TemporaryDirectory() as temporary:
        normalized = Path(temporary) / 'Vdie___024root.h'
        normalized.write_text(actual.replace(TOP, BASE_TOP))
        BASE_EMIT(normalized, tile_header, hbm_header, out, **parameters)
    target = Path(out) / 'combined_access.hpp'
    generated = target.read_text()
    if BASE_TOP + '__DOT__' not in generated:
        raise ValueError('predecessor generated no actual die members')
    target.write_text(generated.replace(BASE_TOP, TOP))
