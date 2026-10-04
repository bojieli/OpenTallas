#pragma once
#include "s81_minimum_tp4_gather.hpp"
#include "s81_minimum_prefix_providers.hpp"

// Concrete factory join into the existing runtime/SourceIo/TAG227 publisher.
// These are references to the FOUR real rank owners, not a new ownership ABI.
// Cicero retains them and their VM participants for the whole native run.
inline DsromS81NativeGather dsrom_s81_attach_native_tp4_gather(
    DsromS81MinimumRuntime& clock_owner,uint64_t identity,
    const std::array<std::reference_wrapper<DsromS81MinimumRuntime>,4>& ranks,
    const std::array<std::reference_wrapper<dsrom_s81_minimum::PrefixPublication>,4>& publications,
    const std::array<DsromS81MinimumSourceIo,4>& actual_io,
    const std::array<std::function<bool(unsigned literal_wait_mask)>,4>& actual_wait) {
    if(!clock_owner.context||!clock_owner.cycle||identity>=(1ull<<47))
        throw std::runtime_error("native gather factory requires actual shared clock/context");
    for(unsigned rank=0;rank<4;rank++) {
        const auto& r=ranks[rank].get();
        if(r.rank!=int(rank)||r.stage!=0||r.context!=clock_owner.context||!r.cycle||
           !actual_wait[rank]||!actual_io[rank].read_word||!actual_io[rank].span_lease||
           !actual_io[rank].offer||!actual_io[rank].visible)
            throw std::runtime_error("gather factory lacks literal L0 actual rank VM/wait binding");
        for(unsigned prior=0;prior<rank;prior++)
            if(&ranks[prior].get()==&r||&publications[prior].get()==&publications[rank].get())
                throw std::runtime_error("rank0 alias is not a native TP4 source/publication");
        // Source enrollment creates neither payload nor input lease or ACK.
        publications[rank].get().enroll_literal(9,{{51648,4*320}});
        publications[rank].get().enroll_literal(10,{{54208,4*128}});
    }
    for(const auto& p:clock_owner.participants)
        if(p.name=="native-TP4-I9-I10-gather")
            throw std::runtime_error("native gather already registered on shared clock");
    auto checked_context=[ranks,actual_wait,identity](unsigned pc) {
        if(pc!=9&&pc!=10)throw std::runtime_error("only literal L0 I9/I10 enrolled");
        for(unsigned rank=0;rank<4;rank++) {
            const auto& r=ranks[rank].get();
            if(!r.identity||*r.identity!=identity||!actual_wait[rank](31))
                throw std::runtime_error("gather lacks actual held rank context/wait31");
        }
    };
    auto provider=dsrom_s81_bind_native_tp4_gather(clock_owner,identity,actual_io,
        [checked_context,publications,identity](unsigned rank,unsigned pc) {
            checked_context(pc); // check again at real pre-edge GO, not just start
            publications[rank].get().begin(identity,pc);
        },
        [ranks,publications](unsigned rank,unsigned pc,const S81EmbeddingOutput& native) {
            // This is the actual accepted transpose output, ONCE per scalar.
            // The SAME immutable tag ledger is later advanced by native VM
            // acceptance/ACK callbacks, not by this reservation/capture.
            for(unsigned lane=0;lane<16;lane++)
                dsrom_s81_capture_minimum_prefix_scalar(
                    ranks[rank].get(),publications[rank].get(),pc,native,lane,true);
        });
    const auto native_start=provider.start;
    auto current_pc=std::make_shared<unsigned>(0);
    provider.start=[native_start,checked_context,current_pc](unsigned pc){
        checked_context(pc);native_start(pc);*current_pc=pc;
    };
    const auto native_complete=provider.complete;
    provider.complete=[native_complete,publications,identity,current_pc]() {
        if(!native_complete())return false;
        if(*current_pc!=9&&*current_pc!=10)return false;
        for(const auto& p:publications)
            if(!p.get().complete(identity,*current_pc))return false;
        return true;
    };
    clock_owner.participants.push_back(provider.participant); // ONE clock owner
    return provider;
}
