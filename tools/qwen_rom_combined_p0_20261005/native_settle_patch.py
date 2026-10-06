#!/usr/bin/env python3
"""Prepare an opt-in native host change; never regenerate or execute a model.

The original rising callback completes die/collective eval before tile capture.
Tile capture changes tile internals, but no die or collective input pin. The
first settle iteration can therefore wire those outputs without evaluating the
same die/collective pins twice. Every later dirty settle iteration still runs.
This applies only to the literal untimed, externally clocked P0 host seam; any
new external input mutation between these calls must invalidate this contract.
No clock edge, tile capture, fixed-point wiring, arithmetic or fault check moves.
"""
import argparse
import hashlib
import json
from pathlib import Path


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('literal native host seam differs: '+old[:80])
    return text.replace(old, new)


def prepare(source, output):
    raw = source.read_bytes()
    text = raw.decode()
    if 'qwen_combined_p0::Clocks clocks;' not in text or '!die[d]->transport_quiet' not in text:
        raise ValueError('actual independently clocked protected P0 host required')
    text = replace_once(text, '    long passes = 0;',
        '    long passes = 0;\n'
        '    const char* native_switch=getenv("QWEN_P0_NATIVE_REENTRY_SKIP");\n'
        '    const bool native_reentry_skip=native_switch && strcmp(native_switch,"1")==0;\n'
        '    if(native_switch && strcmp(native_switch,"0") && strcmp(native_switch,"1"))\n'
        '        fatal("QWEN_P0_NATIVE_REENTRY_SKIP must be 0 or 1");\n'
        '    bool native_die_coll_evaluated=false;\n'
        '    uint64_t native_die_evals=0,native_coll_evals=0,native_reentries_skipped=0;\n'
        '    const char* native_profile_switch=getenv("QWEN_P0_NATIVE_PROFILE");\n'
        '    const bool native_profile=native_profile_switch && strcmp(native_profile_switch,"1")==0;\n'
        '    uint64_t native_die_ns=0,native_coll_ns=0,native_fabric_comb_ns=0;\n'
        '    uint64_t native_fabric_edge_ns=0,native_propagate_ns=0;\n'
        '    auto native_timed=[&](uint64_t& total, auto&& fn) {\n'
        '        if(!native_profile) {fn(); return;}\n'
        '        auto begin=std::chrono::steady_clock::now(); fn();\n'
        '        total+=std::chrono::duration_cast<std::chrono::nanoseconds>(\n'
        '            std::chrono::steady_clock::now()-begin).count();\n'
        '    };')
    text = replace_once(text, '    auto settle = [&](bool fabric_live[D]) {',
        '    auto settle = [&](bool fabric_live[D]) {\n'
        '        const bool skip_first=native_reentry_skip && native_die_coll_evaluated;\n'
        '        native_die_coll_evaluated=false;')
    text = replace_once(text,
        '            for (int d = 0; d < D; d++) die[d]->eval();\n'
        '            coll.eval();\n'
        '            bool ch = wire_coll();',
        '            if(n!=0 || !skip_first) {\n'
        '                native_timed(native_die_ns,[&]{for (int d=0; d<D; ++d) die[d]->eval();});\n'
        '                native_timed(native_coll_ns,[&]{coll.eval();});\n'
        '                native_die_evals+=D; ++native_coll_evals;\n'
        '            } else ++native_reentries_skipped;\n'
        '            bool ch = wire_coll();')
    fabric_call = 'fab[d]->eval_changed();' if 'native_fabric_dirty' in text else 'fab[d]->eval();'
    text = replace_once(text,
        '                if (fabric_live[d] && fab[d]->propagate()) { ch = true; '+fabric_call+' }',
        '                if (fabric_live[d]) {\n'
        '                    bool dirty=false;\n'
        '                    native_timed(native_propagate_ns,[&]{dirty=fab[d]->propagate();});\n'
        '                    if(dirty) { ch=true; native_timed(native_fabric_comb_ns,[&]{'+fabric_call+'}); }\n'
        '                }')
    # Preserve the explicit eval -> original pre-edge tile capture ordering.
    # The marker is consumed at the immediately following settle entry, even
    # with the option OFF. HCLK-only and falling-core entries cannot inherit it.
    text = replace_once(text,
        '            for (int d=0; d<D; ++d) die[d]->eval(); coll.eval();\n'
        '            // Keep the original pre-edge tile inputs through their capture.\n'
        '            for (int d=0; d<D; ++d) if (tile_en[d]) fab[d]->edge();',
        '            native_timed(native_die_ns,[&]{for (int d=0; d<D; ++d) die[d]->eval();});\n'
        '            native_timed(native_coll_ns,[&]{coll.eval();});\n'
        '            native_die_evals+=D; ++native_coll_evals;\n'
        '            // Keep the original pre-edge tile inputs through their capture.\n'
        '            native_timed(native_fabric_edge_ns,[&]{for (int d=0; d<D; ++d) if (tile_en[d]) fab[d]->edge();});\n'
        '            native_die_coll_evaluated=true;')
    text = replace_once(text, '        if (tick % progress_every == 0) {',
        '        if (tick % progress_every == 0) {\n'
        '            printf("P0_NATIVE_EVAL tick=%ld enabled=%d die_evals=%llu coll_evals=%llu "\n'
        '                   "reentries_skipped=%llu die_ns=%llu coll_ns=%llu "\n'
        '                   "fabric_comb_ns=%llu fabric_edge_ns=%llu propagate_ns=%llu\\n",tick,int(native_reentry_skip),\n'
        '                   (unsigned long long)native_die_evals,\n'
        '                   (unsigned long long)native_coll_evals,\n'
        '                   (unsigned long long)native_reentries_skipped,\n'
        '                   (unsigned long long)native_die_ns,(unsigned long long)native_coll_ns,\n'
        '                   (unsigned long long)native_fabric_comb_ns,\n'
        '                   (unsigned long long)native_fabric_edge_ns,\n'
        '                   (unsigned long long)native_propagate_ns);')
    with output.open('x') as f:
        f.write(text)
    return dict(status='PREPARED_HOST_ONLY_NOT_COMPILED_OR_RUN',
        source_sha256=hashlib.sha256(raw).hexdigest(),
        output_sha256=hashlib.sha256(text.encode()).hexdigest(),
        enable='QWEN_P0_NATIVE_REENTRY_SKIP=1; defaultOFF',
        wall_attribution='QWEN_P0_NATIVE_PROFILE=1; defaultOFF; host steady-clock only, no DUT time/pin mutation',
        changed='Skip one redundant die/collective eval reentry after explicit rising eval, before any input rewiring',
        preserved='All pin and clock events, tile eval/capture edges, fixed-point propagation, released state, arithmetic, faults and drain',
        generated_model_changed=False, exactness_pass=False, performance_gain_measured=False)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(prepare(a.source, a.output)))
