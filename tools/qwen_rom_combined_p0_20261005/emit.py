#!/usr/bin/env python3
"""Prepare the actual changed P0 source/host; never compile or launch a token.

Input is the authoritative already-passing guarded host, not a new oracle.
Only the backend and independent clock scheduling change. Existing released
checkpoint preload, all36 carry, fullhead, faults and ACK drain remain intact.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOST_SHA = 'a10ea144c1dfb7534b8a173405450a389aaab15580e24451d40f9378895e69c7'
TOP = 'ot_qwen_rom_combined_p0_20261005'
DONOR_TOP = 'ot_qwen_rom_rt_die_w12_stream4_tagged_ar'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('authoritative host seam differs: ' + old[:80])
    return text.replace(old, new)


def emit(host, output, top=TOP, transport_quiet=False):
    raw = Path(host).read_bytes()
    if hashlib.sha256(raw).hexdigest() != HOST_SHA:
        raise ValueError('requires original passing guarded-v2 full36+head host')
    text = raw.decode()
    text = replace_once(text, '#include "Vdie.h"',
                        '#include "Vdie.h"\n#include "clock.hpp"')
    text = replace_once(text,
                        '    if (fread(v.data(), 4, KV_ELEMS, fp) != KV_ELEMS) fatal("KV history size");',
                        '    if (fread(v.data(), 4, KV_ELEMS, fp) != KV_ELEMS || fgetc(fp) != EOF)\n'
                        '        fatal("P0 actual history must have exact full-layer extent");')
    text = replace_once(text,
                        '        if (k < 0) fatal("KV history value is not E4M3", long(e), long(v[e]));',
                        '        if (k < 0 || (k & 127) == 127)\n'
                        '            fatal("P0 history must be exact finite E4M3", long(e), long(v[e]));')
    text = replace_once(text,
                        '            if (kv_dir.empty()) kvc[d][s].assign(KV_ELEMS, 0);\n'
                        '            else kvc[d][s] = load_kv_codes',
                        '            if (kv_dir.empty()) fatal("P0 requires released history for every layer/rank");\n'
                        '            kvc[d][s] = load_kv_codes')
    if transport_quiet:
        text = replace_once(text,
                            '                for (int d = 0; d < D; d++) busy |= die[d]->kv_wb_busy;',
                            '                for (int d = 0; d < D; d++)\n'
                            '                    busy |= die[d]->kv_wb_busy || !die[d]->transport_quiet;')
    text = replace_once(text, 'die[d]->rm_kv_ideal = kv_ideal;',
                        'die[d]->rm_kv_ideal = kv_ideal;\n'
                        '        die[d]->hclk = 0; die[d]->warm_rst_n = 1;')
    marker = '    long me_busy[D] = {}, tile_edges[D] = {}, edges = 0;'
    text = replace_once(text, marker,
                        '    if (POS != 8191 || kv_ideal || stages.size() != 37)\n'
                        '        fatal("P0 requires L0..L35 plus fullhead at exact8K, real KV");\n'
                        '    for (int i = 0; i < 36; ++i)\n'
                        '        if (stages[i].name != "L" + std::to_string(i) || stages[i].layer != i)\n'
                        '            fatal("P0 layer name/actual region order");\n'
                        '    if (stages.back().name != "head") fatal("P0 fullhead missing");\n'
                        '    qwen_combined_p0::Clocks clocks;\n'
                        '    auto controller = [&](bool hi) { for (int d=0; d<D; ++d) die[d]->hclk=hi; };\n'
                        + marker)
    text = replace_once(text,
                        '        for (int d = 0; d < D; d++) die[d]->clk = 0;\n'
                        '        coll.clk = 0;\n        settle(live_all);',
                        '        clocks.edge(uint64_t(tick)*833333, controller, [&] {\n'
                        '            for (int d=0; d<D; ++d) die[d]->clk=0; coll.clk=0;\n'
                        '        }, [&] { settle(live_all); });')
    text = replace_once(text,
                        '        for (int d = 0; d < D; d++) die[d]->clk = 1;\n'
                        '        coll.clk = 1;\n'
                        '        for (int d = 0; d < D; d++) die[d]->eval();\n'
                        '        coll.eval();\n'
                        '        for (int d = 0; d < D; d++) if (tile_en[d]) fab[d]->edge();',
                        '        clocks.edge(uint64_t(tick)*833333+416666, controller, [&] {\n'
                        '            for (int d=0; d<D; ++d) die[d]->clk=1; coll.clk=1;\n'
                        '            for (int d=0; d<D; ++d) die[d]->eval(); coll.eval();\n'
                        '            // Keep the original pre-edge tile inputs through their capture.\n'
                        '            for (int d=0; d<D; ++d) if (tile_en[d]) fab[d]->edge();\n'
                        '        }, [&] { settle(live_all); });')
    text = text.replace('QWEN_ROM_STREAM4_PLAIN_AR_FULLTOKEN DONE',
                        'QWEN_ROM_COMBINED_P0_SOURCE_JOIN DONE')
    text = replace_once(text, '                    printf("QWEN_ROM_COMBINED_P0_SOURCE_JOIN DONE',
                        '                    printf("P0_CLOCK controller_rises=%llu elapsed_fs=%llu\\n",\n'
                        '                        (unsigned long long)clocks.controller_rises(),\n'
                        '                        (unsigned long long)clocks.elapsed_fs());\n'
                        '                    printf("QWEN_ROM_COMBINED_P0_SOURCE_JOIN DONE')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    (output/'fulltoken.cpp').write_text(text)
    (output/'clock.hpp').write_bytes(Path(__file__).with_name('clock.hpp').read_bytes())
    result = dict(status='PREPARED_SOURCE_JOIN_ONLY', donor_host_sha256=HOST_SHA,
                  top=top, full_token_run=False, adopted=False,
                  transport_quiet_required=transport_quiet,
                  die_parameters=dict(BASELINE_AR=1, PROTECTED_STREAM4=1, G=6144,
                      D=4, SW=64, NW=18, SNW=18, HBM_LAYERS=36, NSTK=4,
                      NPC=128, WBW=4, REAL_MEM=1, ENABLE_AR256=1,
                      HBM_PULLIN=0, CORE_FS=833333, CTL_FS=1024000),
                  physical_transport_ready=False,
                  canonical_verilator='5.050 (must match retained engine objects)',
                  history_backing='all144 released L0..L35 rank0..3 images; exact finite E4M3; no zero fallback',
                  scope='Actual original-AR consumer to producer protected simulation backend; no transport/physical/token PASS',
                  no_new_arithmetic=True, new_join_storage_bits=0,
                  new_join_latency_cycles=0,
                  reused_backend_model='results/rtl/qwen_stream4_protected_20261005/prebuild_model.json',
                  clock_model='independent periodic roots; coincident pins updated together before eval',
                  preserved='released payload/KV preloads, all36 sequential carry, full RTL head, fault checks, final tagged write-ACK drain/readback')
    (output/'prepared.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--top', default=TOP,
                        help='Owner-supplied final numerical top name; does not create a provider')
    parser.add_argument('--transport-quiet', action='store_true',
                        help='Require genuine transport quiet as well as consumer ACK drain before readback')
    args = parser.parse_args()
    print(json.dumps(emit(args.host, args.output, args.top, args.transport_quiet)))
