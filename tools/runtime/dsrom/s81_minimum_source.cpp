#include "s81_minimum_source_plan.hpp"
#include "Vnative_vm.h"
#include <cstdio>
#include <filesystem>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace {
template<class Function,class Keep> void retain(Function& function,const Keep& keep) {
    if(!function)return;
    auto original=std::move(function);
    function=[original=std::move(original),keep](auto&&... args)->decltype(auto) {
        return original(std::forward<decltype(args)>(args)...);
    };
}
}

extern "C" int dsrom_s81_minimum_source_main(DsromS81MinimumRuntime& runtime,const char* output) {
    if(runtime.stage<0||runtime.stage>=81||runtime.rank<0||runtime.rank>=4||
       !runtime.context||!runtime.tick||!runtime.cold_start||
       !runtime.bind_context||!runtime.result||!runtime.cycle)
        throw std::runtime_error("actual selected S81 native runtime required");
    auto vm=std::make_shared<Vnative_vm>(runtime.context,"source_native_vm");
    // Factory owns actual participant resources and literal selected context,
    // source CFG/ROM and native prefix/return/capture/endpoint event binding.
    auto plan=std::make_shared<DsromS81MinimumSourcePlan>(
        dsrom_s81_bind_minimum_source(runtime,vm));
    const bool seeded=plan->position==1048575;
    // Canonical L20's real field/service allocation is stage37. TRACE_STAGE
    // annotations never authorize starting at an unrelated source context.
    if((seeded&&runtime.stage!=37)||(!seeded&&runtime.stage!=0))
        throw std::runtime_error("source plan and actual canonical stage differ");
    if((seeded?(!plan->attach_seeded||!plan->initialize_seeded||!plan->seeded_inputs_visible):!plan->attach)||
       !plan->begin_prefix||!plan->advance||!plan->complete||plan->token>=129280||
       (seeded?plan->token!=16754:plan->position!=0)||plan->identity>=(1ull<<47))
        throw std::runtime_error("actual minimum source plan/input/publication providers required");
    std::shared_ptr<DsromS81MinimumEmbedding> embedding;
    if(seeded) {
        plan->attach_seeded();
    }else {
        embedding=std::make_shared<DsromS81MinimumEmbedding>(runtime,
            plan->embedding_library,plan->embedding_socket,plan->token,plan->position,
            plan->identity,plan->vm_base,plan->embedding_sink);
        auto embedding_participant=std::move(runtime.participants.back());
        runtime.participants.pop_back();
        runtime.participants.insert(runtime.participants.begin(),std::move(embedding_participant));
        plan->attach(*embedding);
    }
    if(runtime.participants.size()<2||!runtime.publication_ready||!runtime.publication_drained)
        throw std::runtime_error("actual source providers must attach before shared cold reset");
    auto keep=std::make_tuple(vm,plan,embedding);
    // Host checks drain after this function returns. Retain model/factory
    // ownership in every callback that can survive the source entry stack.
    for(auto& participant:runtime.participants) {
        retain(participant.prepare,keep);retain(participant.rising,keep);
        retain(participant.falling,keep);retain(participant.fault,keep);
    }
    retain(runtime.publication_ready,keep);retain(runtime.publication_drained,keep);
    runtime.cold_start();
    runtime.bind_context(plan->identity);
    const long input_start=runtime.cycle();
    if(seeded) {
        plan->initialize_seeded();
        while(!plan->seeded_inputs_visible())runtime.tick();
    }else {
        embedding->start();
        while(!embedding->complete())runtime.tick();
    }
    const long input_end=runtime.cycle();
    plan->begin_prefix();
    while(!plan->complete()) {
        plan->advance();
        runtime.tick();
    }
    // The selected component's actual publication authority is checked
    // independently of arithmetic quiet. A factory cannot turn bank-local zero
    // into retirement of unproduced roots or whole-C8/all-copy authority.
    if(!runtime.publication_drained(plan->identity)||!runtime.result().quiet)
        throw std::runtime_error("source terminal precedes native field/context publication drain");
    if(plan->position==1048575&&!plan->write_measurements)
        throw std::runtime_error("target L20 terminal lacks actual native measurement exporter");
    if(plan->write_measurements)plan->write_measurements(output);
    const auto path=std::filesystem::path(output)/"native_source_component.tsv";
    FILE* journal=fopen(path.c_str(),"wx");
    if(!journal)throw std::runtime_error("preserve existing native source stage results");
    const int wrote=fprintf(journal,"scope\tstage\trank\tpair\tidentity\ttoken\tinput_start\tinput_end\tinput_words\tterminal_cycle\n"
        "%s\t%d\t%d\t%d\t%llu\t%u\t%ld\t%ld\t%u\t%ld\n",
        seeded?"L20.seeded-native-component":"L0.I7-component-rows0,1",
        runtime.stage,runtime.rank,runtime.pair,(unsigned long long)plan->identity,
        plan->token,input_start,input_end,seeded?20480u:embedding->committed_words(),runtime.cycle());
    const int closed=fclose(journal);
    if(wrote<0||closed)throw std::runtime_error("native source stage result write failed");
    return 0;
}
