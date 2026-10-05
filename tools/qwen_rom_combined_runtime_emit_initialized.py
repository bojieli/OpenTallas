#!/usr/bin/env python3
"""Initialize every actual model before loading or writing any stage preload.

The pinned BASE and predecessor emitter remain unchanged. No clocks rise and
no commands are accepted during initialization; all reset/start pins are low.
"""
from pathlib import Path
import qwen_rom_combined_runtime_emit as predecessor

ROOT = Path(__file__).resolve().parents[1]
BASE_EMIT = predecessor.emit
INITIALIZATION_ABI = 'combined-initial-eval-v1'


def initialize_source(src):
    if '// INITIALIZATION_ABI ' in src:
        raise ValueError('initialized host must not be transformed twice')
    loads = '''    for (int d = 0; d < D; d++) load_images(mem[d], stages[0].dir[d]);
    printf("images loaded in %.1f s\\n", std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count());'''
    anchor = '    Vcoll coll(&cctx, "coll");'
    if src.count(loads) != 1 or src.count(anchor) != 1:
        raise ValueError('initialization source anchors missing/ambiguous')
    src = src.replace(loads, '    // Initial stage loading follows all model initial blocks below.')
    init = '''
    // Complete Verilator initial blocks BEFORE writing ROM/SRAM/HBM payloads.
    // The macro models initialize arr on first eval. No edge/start is issued.
    coll.clk=0; coll.rst_n=0;
    for(int d=0;d<D;++d) {
        die[d]->clk=die[d]->hclk=die[d]->rst_n=die[d]->hrst_n=die[d]->h_start=0;
        hbm[d]->clocks(false);
        fab[d]->set_clk(0);
        for(auto& tile:fab[d]->t) {
            tile->rst_n=0; tile->ib_go=0; tile->kvw_ce=0;
        }
    }
    for(int d=0;d<D;++d)die[d]->eval();
    coll.eval();
    for(int d=0;d<D;++d)hbm[d]->eval();
    for(int d=0;d<D;++d)fab[d]->eval();
'''
    src = src.replace(anchor, anchor+init+loads)
    return '// INITIALIZATION_ABI '+INITIALIZATION_ABI+'\n'+src


def emit(root=ROOT):
    return initialize_source(BASE_EMIT(root))
