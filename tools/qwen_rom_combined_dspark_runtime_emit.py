#!/usr/bin/env python3
"""Enclosing one-layer host for the opt-in owner VPOS/KVmp/near successor.

Actual program sidecar supplies slot bases; native RTL owns math, row service,
ACK and drain. Compatible generated top/access headers are required. This does
not select a cached single-position model or credit standalone DSpark results.
"""
import argparse
from pathlib import Path
import qwen_rom_combined_nearbaseline_runtime_emit as predecessor

ROOT = Path(__file__).resolve().parents[1]
TOP = 'ot_qwen_rom_combined_dspark_die'


def emit(root=ROOT):
    src = predecessor.emit(root)
    def replace(old, new):
        nonlocal src
        if src.count(old) != 1:
            raise ValueError('DSpark enclosing host anchor: ' + old[:80])
        src = src.replace(old, new)
    replace('#include "combined_driver.hpp"',
            '#include "combined_driver.hpp"\n#include "dspark_slot_binding.hpp"\n#include <sstream>')
    replace('constexpr size_t VM_ELEMS = 177808,', 'constexpr size_t VM_ELEMS = 1048576,')
    replace('static void load_images(DieMem& m, const std::string& p) {',
            'static void load_images(DieMem& m, const std::string& p, bool decoder) {')
    replace('struct DieMem {', 'struct DieMem {\n    std::vector<qwen_combined::NearPositionBases> near_slots;')
    replace('    m.prog = QwenHex::load(p + "/program.hex", 32);',
            '    if(decoder)m.near_slots=qwen_combined::load_near_position_bases(p+"/near_slot_bases.hex");\n    m.prog = QwenHex::load(p + "/program.hex", 32);')
    replace('if(m.desc.empty() || (m.desc[0]&3)!=3 || (m.desc[0]>>62)!=0)',
            'if(decoder && (m.desc.empty() || (m.desc[0]&3)!=3 || (m.desc[0]>>62)!=0))')
    replace('if (m.prog.size() > 64 * 32 || m.desc.size() > 8)',
            'if (m.prog.size() > 1024 * 32 || m.desc.size() > 64)')
    replace('m.prog.resize(64 * 32, 0); m.desc.resize(8, 0);',
            'm.prog.resize(1024 * 32, 0); m.desc.resize(64, 0);')
    # Reuse the existing VPRM ACCEPT plan line: pending token then actual drafts.
    # Targets come ONLY from the actual head's seq_tok_vec in RTL.
    replace('    std::vector<Stage> stages;', '    std::vector<Stage> stages;\n    std::vector<uint32_t> acc_toks;')
    replace('            Stage st; st.name = n;', '''            if(std::string(n)=="ACCEPT") {
                if(!acc_toks.empty() || !stages.empty())fatal("duplicate/late ACCEPT input");
                char line[4096];if(!fgets(line,sizeof(line),fp))fatal("missing ACCEPT input");
                std::istringstream words(line);std::string word;
                while(words>>word){
                    size_t used=0;unsigned long tok=std::stoul(word,&used,10);
                    if(used!=word.size() || tok>=(1ul<<COUNTWIDTH) || acc_toks.size()==4)
                        fatal("invalid actual pending/draft token");
                    acc_toks.push_back(uint32_t(tok));
                }
                continue;
            }
            Stage st; st.name = n;''')
    replace('    if(stages.size()!=1 || stages[0].layer<0)\n        fatal("near baseline requires exactly one decoder layer");', '''    if(stages[0].layer<0 || stages.size()>2 ||
       (stages.size()==2 && stages[1].name!="head"))
        fatal("DSpark requires one decoder optionally followed by actual head");
    const bool accept_commit=(stages.size()==2);
    if(accept_commit && (acc_toks.empty() || acc_toks[0]!=unsigned(TOKEN)))
        fatal("HEAD requires actual ACCEPT pending/draft inputs");
    if(!accept_commit && !acc_toks.empty())fatal("ACCEPT input without actual head");''')
    replace('    DieMem mem[D];', '''    if(accept_commit)for(int d=0;d<D;++d){
        for(const char* name:{"program.hex","segments.hex","matrix_int8.hex","matrix_scale_bf16.hex","crom.hex"}){
            std::ifstream input(stages[1].dir[d]+"/"+name);
            if(!input.good())fatal("actual HEAD image missing before launch",d);
        }
        const auto head_desc=QwenHex::load(stages[1].dir[d]+"/segments.hex",2);
        if(head_desc.empty())fatal("actual HEAD descriptor missing",d);
    }
    DieMem mem[D];''')
    replace('        die[d]->rm_kv_ideal = 0;',
            '        die[d]->rm_kv_ideal = 0;\n        qwen_combined::initialize_dspark_inputs(*die[d]);')
    src=src.replace('load_images(mem[d], stages[0].dir[d]);',
                    'load_images(mem[d], stages[0].dir[d],true);')
    src=src.replace('load_images(mem[d], stages[cur].dir[d]);',
                    'load_images(mem[d], stages[cur].dir[d],stages[cur].layer>=0);')
    # Existing one-layer host has initial preload and an unreachable stage-switch
    # preload. Bind both so widening its stage scope cannot silently lose slots.
    old='preload_die_roms(*die[d], mem[d], pool);'
    if src.count(old)!=2:raise ValueError('actual ROM preload sites changed')
    src=src.replace(old, '''if(stages[cur].layer>=0) {
            qwen_combined::bind_dspark_decoder_slots(*die[d],mem[d].near_slots,POS,VM_ELEMS);
            if(accept_commit && mem[d].near_slots.size()!=acc_toks.size())
                fatal("actual draft/decoder block extent mismatch",d);
        }
        '''+old)
    # Initial preload precedes the runtime cur declaration; its stage is zero.
    initial_end=src.index('    auto wire_coll = [&]() -> bool {')
    src=src[:initial_end].replace('stages[cur].layer>=0','stages[0].layer>=0')+src[initial_end:]
    replace('    bool booted=false,pulse_pending=false;', '''    bool booted=false,pulse_pending=false;
    size_t acc_feed=0;
    bool acc_seen[D]={};unsigned accepted_n[D]={},accepted_bonus[D]={};''')
    replace('            uint32_t cyc = die[0]->cyc;', '''            uint32_t cyc = die[0]->cyc;
            if(accept_commit && stages[cur].layer<0)for(int d=0;d<D;++d){
                if(die[d]->acc_done && !acc_seen[d]){
                    if(die[d]->seq_n_tok!=acc_toks.size() ||
                       die[d]->acc_n_emit==0 || die[d]->acc_n_emit>acc_toks.size() ||
                       die[d]->acc_n_emit!=die[d]->acc_a+1)
                        fatal("actual HEAD/ACCEPT extent mismatch",d);
                    acc_seen[d]=true;accepted_n[d]=die[d]->acc_n_emit;
                    accepted_bonus[d]=die[d]->acc_bonus;
                    printf("ACCEPT die=%d a=%u n_emit=%u bonus=%u cyc=%u\\n",d,
                        unsigned(die[d]->acc_a),accepted_n[d],accepted_bonus[d],cyc);
                    fflush(stdout);
                }
            }''')
    replace('            for(int d=0;d<D;++d)all_done&=layer_fences[d].can_retire(sample(d));', '''            for(int d=0;d<D;++d){
                all_done&=layer_fences[d].can_retire(sample(d));
                if(accept_commit && stages[cur].layer<0){
                    all_done&=acc_seen[d] && die[d]->kv_committed_v &&
                        die[d]->kv_committed_len==unsigned(POS)+accepted_n[d] &&
                        die[d]->kv_ok_o && die[d]->kv_drained_o && die[d]->row_drained_o;
                    if(acc_seen[d] && (accepted_n[d]!=accepted_n[0] || accepted_bonus[d]!=accepted_bonus[0]))
                        fatal("TP4 actual acceptance disagreement",d);
                }
            }''')
    # Held loader pins are consumed ONLY on real core rising edges. No helper
    # ticks, expected targets, host acceptance calculation or host commit pulse.
    replace('        if(!booted&&clocks.core_rises()>=8&&clocks.service_rises()>=8){', '''        if(clock_event.core_rise())for(int d=0;d<D;++d){
            die[d]->acc_start_v=die[d]->acc_tokx_v=die[d]->acc_arm=0;
        }
        if(accept_commit && booted && clock_event.core_rise() && acc_feed<acc_toks.size()){
            for(int d=0;d<D;++d){
                if(acc_feed==0){die[d]->acc_start_v=1;die[d]->acc_start_tok=acc_toks[0];}
                else {die[d]->acc_tokx_v=1;die[d]->acc_tokx_slot=acc_feed;die[d]->acc_tokx_tok=acc_toks[acc_feed];}
            }
            ++acc_feed;
        }
        if(!booted&&clocks.core_rises()>=8&&clocks.service_rises()>=8){''')
    replace('        if (next_stage) {', '        if (next_stage && clock_event.core_rise()) {')
    # rm_layer must be updated before the decoder-only slot guard, and head
    # launch must wait for the final held draft load edge, not merely its drive.
    replace('            auto tp = std::chrono::steady_clock::now();', '''            if(acc_feed!=acc_toks.size())fatal("HEAD before actual draft loader complete");
            auto tp = std::chrono::steady_clock::now();''')
    replace('                load_images(mem[d], stages[cur].dir[d],stages[cur].layer>=0);', '''                die[d]->rm_layer=uint8_t(stages[cur].layer);
                load_images(mem[d], stages[cur].dir[d],stages[cur].layer>=0);''')
    replace('                die[d]->h_start = 1;\n                layer_fences[d].begin', '''                die[d]->h_start = 1;
                if(accept_commit && stages[cur].layer<0){die[d]->acc_commit_en=1;die[d]->acc_arm=1;}
                layer_fences[d].begin''')
    replace('                    return 0;', '                    fflush(stdout);\n                    return 0;')
    replace('QWEN_ROM_NEARBASELINE PASS stages=%zu',
            'QWEN_DSPARK_NEAR_COMPONENT_DONE stages=%zu')
    return '// Actual opt-in '+TOP+' component host; no full-token/timing qualification.\n'+src


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    with a.out.open('x') as f:f.write(emit())
