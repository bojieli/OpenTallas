#!/usr/bin/env python3
"""Additive posted-write core emitter; retained emitter and arithmetic unchanged.

POSTED_KV is off by default. Ordinary SU issue retains SU-idle serialization,
but can overlap tagged HBM write-done with later work. Barrier/END drain and
kv_write_flush are byte-identical to the retained core. The existing KV service
retains all write ownership, tags, generations, buffers and bounds checks.
"""
import qwen_rom_rt_core_emit_w12 as retained

CORE = retained.CORE
VSTREAM = retained.VSTREAM
emit_vstream = retained.emit_vstream


def emit(text):
    text = retained.emit(text)
    old = '    parameter integer KV_VEC_WRITE_BRIDGE = 0,'
    if text.count(old) != 1:
        raise ValueError('posted core parameter anchor')
    text = text.replace(old, old + '\n    parameter integer POSTED_KV = 0,', 1)
    old = '(su_ready && (!KV_VEC_WRITE_BRIDGE || (su_idle && kv_write_drained)));'
    if text.count(old) != 1:
        raise ValueError('posted ordinary SU issue anchor')
    text = text.replace(old, '(su_ready && (!KV_VEC_WRITE_BRIDGE || (su_idle && (POSTED_KV || kv_write_drained))));', 1)
    return '// POSTED_KV successor: barriers/END keep real write-done fence.\n' + text
