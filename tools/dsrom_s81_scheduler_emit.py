#!/usr/bin/env python3
"""Emit the executable caller hook using the selected native S81 host loop.

Model archives are supplied by Arch's sole hierarchical build. This emits C++
only: no model generation, model make, simulation, golden or input preparation.
"""
import argparse
from pathlib import Path

HOST = 'rtl/test/v41_runtime/s81_selected/w17_current_fastpp_c8_s81_rt.cpp'


def emit(owner, out, *, wavefront=False):
    owner, out = Path(owner).resolve(), Path(out)
    source = (owner / HOST).read_text()
    # Retain the exact selected DieBase API for both the runtime and caller DSO.
    start = source.index('struct DieBase {')
    end = source.index('\ntemplate <class DIE> struct Die', start)
    base = source[start:end]
    for hook in ['c8_workspace_write', 'capture_visible', 'c8_context', 'c8_retired']:
        if hook not in base:
            raise ValueError('selected actual native interface missing: '+hook)
    header = '''#pragma once
#if !defined(DSROM_C8_S81) || DSROM_C8_S81 != 1
#error "source caller and native runtime must both select DSROM_C8_S81=1"
#endif
#include <cstdint>
#include <vector>
#include <functional>
#include <string>
'''+base+'''
// Rank-local native models; physical stage/rank identity stays with the source
// descriptors and DsromC8SourceDispatch. The caller owns all source leases.
struct DsromS81Runtime {
    int stage;
    std::vector<DieBase*> dies;
    std::function<void()> tick;
    std::function<long()> cycle;
    // These are only the native host's transport queues, not a VM/lease fence.
    std::function<bool()> links_empty;
};
// The actual source caller implements this exported entry. It consumes its
// existing dispatch/saved context and actual visibility callbacks directly.
using DsromS81SourceMain = int (*)(DsromS81Runtime&, const char* output);
extern "C" int dsrom_s81_source_main(DsromS81Runtime&, const char* output);
'''
    native = source[:start]+'#include "dsrom_s81_scheduler_api.hpp"\n'+source[end:]
    if wavefront:
        native='#include "s81_wavefront_native_result_read.hpp"\n'+native
        # Bind the existing typed join while DIE is still known. DieBase and
        # the caller DSO ABI remain unchanged; there is no default provider.
        anchor='    Die(RtPool& pool, const std::string& dir, int id_, int argc, const char** argv) : id(id_) {'
        if native.count(anchor)!=1:
            raise ValueError('typed selected Die constructor changed')
        native=native.replace(anchor,r'''
    std::function<void()> wave_prepare,wave_sample,wave_after,wave_quarantine;
    std::function<void()> result_sample,result_after,result_quarantine;
    bool wave_sampled=false,wave_armed=false,result_sampled=false;
    template<class Reader> void bind_native_result_read(std::shared_ptr<Reader> reader) {
        if(result_sample||!reader||d->clk||d->rst_n)
            throw std::runtime_error("HEAD result needs actual cold typed reader");
        // The existing reader retains the accepted offer, native producer/END
        // PCs and sequence. It never grants the poller's enclosing fences.
        result_sample=[reader](){reader->sample_before_edge();};
        result_after=[reader](){reader->after_edge();};
        result_quarantine=[reader](){reader->warm_quarantine();};
    }
    auto bind_native_head_terminal(DsromS81NativeResultTerminal terminal,uint64_t sequence) {
        if(terminal.source_node!="Lhead.I6"||terminal.offer.die_id%4!=id||
           unsigned(terminal.producer_pc)+1!=unsigned(terminal.end_pc))
            throw std::runtime_error("HEAD requires actual accepted compute home and released I5/I6 PCs");
        auto reader=dsrom_s81_bind_native_result_read(*this,std::move(terminal),sequence,true);
        bind_native_result_read(reader);
        return reader; // SAME reader supplies existing stage poller's ReadResult
    }
    template<class Join> void bind_native_wave(std::shared_ptr<Join> joined,
        std::function<void()> before_edge,std::function<void()> sample_before_edge,
        std::function<void()> after_edge) {
        if(wave_prepare||!joined||!before_edge||!sample_before_edge||!after_edge||d->clk||d->rst_n)
            throw std::runtime_error("WAVE needs actual cold typed join and stage callbacks");
        // These are the existing poller composition callbacks: before owns
        // Join.drive, and after owns Poller.after_edge then Join.after_edge.
        // Calling Join again here would duplicate acceptance and retirement.
        wave_prepare=[joined,before_edge](){before_edge();};
        wave_sample=[joined,sample_before_edge](){sample_before_edge();};
        wave_after=[joined,after_edge](){after_edge();};
        wave_quarantine=[joined](){joined->warm_quarantine();};
    }
    template<class Binding> void bind_native_wave(const Binding& bound) {
        if(!bound.warm_quarantine)
            throw std::runtime_error("WAVE composition must retain poller and ledger quarantine");
        bind_native_wave(bound.join,bound.before_edge,bound.sample_before_edge,bound.after_edge);
        // The composition owns BOTH existing poller and external ledger debt.
        // Quarantining only Join would leave that enclosing owner runnable.
        wave_quarantine=bound.warm_quarantine;
    }
    void arm_native_wave() {wave_armed=bool(wave_prepare)||bool(result_sample);}
    void finish_native_wave_edge() {
        // Native END and its actual C8 retirement are observed before the
        // stage poller reads the held result on this same accepted edge.
        if(result_sampled) {
            if(!d->clk||!d->rst_n)throw std::runtime_error("HEAD result sampled edge lost");
            result_after();result_sampled=false;
        }
        if(wave_sampled) {
            if(!d->clk||!d->rst_n)throw std::runtime_error("WAVE sampled edge lost");
            wave_after();wave_sampled=false;
        }
    }
'''+anchor)
        edge='    void set_inputs(uint8_t clk, uint8_t rst) override {'
        if native.count(edge)!=1:
            raise ValueError('actual shared edge hook changed')
        native=native.replace(edge,edge+r'''
        if(wave_armed&&clk&&rst) {
            if(d->clk||wave_sampled||result_sampled)throw std::runtime_error("WAVE edge sampled twice");
            if(!d->rst_n){d->rst_n=1;d->eval();}
            if(wave_prepare)wave_prepare();
            d->eval(); // LOW settle; no new clock
            if(wave_sample){wave_sample();wave_sampled=true;}
            if(result_sample){result_sample();result_sampled=true;}
        } else if(wave_armed&&!rst&&d->rst_n) {
            if(result_quarantine)result_quarantine();
            if(wave_quarantine)wave_quarantine();
            throw std::runtime_error("WAVE warm reset retains accepted stage debt");
        }
''')
    # Include the selected host as a library. Its singleton main is excluded.
    first = source.index('    int threads = 16;', source.index('#ifndef DSROM_C8_LIBRARY'))
    last = source.index('    // window priming', first)
    loop = source[first:last]
    if wavefront:
        # The committed caller constructed directly into DieBase storage.
        # Retain typed owners first rather than depending on another WIP host.
        old='\n'.join('    dies.emplace_back(new Die<Vdie'+str(r)+
            '>(pool, root + "/r'+str(r)+'", '+str(r)+', 3, av['+str(r)+'].data()));'
            for r in range(4))
        if old in loop:
            typed='\n'.join('    auto native_rank'+str(r)+'=std::make_unique<Die<Vdie'+str(r)+
                '>>(pool, root + "/r'+str(r)+'", '+str(r)+', 3, av['+str(r)+'].data());'
                for r in range(4))
            erased='\n'.join('    dies.emplace_back(std::move(native_rank'+str(r)+'));' for r in range(4))
            loop=loop.replace(old,typed+'\n'+erased)
        erase='    dies.emplace_back(std::move(native_rank0));'
        if loop.count(erase)!=1:
            raise ValueError('typed four-rank construction/erasure changed')
        loop=loop.replace(erase,r'''
#ifndef DSROM_S81_BIND_TYPED_WAVE_CALLER
#error "selected WAVE requires actual source/poller/RESULT binder before Die erasure"
#endif
    // runtime exists in this scope. Borrow all four actual models and retain
    // the source callbacks before moving their owners into DieBase storage.
    const std::function<int(const char*)> wave_source_main=
        DSROM_S81_BIND_TYPED_WAVE_CALLER(runtime,*native_rank0,*native_rank1,*native_rank2,*native_rank3);
    if(!wave_source_main)
        throw std::runtime_error("typed WAVE binder omitted whole-stage caller");
    if(!native_rank0->wave_prepare)
        throw std::runtime_error("typed WAVE binder omitted actual rank0 source join");
    const std::array<std::function<void()>,4> wave_arm={
        [p=native_rank0.get()](){p->arm_native_wave();},
        [p=native_rank1.get()](){p->arm_native_wave();},
        [p=native_rank2.get()](){p->arm_native_wave();},
        [p=native_rank3.get()](){p->arm_native_wave();}};
    const std::array<std::function<void()>,4> wave_finish={
        [p=native_rank0.get()](){p->finish_native_wave_edge();},
        [p=native_rank1.get()](){p->finish_native_wave_edge();},
        [p=native_rank2.get()](){p->finish_native_wave_edge();},
        [p=native_rank3.get()](){p->finish_native_wave_edge();}};
'''+erase)
        if loop.count('        link_step();')!=1:
            raise ValueError('shared all-rank rising boundary changed')
        loop=loop.replace('        link_step();',
            '        // All native rising evaluations completed; still HIGH.\n'
            '        for(const auto& finish:wave_finish)finish();\n'
            '        link_step();')
    # maxc/wrong-edge/watchdog controls are outside this retained section.
    if 'maxc' in loop:
        raise ValueError('unexpected singleton deadline in selected clock loop')
    append = r'''
#include <dlfcn.h>
int main(int argc,char** argv) {
    if(argc!=4){fprintf(stderr,"usage: s81_c8_scheduler IMGROOT OUTPUT ACTUAL_SOURCE_CALLER.so\n");return 2;}
    std::string root=argv[1],out=argv[2];
    bool wrong=false; // use only the selected native pre-edge ordering
    void* caller=dlopen(argv[3],RTLD_NOW|RTLD_LOCAL);
    if(!caller){fprintf(stderr,"source caller load failed: %s\n",dlerror());return 2;}
    auto source_main=reinterpret_cast<DsromS81SourceMain>(dlsym(caller,"dsrom_s81_source_main"));
    if(!source_main){fprintf(stderr,"actual source caller entry missing: %s\n",dlerror());return 2;}
    try {
        DsromS81Runtime runtime{};
        const char* stage=getenv("DSROM_S81_STAGE");
        if(!stage)throw std::runtime_error("actual native stage required");
        runtime.stage=std::stoi(stage);
'''+loop+r'''
        for(auto& die:dies)runtime.dies.push_back(die.get());
        runtime.tick=[&](){
            tick();
            for(auto& die:dies){
                die->c8_observe(cyc);
                if(die->fault())throw std::runtime_error("actual native die fault");
            }
        };
        runtime.cycle=[&](){return cyc;};
        runtime.links_empty=[&](){
            for(auto& r:rx)if(!r.u.q.empty()||!r.x[0].q.empty()||!r.x[1].q.empty())return false;
            for(auto& row:ckv_q)for(auto& q:row)if(!q.empty())return false;
            return true;
        };
        // No automatic offer, restored, priming or expected-state injection.
        // Caller drives native C8/context/prime through the retained DieBase.
        int rc=source_main(runtime,out.c_str());
        printf("SOURCE_CALLER_EXIT rc=%d cycle=%ld\n",rc,cyc);
        // Runtime observers may retain source-SO closures. Keep that image
        // loaded through their destruction, rather than unloading their code.
        return rc;
    }catch(const std::exception& e){
        fprintf(stderr,"S81_SOURCE_RUNTIME_ERROR %s\n",e.what());
        return 1;
    }
}
'''
    if wavefront:
        append=append.replace('        int rc=source_main(runtime,out.c_str());',
            '        for(const auto& arm:wave_arm)arm();\n'
            '        // WAVE owns admission; do not also issue blocking C8 groups.\n'
            '        int rc=wave_source_main(out.c_str());')
    defines = '#define DSROM_C8_LIBRARY 1\n#define DSROM_C8_S81 1\n#define DSROM_S81_CAPTURE 1\n'
    out.mkdir(parents=True, exist_ok=False)
    (out/'dsrom_s81_scheduler_api.hpp').write_text(header)
    (out/'s81_c8_scheduler.cpp').write_text(defines+native+append)
    # Actual source helpers, unchanged; both runtime and source caller see the
    # same native vtable and the already integrated restore/drain dispatch.
    for relative in ['rtl/test/v41_runtime/dsrom_c8_source_dispatch.hpp',
                     'rtl/test/v41_runtime/s81_selected/dsrom_s81_workspace.hpp',
                     'rtl/test/v41_runtime/s81_selected/dsrom_s81_rom_client.hpp']:
        (out/Path(relative).name).write_bytes((owner/relative).read_bytes())
    (out/'dsrom_s81_source_scheduler.hpp').write_text(SOURCE_SCHEDULER)
    # The actual executable caller and its VM-carry integration are support
    # sources; they need not be present in the immutable native-model owner.
    support = Path(__file__).resolve().parent/'runtime/dsrom'
    for name in ['s81_source_caller.cpp', 's81_source_caller_plan.hpp', 's81_source_receipts.cpp',
                 's81_source_caller_hooks.hpp', 's81_wavefront_c8_group_step.hpp',
                 's81_wavefront_c8_port_join.hpp', 's81_wavefront_stage_poller.hpp',
                 's81_wavefront_result_ledger.hpp', 's81_wavefront_native_result_read.hpp']:
        (out/name).write_bytes((support/name).read_bytes())
    return out/'s81_c8_scheduler.cpp'


