#!/usr/bin/env python3
"""Emit the executable caller hook using the selected native S81 host loop.

Model archives are supplied by Arch's sole hierarchical build. This emits C++
only: no model generation, model make, simulation, golden or input preparation.
"""
import argparse
from pathlib import Path

HOST = 'rtl/test/v41_runtime/s81_selected/w17_current_fastpp_c8_s81_rt.cpp'


def emit(owner, out):
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
    # Include the selected host as a library. Its singleton main is excluded.
    first = source.index('    int threads = 16;', source.index('#ifndef DSROM_C8_LIBRARY'))
    last = source.index('    // window priming', first)
    loop = source[first:last]
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
    for name in ['s81_source_caller.cpp', 's81_source_caller_plan.hpp',
                 's81_source_caller_hooks.hpp']:
        (out/name).write_bytes((support/name).read_bytes())
    return out/'s81_c8_scheduler.cpp'


SOURCE_SCHEDULER = r'''#pragma once
#include "dsrom_s81_scheduler_api.hpp"
#include "dsrom_c8_source_dispatch.hpp"
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
    std::vector<DsromC8SourceDispatch> dispatches;
    bool ranks[4]={false,false,false,false};
    for(const auto& offer:offers) {
        if(offer.die_id<0 || offer.die_id>=324 || offer.die_id/4!=runtime.stage ||
           ranks[offer.die_id%4] || offer.identity!=offers[0].identity || offer.token!=offers[0].token)
            throw std::runtime_error("source TP4 owner/context group mismatch");
        ranks[offer.die_id%4]=true;dispatches.emplace_back(offer);
    }
    for(;;) {
        bool complete=true;
        for(size_t i=0;i<offers.size();i++)if(!dispatches[i].complete()) {
            auto& die=*runtime.dies.at(offers[i].die_id%4);
            if(die.fault())throw std::runtime_error("source group native fault");
            dispatches[i].before_edge(die,offers[i].die_id,restore,drain);
            complete &= dispatches[i].complete();
        }
        if(complete)return;
        runtime.tick();
        for(auto& dispatch:dispatches)dispatch.accepted_edge();
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
    a=p.parse_args();print(emit(a.owner,a.out))


if __name__ == '__main__':
    main()
