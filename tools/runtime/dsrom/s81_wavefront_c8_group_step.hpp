#pragma once
#include <array>
#include <functional>
#include "dsrom_c8_source_dispatch.hpp"

// Incremental version of the existing source TP4 dispatch. The enclosing
// WAVE/stage runner owns the ONE shared edge; no recursive/private tick.
// Completion is one actual emitted fragment group, NOT a whole-stage result.
class DsromS81C8GroupStep {
    std::array<DsromC8SourceOffer,4> offers;
    std::array<DsromC8SourceDispatch,4> dispatch;
    bool prepared=false,stopped=false;
    std::array<bool,4> taken{},sample_accept{};
    std::array<std::function<bool()>,4> accepted_context{};
    std::function<void(const DsromC8SourceOffer&)> accepted_hook;
public:
    explicit DsromS81C8GroupStep(std::array<DsromC8SourceOffer,4> source,
        std::function<void(const DsromC8SourceOffer&)> actual_accept={}):
        offers(source),dispatch{{DsromC8SourceDispatch(source[0]),DsromC8SourceDispatch(source[1]),
                                DsromC8SourceDispatch(source[2]),DsromC8SourceDispatch(source[3])}},
        accepted_hook(std::move(actual_accept)) {
        std::array<bool,4> ranks{};
        for(const auto& o:offers) {
            if(o.die_id<0||o.die_id>=324||ranks[o.die_id%4]||
               o.die_id/4!=offers[0].die_id/4||o.identity!=offers[0].identity||o.token!=offers[0].token)
                throw std::runtime_error("incremental TP4 actual source group mismatch");
            ranks[o.die_id%4]=true;
        }
    }
    template<class Runtime,class Restore,class Drain>
    bool before_edge(Runtime& runtime,Restore& restore,Drain& drain) {
        if(stopped||prepared)throw std::runtime_error("TP4 source edge reused/quarantined");
        try {
            sample_accept.fill(false);
            if(runtime.stage!=offers[0].die_id/4||runtime.dies.size()!=4)
                throw std::runtime_error("incremental TP4 native owner mismatch");
            for(unsigned i=0;i<4;i++)if(!dispatch[i].complete()) {
                auto* die=runtime.dies.at(offers[i].die_id%4);
                if(!die||die->fault())throw std::runtime_error("incremental TP4 native fault/missing rank");
                dispatch[i].before_edge(*die,offers[i].die_id,restore,drain);
                sample_accept[i]=!taken[i]&&!dispatch[i].complete()&&die->c8_ready();
                const auto offer=offers[i];
                accepted_context[i]=[die,offer](){
                    uint64_t identity=0;uint32_t token=0;uint16_t entry=0;
                    return die->c8_context(identity,token,entry)&&identity==offer.identity&&
                           token==offer.token&&entry==offer.entry;
                };
            }
            prepared=!complete();return prepared;
        }catch(...){stopped=true;throw;}
    }
    void after_edge() {
        if(stopped||!prepared)throw std::runtime_error("TP4 source acceptance without shared sampled edge");
        try {
            for(auto& d:dispatch)d.accepted_edge();
            for(unsigned i=0;i<4;i++)if(sample_accept[i]&&!accepted_context[i]())
                throw std::runtime_error("sampled C8 handshake lacks actual post-edge accepted context");
            for(unsigned i=0;i<4;i++)if(sample_accept[i])taken[i]=true;
            for(unsigned i=0;i<4;i++)if(sample_accept[i]&&accepted_hook)accepted_hook(offers[i]);
            prepared=false;
        }catch(...){stopped=true;throw;}
    }
    bool complete()const {
        for(const auto& d:dispatch)if(!d.complete())return false;
        return true;
    }
    void warm_quarantine(){stopped=true;}
    bool fault()const{return stopped;}
};
