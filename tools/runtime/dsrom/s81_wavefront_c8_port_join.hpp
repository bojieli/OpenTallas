#pragma once
#include <functional>
#include <optional>
#include <utility>
#include "dsrom_c8_source_dispatch.hpp"

// Native port join for Boole's selected S81 WAVE wrapper. This is caller
// bookkeeping, not engine RTL or a visibility/credit provider. No private
// eval/clock/reset and no completion inferred from C8 fragment retirement.
struct DsromS81WaveRequest {
    uint64_t sequence;
    uint32_t token,position,user;
};
struct DsromS81WaveStageResult {
    uint64_t request_sequence,identity;
    uint32_t next_token,next_value;
};
struct DsromS81WaveResultOrigin {
    uint64_t identity; // actual accepted-context ledger lookup, NOT a new epoch
    uint32_t user,position;
};

template<class Top> class DsromS81WaveC8PortJoin {
public:
    // Resolve through the actual emitted stage plan and saved epoch, then
    // retain/execute every fragment through existing source C8 dispatch.
    using Resolve=std::function<DsromC8SourceOffer(const DsromS81WaveRequest&)>;
    using Start=std::function<void(const DsromS81WaveRequest&,const DsromC8SourceOffer&)>;
    // Must inspect WHOLE-stage result + KV/index/remote/allcopy visibility.
    using Result=std::function<std::optional<DsromS81WaveStageResult>(const DsromS81WaveRequest&,const DsromC8SourceOffer&)>;
    using Retire=std::function<void(const DsromS81WaveStageResult&)>;
    // Actual incoming RESULT owner, sampled BEFORE edge. cur_user is NOT
    // its identity: a different request can issue on the very same edge.
    using ResultOrigin=std::function<std::optional<DsromS81WaveResultOrigin>()>;
    using Squash=std::function<void(const DsromS81WaveResultOrigin&,bool reject,bool squash)>;
    using ResultConsumed=std::function<void(const DsromS81WaveResultOrigin&)>;
private:
    Top& top;
    Resolve resolve;
    Start start;
    Result result;
    Retire retire;
    ResultOrigin origin;
    Squash invalidate;
    ResultConsumed consumed;
    bool enabled,stopped=false,prepared=false,request=false,accept=false;
    uint64_t sequence=0;
    uint32_t token=0,position=0;
    std::optional<DsromS81WaveRequest> active;
    std::optional<DsromC8SourceOffer> lease;
    std::optional<DsromS81WaveStageResult> held;
    std::optional<DsromS81WaveResultOrigin> incoming;
    static void require(bool b,const char* why) {
        if(!b)throw std::runtime_error(why);
    }
public:
    DsromS81WaveC8PortJoin(Top& t,Resolve r,Start s,Result p,Retire done,
                         ResultOrigin o,Squash q,bool enable=false,ResultConsumed received={}):
        top(t),resolve(std::move(r)),start(std::move(s)),result(std::move(p)),
        retire(std::move(done)),origin(std::move(o)),invalidate(std::move(q)),
        consumed(std::move(received)),enabled(enable) {
        require(bool(resolve)&&bool(start)&&bool(result)&&bool(retire)&&bool(origin)&&bool(invalidate),
                "WAVE requires source context, full-stage visibility and result-owner authorities");
        require(!enabled||bool(consumed),"enabled WAVE requires actual final RESULT ledger consumption");
    }
    // Enclosing caller must settle the real native model AFTER this method,
    // then call sample_before_edge(), then clock once, then after_edge().
    void drive() {
        if(!enabled)return;
        require(!stopped&&!prepared,"WAVE join quarantined or edge already sampled");
        if(active&&!held) {
            held=result(*active,*lease);
            if(held)require(held->request_sequence==active->sequence&&
                            held->identity==lease->identity&&held->next_token<(1u<<21),
                            "whole-stage result differs from saved WAVE source identity");
        }
        top.wf_stage_done=bool(held);
        top.wf_stage_next_token=held?held->next_token:0;
        top.wf_stage_next_val=held?held->next_value:0;
    }
    void sample_before_edge() {
        if(!enabled)return;
        require(!stopped&&!prepared,"WAVE edge sampled twice/quarantined");
        request=top.wf_request;token=top.wf_token;position=top.wf_pos;
        accept=top.wf_stage_accepted;incoming=origin();prepared=true;
        if(incoming)require(incoming->identity<(uint64_t(1)<<47)&&
                            incoming->user<(1u<<10)&&incoming->position<(1u<<21)&&
                            ((incoming->identity>>21)&1023)==incoming->user&&
                            (incoming->identity&((1u<<21)-1))==incoming->position,
                            "incoming RESULT lacks matching saved source context identity");
        require(!accept||bool(held),"unsolicited WAVE whole-stage acceptance");
    }
    void after_edge() {
        if(!enabled)return;
        try {
            require(prepared&&!stopped,"WAVE edge has no old-port sample");
            // Complete old stage BEFORE retaining a simultaneous new request.
            if(accept){retire(*held);held.reset();active.reset();lease.reset();}
            if(top.wf_reject||top.wf_squash) {
                require(bool(incoming),"WAVE squash lacks actual incoming RESULT owner");
                invalidate(*incoming,bool(top.wf_reject),bool(top.wf_squash));
            }
            // Provider returns ONLY old res_v with the actual final-part
            // condition. Consume every such RESULT, not only reject/squash.
            if(incoming)consumed(*incoming);
            if(request) {
                require(!active,"WAVE issued over an unaccepted whole-stage result");
                const uint32_t user=top.wf_user; // source cur_user updated on this edge
                require(token<(1u<<21)&&position<(1u<<21)&&user<(1u<<10),"WAVE request bounds");
                DsromS81WaveRequest req{sequence++,token,position,user};
                const auto offer=resolve(req);
                DsromC8SourceDispatch checked(offer); // exact retained ID47 codec
                require(offer.token==token&&offer.position==position&&offer.user==user,
                        "resolved C8 source differs from actual WAVE request");
                active=req;lease=offer;start(req,offer); // retention, NOT engine acceptance
            }
            prepared=false;
        }catch(...){stopped=true;throw;}
    }
    // Never clear pending state on local reset or rejected-token observation.
    void warm_quarantine(){stopped=true;}
    bool pending()const{return bool(active)||bool(held);}
    bool fault()const{return stopped;}
};
