#!/usr/bin/env python3
"""Emit the actual combined runtime from the immutable W12 REAL_MEM host.

Reuses its tile fabric, macro preloads, E4M3 transport and result readback.
Only replaces the die/HBM clock/port composition and full-width tag wiring.
The owning Laplace build compiles this against the actual generated models.
"""
import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'rtl/test/qwen_rom_runtime/qwen_rom_rt_w12_rm.cpp'
BASE_SHA = '5da95b5764c7bf837e59ebcc1806853f16474b46dc3b85352d71fdf3c7086817'


def emit(root=ROOT):
    raw = (root/BASE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASE_SHA:
        raise ValueError('pinned W12 REAL_MEM host changed')
    src = raw.decode()
    def replace(old, new):
        nonlocal src
        if src.count(old) != 1:
            raise ValueError('runtime source anchor is not unique: '+old[:90])
        src = src.replace(old, new)
    replace('#include "rm_access.hpp"', '#include "combined_driver.hpp"\n#include "combined_access.hpp"')
    replace('// ---- via-mask writers:', '#include "hbm_stack_binding.hpp"\n// ---- via-mask writers:')
    replace('static void preload_hbm(Vdie& v, int layer, const std::vector<uint8_t>& codes) {\n    auto* r = v.rootp;',
            'static void preload_hbm(Vdie&, CombinedHBM& h, int layer, const std::vector<uint8_t>& codes) {')
    replace('rm_hbm_mem(r)[size_t(layer) * 131072 + s][k]', 'h.memory(size_t(layer) * 131072 + s)[k]')
    replace('preload_hbm(*die[d], stages[s].layer, kvc[d][s]);', 'preload_hbm(*die[d], *hbm[d], stages[s].layer, kvc[d][s]);')
    replace('rm_hbm_mem(v.rootp)[lb + a / 2][((a & 1) * 16 + (POS & 15)) / 4]',
            'hbm[d]->memory(lb + a / 2)[((a & 1) * 16 + (POS & 15)) / 4]')
    replace('rm_hbm_mem(v.rootp)[lb + a / 2][((a & 1) * 16 + dd % 16) / 4]',
            'hbm[d]->memory(lb + a / 2)[((a & 1) * 16 + dd % 16) / 4]')
    replace('    long max_cycles = 400000000L;',
            '    qwen_combined::ClockSpec core_clock{0,0}, hbm_clock{0,0};')
    replace('        else if (k == "--max-cycles") max_cycles = atol(argv[i + 1]);', '''        else if (k == "--core-period-fs") core_clock.period_fs = strtoull(argv[i+1],nullptr,10);
        else if (k == "--core-first-rise-fs") core_clock.first_rise_fs = strtoull(argv[i+1],nullptr,10);
        else if (k == "--service-period-fs") hbm_clock.period_fs = strtoull(argv[i+1],nullptr,10);
        else if (k == "--service-first-rise-fs") hbm_clock.first_rise_fs = strtoull(argv[i+1],nullptr,10);''')
    replace('    int threads = 16;', '''    if(kv_ideal)fatal("combined runtime has no ideal memory selection");
    qwen_combined::ClockDriver clocks(core_clock,hbm_clock);
    if(hbm_clock.period_fs!=uint64_t(HBM_CLOCK_PS)*1000)fatal("compiled HBM CLK_PS mismatch");
    static_assert(D==4 && G==6144 && SW==64 && COUNTWIDTH==18,"fullshape combined runtime");
    int threads = 16;''')
    replace('    std::unique_ptr<Fabric> fab[D];', '    std::unique_ptr<Fabric> fab[D];\n    std::unique_ptr<CombinedHBM> hbm[D];')
    replace('        die[d]->rm_kv_ideal = kv_ideal;', '''        die[d]->rm_kv_ideal = 0;
        die[d]->clk=die[d]->hclk=die[d]->rst_n=die[d]->hrst_n=0;
        hbm[d].reset(new CombinedHBM(*die[d],dctx[d]));
        hbm[d]->clocks(false);''')
    replace('setb(itag, 32 * d, 32, die[d]->c_tag);','setb(itag, 44 * d, 44, die[d]->c_tag);')
    replace('            coll.eval();\n            bool ch = wire_coll();', '''            coll.eval();
            for(int d=0;d<D;++d)hbm[d]->eval();
            bool ch = wire_coll();
            for(int d=0;d<D;++d)ch|=hbm[d]->wire();''')
    replace('    for (long tick = 0;; tick++) {\n        for (int d = 0; d < D; d++) die[d]->clk = 0;\n        coll.clk = 0;\n        settle(live_all);', '''    std::array<qwen_combined::LayerFence,D> layer_fences;
    for(auto& f:layer_fences)f.begin(unsigned(uint8_t(stages[0].layer)),POS,TOKEN);
    auto sample=[&](int d) {
        auto& v=*die[d];
        return qwen_combined::RankPins{bool(v.rst_n),bool(v.h_start),bool(v.core_start_o),
            bool(v.kv_arm_o),bool(v.kv_layer_start_o),bool(v.rst_n),bool(v.kv_layer_start_o),
            unsigned(v.rm_layer),unsigned(v.tp_pos),unsigned(v.tp_token),unsigned(v.rm_layer),unsigned(v.tp_pos),
            bool(v.s_done),bool(v.kv_ok_o),bool(v.kv_drained_o),bool(v.row_drained_o),
            bool(v.mem_fault||v.core_fault||v.s_fault||coll.fault)};
    };
    bool booted=false,pulse_pending=false;
    for (long tick = 0;; tick++) {
        settle(live_all);
        auto clock_event=clocks.next();
        for(int d=0;d<D;++d)layer_fences[d].observe(sample(d),clock_event);''')
    replace('            if (cyc > 8 && all_done && !stage_done) {', '''            for(int d=0;d<D;++d)all_done&=layer_fences[d].can_retire(sample(d));
            if (booted && all_done && !stage_done) {
                for(int d=0;d<D;++d)layer_fences[d].retire(sample(d));''')
    replace('            if (cyc > max_cycles) { printf("timeout cyc=%u\\n", cyc); return 3; }', '')
    replace('        for (int d = 0; d < D; d++) {\n            uint8_t me = die[d]->me_clk_en;',
            '        if(clock_event.core_rise())for (int d = 0; d < D; d++) {\n            uint8_t me = die[d]->me_clk_en;')
    replace('        for (int d = 0; d < D; d++) die[d]->clk = 1;\n        coll.clk = 1;\n        for (int d = 0; d < D; d++) die[d]->eval();\n        coll.eval();\n        for (int d = 0; d < D; d++) if (tile_en[d]) fab[d]->edge();\n        edges++;', '''        // Assign EVERY model's clocks before evaluating ANY sequential model.
        // Ports still carry the pre-edge values from settle(), including ties.
        for(int w=0;w<pool.size();++w)pool.ctx(w)->time(clock_event.time_fs/1000);
        cctx.time(clock_event.time_fs/1000);
        for(int d=0;d<D;++d){
            dctx[d].time(clock_event.time_fs/1000);
            die[d]->clk=clock_event.core_high;die[d]->hclk=clock_event.service_high;
            hbm[d]->clocks(clock_event.service_high);
        }
        coll.clk=clock_event.core_high;
        for(int d=0;d<D;++d)die[d]->eval();
        coll.eval();
        for(int d=0;d<D;++d)hbm[d]->eval();
        if(clock_event.core_rise()){
            for(int d=0;d<D;++d)if(tile_en[d])fab[d]->edge();
            ++edges;
        }
        if(pulse_pending&&clock_event.core_rise()){
            for(int d=0;d<D;++d)die[d]->h_start=0;
            pulse_pending=false;
        }
        if(!booted&&clocks.core_rises()>=8&&clocks.service_rises()>=8){
            for(int d=0;d<D;++d){die[d]->rst_n=die[d]->hrst_n=1;die[d]->h_start=1;}
            pulse_pending=true;booted=true;stage_start=die[0]->cyc;
        }''')
    replace('        for (int d = 0; d < D; d++) die[d]->h_start = 0;', '')
    replace('                die[d]->h_start = 1;\n                busy0[d]', '''                die[d]->h_start = 1;
                layer_fences[d].begin(unsigned(uint8_t(stages[cur].layer)),POS,TOKEN);
                busy0[d]''')
    replace('            stage_start = long(die[0]->cyc);', '            pulse_pending=true;\n            stage_start = long(die[0]->cyc);')
    replace('QWEN_ROM_REALMEM PASS stages=%zu cycles=%u edges=%ld settle_max=%d wall_s=%.1f RSS_KiB=%ld threads=%d kv_ideal=%d',
            'QWEN_ROM_COMBINED PASS stages=%zu cycles=%u edges=%ld settle_max=%d wall_s=%.1f RSS_KiB=%ld threads=%d kv_ideal=%d')
    return '// GENERATED source-bound combined runtime; baseline host SHA '+BASE_SHA+'\n'+src


def main():
    ap=argparse.ArgumentParser(description=__doc__.splitlines()[0]);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();text=emit()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.open('x') as f:f.write(text)
    print(a.out)


if __name__=='__main__':main()
