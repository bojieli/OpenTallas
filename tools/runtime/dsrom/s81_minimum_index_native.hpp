#pragma once
#include "s81_minimum_index_participant.hpp"
#include "VDsromS81IndexScorer.h"
#include "VDsromS81IndexSelector.h"
#include <memory>

// Explicit factory for Arendt's already-built production units. Construct four
// instances before the ONE shared cold_start; the enclosing factory retains
// their actual HBM, source-memory and publication owners. No library build or
// clock is performed here. I45 local512 only; I50 K2048 and I93 FP32 require
// their own source-selected providers and cannot be admitted through this API.
namespace dsrom_s81_minimum {
class NativeIndexRank {
public:
    using Ports=NativeIndexParticipant<VDsromS81IndexScorer,VDsromS81IndexSelector>;
    using NativeJoin=std::function<void(unsigned,VDsromS81IndexScorer&,VDsromS81IndexSelector&)>;
    using Offer=std::function<bool(unsigned,const Ports::SelectionWrite&)>;
    using Visible=std::function<bool(unsigned,const Ports::SelectionWrite&)>;
    using Fence=std::function<bool(unsigned)>;
private:
    unsigned rank;
    NativeJoin join;
    Offer offer;
    Visible visible;
    Fence fence;
    VDsromS81IndexScorer scorer;
    VDsromS81IndexSelector selector;
    Ports ports;
public:
    NativeIndexRank(DsromS81MinimumRuntime& runtime,unsigned actual_rank,
        NativeJoin actual_port_join,Offer actual_vm_offer,
        Visible actual_vm_visible,Fence actual_source_history_fence)
    :rank(actual_rank),join(std::move(actual_port_join)),offer(std::move(actual_vm_offer)),
     visible(std::move(actual_vm_visible)),fence(std::move(actual_source_history_fence)),
     scorer(runtime.context,("s81_index_rank"+std::to_string(rank)).c_str()),
     selector(runtime.context,("s81_local_select_rank"+std::to_string(rank)).c_str()),
     ports(runtime,scorer,selector,[this]{join(rank,scorer,selector);},
         [this](const auto& w){return offer(rank,w);},
         [this](const auto& w){return visible(rank,w);},[this]{return fence(rank);}) {
        if(rank>=4||!runtime.context||runtime.identity||!join||!offer||!visible||!fence||
           scorer.contextp()!=runtime.context||selector.contextp()!=runtime.context)
            throw std::runtime_error("index rank requires cold same-context actual port owners");
        scorer.clk=0;selector.clk=0;scorer.rst_n=0;selector.rst_n=0;
        scorer.go=0;selector.go=0;
    }
    VDsromS81IndexScorer& native_scorer(){return scorer;}
    VDsromS81IndexSelector& native_selector(){return selector;}
    void arm(uint64_t identity,uint32_t actual_selection_base){ports.arm(identity,actual_selection_base);}
    bool rank_selection_visible()const{return ports.rank_selection_visible();}
    const Ports::Counters& counters()const{return ports.counters();}
    DsromS81MinimumParticipant participant() {
        auto p=ports.participant();p.name+="-rank"+std::to_string(rank);return p;
    }
};
}
