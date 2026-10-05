#pragma once
#include "s81_wavefront_c8_port_join.hpp"
#include <memory>
#include <string>
#include <type_traits>

// The actual emitted terminal source node/entry and producer+END instruction PCs.
// Arch must bind this from its complete native source plan, not FIELD+END alone.
struct DsromS81NativeResultTerminal {
    DsromC8SourceOffer offer;
    std::string source_node;
    uint16_t producer_pc,end_pc;
};

template<class Top> class DsromS81WaveNativeResultRead {
    Top& top;
    const DsromS81NativeResultTerminal terminal;
    const uint64_t sequence;
    bool enabled,prepared=false,stopped=false,fresh=false,retired=false;
    bool producer=false,end=false,scope=false;
    uint16_t pc=0;
    std::optional<DsromS81WaveStageResult> held;
    static void require(bool b,const char* why){if(!b)throw std::runtime_error(why);}
    bool same_scope()const {
        return uint64_t(top.native_result_identity)==terminal.offer.identity&&
               uint32_t(top.native_result_entry)==terminal.offer.entry;
    }
    void healthy()const {
        require(!stopped&&!top.fault&&!top.c8_stage_quarantine&&
                !top.c8_write_quarantine&&!top.c8_write_fault,"native result reader fault/quarantine");
    }
    static bool same_offer(const DsromC8SourceOffer& a,const DsromC8SourceOffer& b) {
        return a.die_id==b.die_id&&a.identity==b.identity&&a.token==b.token&&a.position==b.position&&
               a.user==b.user&&a.epoch==b.epoch&&a.entry==b.entry;
    }
public:
    DsromS81WaveNativeResultRead(Top& native,DsromS81NativeResultTerminal actual_terminal,
                               uint64_t accepted_request_sequence,bool enable=false):
        top(native),terminal(std::move(actual_terminal)),sequence(accepted_request_sequence),enabled(enable) {
        DsromC8SourceDispatch checked(terminal.offer);
        require(!terminal.source_node.empty()&&terminal.producer_pc<(1u<<14)&&terminal.end_pc<(1u<<14)&&
                terminal.offer.entry<=terminal.producer_pc&&terminal.producer_pc<terminal.end_pc,
                "actual terminal source producer/entry/END required");
        if(enabled)require(top.native_result_selected,"native result output adapter default off");
    }
    // Enclosing caller: settle native model -> sample_before_edge -> ONE real
    // rising edge/settle -> after_edge. No private tick, eval or reset here.
    void sample_before_edge() {
        if(!enabled)return;
        try {
            healthy();require(!prepared&&top.rst_n,"native result edge reused/reset");
            scope=same_scope()&&bool(top.native_result_active);
            producer=scope&&bool(top.native_result_producer_take);
            end=scope&&bool(top.native_result_end_take);pc=uint16_t(top.native_result_pc);
            if(end)require(pc==terminal.end_pc&&fresh&&top.native_result_am_any,
                           "terminal END has no fresh bound native argmax producer");
            prepared=true;
        }catch(...){stopped=true;throw;}
    }
    void after_edge() {
        if(!enabled)return;
        try {
            healthy();require(prepared&&top.rst_n,"native result edge not sampled/reset");
            if(producer) {
                require(!held,"native producer overwrote retained terminal output");
                // An intervening argmax from another instruction invalidates provenance.
                fresh=(pc==terminal.producer_pc);
            }
            if(end) {
                require(!held&&same_scope()&&top.native_result_done,"native terminal END did not complete");
                const uint32_t token=top.native_result_token;
                require(token<(1u<<21),"native terminal token bounds");
                held=DsromS81WaveStageResult{sequence,terminal.offer.identity,token,uint32_t(top.native_result_value)};
            }
            if(held&&top.c8_retire_v&&uint64_t(top.c8_retire_identity)==terminal.offer.identity) {
                require(same_scope(),"native terminal retirement belongs to another entry");retired=true;
            }
            prepared=false;
        }catch(...){stopped=true;throw;}
    }
    // Exact ReadResult signature. Arch's poller additionally requires COMPLETE
    // stage coverage and KV/index/remote/allcopy fences before invoking it.
    // Neither END nor C8 retirement alone provides those fences/stage credit.
    std::optional<DsromS81WaveStageResult> operator()(const DsromC8SourceOffer& offer)const {
        if(!enabled)return std::nullopt;
        healthy();require(same_offer(offer,terminal.offer),"ReadResult foreign terminal source offer");
        return retired?held:std::nullopt;
    }
    void warm_quarantine(){stopped=true;} // never erase the retained output
    bool fault()const{return stopped;}
};

// Bind the ACTUAL native Die<DIE>::d object at runtime construction, before it
// is erased to DieBase. Shared ownership keeps edge hooks/ReadResult coherent.
template<class NativeDie>
auto dsrom_s81_bind_native_result_read(NativeDie& die,DsromS81NativeResultTerminal terminal,
                                     uint64_t accepted_request_sequence,bool enable=false) {
    using Top=typename std::remove_reference<decltype(*die.d)>::type;
    return std::make_shared<DsromS81WaveNativeResultRead<Top>>(*die.d,std::move(terminal),accepted_request_sequence,enable);
}

// Exact DsromS81WaveStagePoller::ReadResult callback, shared with the edge hooks.
// Invoke it through that poller only after Arch's complete-stage/fence guards.
template<class Reader>
auto dsrom_s81_native_read_result_callback(std::shared_ptr<Reader> reader)
    -> std::function<std::optional<DsromS81WaveStageResult>(const DsromC8SourceOffer&)> {
    if(!reader)throw std::runtime_error("native ReadResult reader required");
    return [reader](const DsromC8SourceOffer& offer){return (*reader)(offer);};
}
