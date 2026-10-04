#!/usr/bin/env python3
"""Initialize and wire a single actual STREAM4/near decoder layer.

The native tagged-row service is a required linked source, never a host server.
"""
import argparse
from pathlib import Path
import qwen_rom_combined_nearbaseline_runtime_emit as predecessor

ROOT=Path(__file__).resolve().parents[1]
TOP='ot_qwen_rom_combined_stream4_die'
ABI='combined-stream4-layer-v1'
initialized=predecessor.initialized


def emit(root=ROOT, *, dspark=False):
    if dspark:
        import qwen_rom_combined_dspark_runtime_emit as block
        src=block.emit(root)
        top=block.TOP
    else:
        src=predecessor.emit(root)
        top=TOP
    def replace(old,new):
        nonlocal src
        if src.count(old)!=1:raise ValueError('STREAM4 source anchor missing/ambiguous: '+old[:90])
        src=src.replace(old,new)
    # Selected Vdie/Vtile/Vcoll/Vhbm each report threads()==1. Keep the
    # independent RtPool workers; avoid a default internal pool per context.
    replace('    RtPool pool(threads);', '''    RtPool pool(threads);
    for(int w=0;w<pool.size();++w)pool.ctx(w)->threads(1);''')
    replace('    VerilatedContext dctx[D], cctx;', '''    VerilatedContext dctx[D], cctx;
    for(int d=0;d<D;++d)dctx[d].threads(1);
    cctx.threads(1);''')
    replace('#include "combined_driver.hpp"','#include "stream4_clock_driver.hpp"')
    replace('#include "hbm_stack_binding.hpp"','#include "stream4_runtime_binding.hpp"')
    src=src.replace('CombinedHBM','CombinedStream4')
    src=src.replace('qwen_combined::ClockSpec','qwen_stream4::ClockSpec')
    src=src.replace('qwen_combined::ClockDriver','qwen_stream4::ClockDriver')
    replace('if(hbm_clock.period_fs!=uint64_t(HBM_CLOCK_PS)*1000)fatal("compiled HBM CLK_PS mismatch");',
            'if(core_clock.period_fs!=uint64_t(STREAM4_CORE_FS))fatal("actual STREAM4 CORE_FS mismatch");')
    replace('        die[d]->rm_kv_ideal = 0;', '''        die[d]->rm_kv_ideal = 0;
        die[d]->rm_next_layer = 255; // one-layer run has no fabricated next notice
        die[d]->rm_early_go = 0;
        die[d]->rm_posted_wb = 0; // explicit non-posted baseline; wb debt still checked
        die[d]->rm_kv_free = 0;''')
    replace('    auto wire_coll = [&]() -> bool {', '''    std::array<unsigned,D> actual_mlp_base;
    for(int d=0;d<D;++d)actual_mlp_base[d]=qwen_combined::stream4_mlp_program_base(mem[d].desc);
    auto wire_coll = [&]() -> bool {''')
    replace('            for(int d=0;d<D;++d)ch|=hbm[d]->wire();', '''            for(int d=0;d<D;++d){
                ch|=hbm[d]->wire();
                if(!die[d]->clk)ch|=qwen_combined::wire_stream4_kv_free(*die[d],actual_mlp_base[d]);
            }''')
    if dspark:
        replace('all_done&=layer_fences[d].can_retire(sample(d));',
                'all_done&=layer_fences[d].can_retire(sample(d))&&qwen_combined::stream4_layer_terminal(*die[d]);')
    else:
        replace('for(int d=0;d<D;++d)all_done&=layer_fences[d].can_retire(sample(d));',
                'for(int d=0;d<D;++d)all_done&=layer_fences[d].can_retire(sample(d))&&qwen_combined::stream4_layer_terminal(*die[d]);')
    replace('hbm[d]->clocks(clock_event.service_high);','hbm[d]->clocks(clock_event.core_high);')
    replace('    for(int d=0;d<D;++d)die[d]->eval();\n    coll.eval();', '''    // Expose actual asserted resets/LOW clocks to the native hook before
    // any first eval. The hook forwards pins; it owns no model or edges.
    for(int d=0;d<D;++d)hbm[d]->wire();
    for(int d=0;d<D;++d)die[d]->eval();
    coll.eval();''')
    replace('        coll.clk=clock_event.core_high;\n        for(int d=0;d<D;++d)die[d]->eval();', '''        coll.clk=clock_event.core_high;
        // All clocks/resets are now assigned. Forward the held pre-edge
        // requests and actual hclk to the native hook BEFORE either side
        // evaluates. Post-edge outputs are propagated by settle below.
        for(int d=0;d<D;++d)hbm[d]->wire();
        for(int d=0;d<D;++d)die[d]->eval();''')
    replace('QWEN_DSPARK_NEAR_COMPONENT_DONE stages=%zu' if dspark else 'QWEN_ROM_NEARBASELINE PASS stages=%zu',
            'QWEN_DSPARK_STREAM4_COMPONENT_DONE stages=%zu' if dspark else 'QWEN_ROM_STREAM4_COMBINED PASS stages=%zu')
    return '// STREAM4_RUNTIME_ABI '+ABI+'; actual selected top '+top+'\n'+src


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--dspark',action='store_true')
    a=p.parse_args()
    with a.out.open('x') as stream:stream.write(emit(dspark=a.dspark))
