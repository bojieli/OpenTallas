#!/usr/bin/env python3
"""Opt-in source-only tile dirty eval; never edit an input or launch a model.

Only combinational settle evaluations are filtered. Initialization and every
Fabric.edge low/high evaluation remain full. Native debug/negative mutations
must call the affected Fabric.invalidate_all() after the write and before
settle; untracked memory mutations cannot be inferred from unchanged inputs.
Socrates owns changed-host minimum validation and final full-token execution.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('native fabric source seam differs: '+old[:100])
    return text.replace(old, new, 1)


def patch(text, enable=False):
    if not enable:
        return text
    if 'native_fabric_dirty' in text:
        raise ValueError('already patched; use the original separate input')
    text = once(text, '    std::vector<uint8_t> kv_ce_prev;',
        '    std::vector<uint8_t> kv_ce_prev;\n'
        '    // native_fabric_dirty: independent bytes, never packed concurrent bits.\n'
        '    std::vector<uint8_t> native_fabric_dirty;\n'
        '    uint64_t native_full_tile_evals = 0, native_changed_tile_evals = 0;')
    text = once(text, '        kv_ce_prev.assign(NT, 0);',
        '        kv_ce_prev.assign(NT, 0);\n'
        '        native_fabric_dirty.assign(NT, 1);')
    original_eval = '    void eval() { pool.run(t.size(), [&](size_t i) { t[i]->eval(); }); }'
    text = once(text, original_eval,
        '    void invalidate_all() {\n'
        '        std::fill(native_fabric_dirty.begin(), native_fabric_dirty.end(), uint8_t(1));\n'
        '    }\n'
        '    void eval() {\n'
        '        // Initialization and ALL real clock edges still evaluate every tile.\n'
        '        pool.run(t.size(), [&](size_t i) { t[i]->eval(); });\n'
        '        native_full_tile_evals += t.size();\n'
        '        std::fill(native_fabric_dirty.begin(), native_fabric_dirty.end(), uint8_t(0));\n'
        '    }\n'
        '    void eval_changed() {\n'
        '        // Retain whole-fabric cold-POR evaluation, including masked/undriven outputs.\n'
        '        if (!die.rt_rst_n) { eval(); return; }\n'
        '        native_changed_tile_evals += std::count(native_fabric_dirty.begin(), native_fabric_dirty.end(), uint8_t(1));\n'
        '        pool.run(t.size(), [&](size_t i) {\n'
        '            if (native_fabric_dirty[i]) {\n'
        '                t[i]->eval();\n'
        '                native_fabric_dirty[i] = 0;\n'
        '            }\n'
        '        });\n'
        '    }')
    text = once(text, '            if (ch) any.store(true, std::memory_order_relaxed);',
        '            // Preserve invalidation debt until this tile actually evaluates.\n'
        '            native_fabric_dirty[i] = uint8_t(native_fabric_dirty[i] || ch);\n'
        '            if (native_fabric_dirty[i]) any.store(true, std::memory_order_relaxed);')
    text = once(text,
        'if (fabric_live[d] && fab[d]->propagate()) { ch = true; fab[d]->eval(); }',
        'if (fabric_live[d] && fab[d]->propagate()) { ch = true; fab[d]->eval_changed(); }')
    # Actual preload call sites, after each write and its worker barrier.
    # Initial VM/embedding writes precede these already-invalidating calls.
    # Do not change the preloader, memory content, phase edge or reset source.
    for name, args in (
        ('preload_die_roms', '*die[d], mem[d], pool'),
        ('preload_tile_roms', '*fab[d], mem[d]'),
        ('preload_hbm', '*die[d], stages[s].layer, kvc[d][s]'),
        ('preload_slices_ideal', '*fab[d], kvc[d][0], POS'),
        ('preload_slices_ideal', '*fab[d], kvc[d][cur], POS'),
    ):
        call = name+'('+args+');'
        if call not in text:
            raise ValueError('actual preload invalidation seam missing: '+call)
        # A braced statement also preserves the existing single-line if/for
        # guards: the invalidation executes iff that same preload executes.
        text = text.replace(call, '{ '+call+' fab[d]->invalidate_all(); }')
    return text


def emit(source, output, enable=False):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError('separate input/output required; live source is immutable')
    raw = source.read_bytes()
    if enable:
        original = raw.decode()
        # Confirm the actual clock-edge and global convergence bodies are
        # byte-identical; root/coll settle changes belong to Socrates alone.
        edge = re.search(r'    void edge\(\) \{.*?\n    \}', original, re.S)
        if not edge:
            raise ValueError('actual Fabric.edge body missing')
        transformed = patch(original, True)
        if edge.group() not in transformed:
            raise ValueError('real low/high edge body changed')
        data = transformed.encode()
    else:
        data = raw
    with output.open('xb') as f:
        f.write(data)
    return dict(enabled=enable, input_sha256=hashlib.sha256(raw).hexdigest(),
        output_sha256=hashlib.sha256(data).hexdigest(),
        scope='host-source combinational tile eval only; no compiled model/archive/RTL/runtime change',
        preserved='all Fabric.edge low/high evals, initialization, coldPOR full eval, clocks, whole propagate/tree/t_lvl/fault scan, fixedpoint convergence',
        invalidation='full affected-fabric invalidation after every existing ROM/HBM/slice preload; debug/negative direct-memory mutations MUST invoke invalidate_all() after write and before settle, outside pool workers',
        counters='per-Fabric native_full_tile_evals/native_changed_tile_evals; count model calls, not exactness/performance proof',
        owner_validation_pending=True, adopted=False)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--enable',action='store_true',help='defaultOFF; change only a new host source')
    a=p.parse_args()
    print(json.dumps(emit(a.input,a.output,a.enable),indent=2))