SOURCE_SCHEDULER = r'''#pragma once
#include "dsrom_s81_scheduler_api.hpp"
#include "dsrom_c8_source_dispatch.hpp"
#include "s81_wavefront_c8_group_step.hpp"
#include "dsrom_s81_workspace.hpp"

// The source caller owns the selected program entry and physical die. All
// restoration and drain decisions are the original caller's actual callbacks.
template<class Restore,class Drain>
void dsrom_s81_run_offer(DsromS81Runtime& runtime,const DsromC8SourceOffer& offer,
                        Restore& restore,Drain& drain) {
    if(offer.die_id<0 || offer.die_id>=324 || runtime.dies.size()!=4 || offer.die_id/4!=runtime.stage)
        throw std::runtime_error("actual S81 source offer owner");
    DieBase& die=*runtime.dies.at(offer.die_id%4);
    DsromC8SourceDispatch dispatch(offer);
    while(!dispatch.complete()) {
        if(die.fault())throw std::runtime_error("source dispatch native fault");
        dispatch.before_edge(die,offer.die_id,restore,drain);
        if(dispatch.complete())break;
        runtime.tick();
        dispatch.accepted_edge();
    }
}

// Drive all TP4 ranks before the same edge. A serial rank-at-a-time launch
// would deadlock native collectives and is not the selected group schedule.
template<class Restore,class Drain>
void dsrom_s81_run_group(DsromS81Runtime& runtime,const std::vector<DsromC8SourceOffer>& offers,
                        Restore& restore,Drain& drain) {
    if(offers.size()!=4 || runtime.dies.size()!=4)
        throw std::runtime_error("actual TP4 source offer group required");
    std::array<DsromC8SourceOffer,4> group{{offers[0],offers[1],offers[2],offers[3]}};
    DsromS81C8GroupStep step(group);
    // Same accepted-event semantics as the old blocking loop. A WAVE caller
    // can use step.before_edge/after_edge directly to service other providers
    // around the SAME edge without a recursive runtime.tick().
    while(step.before_edge(runtime,restore,drain)) {
        runtime.tick();
        step.after_edge();
    }
}

// A carried span uses the native source.vm_word and destination workspace
// writer. setup_complete alone never substitutes for restore/VM visibility.
template<class SourceVisibility,class InputVisibility>
bool dsrom_s81_restore_carry(DsromS81Runtime& source_runtime,DsromS81Runtime& target_runtime,
                            DsromS81Workspace& workspace,
                            int source_die,int target_die,const DsromC8SourceOffer& offer,
                            SourceVisibility& source_visible,InputVisibility& input_visible) {
    if(target_die!=offer.die_id || workspace.identity()!=offer.identity ||
       source_die<0 || source_die>=324 || target_die<0 || target_die>=324)
        throw std::runtime_error("native workspace source/target context mismatch");
    // Cross-stage producers use their actual runtime instance, never rank%4
    // on the destination group's models or an expected-activation substitute.
    if(source_die/4!=source_runtime.stage || target_die/4!=target_runtime.stage)
        throw std::runtime_error("workspace runtime stage owner mismatch");
    if(!workspace.capture(*source_runtime.dies.at(source_die%4),source_die,source_visible))return false;
    workspace.load(*target_runtime.dies.at(target_die%4),target_die,1u<<19);
    return workspace.setup_complete() && input_visible(offer);
}
'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--owner',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--wavefront',action='store_true',help='require typed WAVE/C8 source binder before erasure')
    a=p.parse_args();print(emit(a.owner,a.out,wavefront=a.wavefront))


if __name__ == '__main__':
    main()
