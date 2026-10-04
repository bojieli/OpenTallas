#pragma once
#include "s81_minimum_l20_collective.hpp"
#include "s81_minimum_prefix_providers.hpp"

inline DsromS81PrefixNativeEngine dsrom_s81_attach_native_l20_collective(
    DsromS81MinimumRuntime& clock_owner,uint64_t identity,
    const std::array<std::reference_wrapper<DsromS81MinimumRuntime>,4>& ranks,
    const std::array<std::reference_wrapper<dsrom_s81_minimum::PrefixPublication>,4>& publications,
    const std::array<DsromS81MinimumSourceIo,4>& io,
    const std::array<std::function<bool(unsigned)>,4>& actual_wait,
    bool opt_in=false) {
    if(!opt_in)throw std::runtime_error("L20 collective defaults OFF");
    for(unsigned rank=0;rank<4;rank++) {
        const auto& r=ranks[rank].get();
        if(r.rank!=int(rank)||r.context!=clock_owner.context||!r.cycle||!actual_wait[rank])
            throw std::runtime_error("L20 collective requires four actual shared-clock rank owners");
        for(unsigned prior=0;prior<rank;prior++)
            if(&ranks[prior].get()==&r||&publications[prior].get()==&publications[rank].get())
                throw std::runtime_error("L20 collective rank/publication alias");
    }
    for(const auto& p:clock_owner.participants)
        if(p.name=="native-L20-nonTOPK-TP4")
            throw std::runtime_error("L20 collective already registered");
    auto allowed=[ranks,actual_wait,identity]() {
        for(unsigned rank=0;rank<4;rank++) {
            const auto& r=ranks[rank].get();
            if(!r.identity||*r.identity!=identity||!actual_wait[rank](31))return false;
        }
        return true;
    };
    auto engine=dsrom_s81_bind_native_l20_collective(clock_owner,identity,io,
        [allowed,publications,identity](unsigned rank,unsigned pc) {
            if(!allowed())throw std::runtime_error("L20 collective lost actual wait31/context at GO");
            publications[rank].get().begin(identity,pc);
        },
        [ranks,publications](unsigned rank,unsigned pc,const S81EmbeddingOutput& out) {
            for(unsigned lane=0;lane<16;lane++)
                dsrom_s81_capture_minimum_prefix_scalar(ranks[rank].get(),publications[rank].get(),pc,out,lane,true);
        },true);
    for(const auto& item:dsrom_s81_l20_collective_literals())
        for(const auto& p:publications)
            p.get().enroll_literal(item.operation.index,{{item.dst,item.mode?4*item.n:item.n}});
    auto ready=engine.ready;
    engine.ready=[allowed,ready](){return allowed()&&ready();};
    auto inputs=engine.inputs_ready;
    engine.inputs_ready=[allowed,inputs](const auto& op){return allowed()&&inputs(op);};
    auto native_idle=engine.idle;
    auto current=std::make_shared<unsigned>(0);
    auto drive=engine.drive;
    engine.drive=[drive,current,allowed](const auto& op,bool go) {
        if(go&&!allowed())throw std::runtime_error("L20 collective GO without actual rank wait31");
        drive(op,go);if(go)*current=op.index;
    };
    engine.idle=[native_idle,current,publications,identity]() {
        if(!native_idle())return false;
        if(!*current)return true;
        for(const auto& p:publications)if(!p.get().complete(identity,*current))return false;
        return true;
    };
    // Return the existing engine to Arch's dispatcher. If the dispatcher
    // nests participant callbacks, do NOT also register them on the runtime.
    // A standalone caller may register engine.participant exactly once.
    return engine;
}
