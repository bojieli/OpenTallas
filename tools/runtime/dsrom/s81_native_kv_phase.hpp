#pragma once
#include "s81_minimum_runtime.hpp"
#include <array>
#include <algorithm>
#include <memory>
#include <stdexcept>

namespace dsrom_s81_minimum {
// Borrow VDsromS81NativeKvPhase built with CKV_SELECTED=1 in the SAME context.
// No model allocation, source port remapping, host counter, readiness receipt
// or private tick. The caller drives/settles the existing WINDOW/CKV/ATT joins
// before this participant's prepare and registers this sole phase clock owner
// before shared cold_start. WINDOW, CKV service and HBM have separate owners.
// Output pins are the native RTL authority. SourceDescriptorOwner readiness,
// generation and final full640 retirement remain the provider's actual hooks.
template<class NativePhase>
DsromS81MinimumParticipant dsrom_s81_native_kv_phase_participant(
    DsromS81MinimumRuntime& runtime,NativePhase& phase) {
    if(!runtime.context||phase.contextp()!=runtime.context)
        throw std::runtime_error("native KV phase must borrow the shared context");
    struct Old {
        bool prepared=false,stopped=false;
        uint8_t start=0,wv=0,wm=0,ready=0,sv=0,sm=0,jready=0,jdone=0,pending=0;
        std::array<uint32_t,530> ww{},sw{};
    };
    auto old=std::make_shared<Old>();
    auto restore=[&phase,old]() {
        phase.window_source_start=old->start;phase.wsrc_v=old->wv;phase.wsrc_m=old->wm;
        phase.tile_packed_ready=old->ready;phase.svc_kv_v=old->sv;phase.svc_kv_m=old->sm;
        phase.svc_job_ready=old->jready;phase.svc_job_done=old->jdone;
        phase.svc_own_pending=old->pending;
        std::copy(old->ww.begin(),old->ww.end(),phase.wsrc_w.data());
        std::copy(old->sw.begin(),old->sw.end(),phase.svc_kv_w.data());
    };
    auto edge=[&runtime,&phase,old,restore](bool released,bool rising) {
        try {
            if(old->stopped||!old->prepared||(!released&&runtime.identity))
                throw std::runtime_error("native KV phase edge lacks snapshot or resets admitted context");
            restore();phase.rn=released;phase.clk=rising;phase.eval();
            if(!rising)old->prepared=false;
        }catch(...){old->stopped=true;throw;}
    };
    return {"borrowed native WINDOW32 to CKV128 phase",
        [&phase,old](const auto&) {
            try {
                if(old->stopped||old->prepared)
                    throw std::runtime_error("native KV phase duplicate or faulted prepare");
                old->start=phase.window_source_start;old->wv=phase.wsrc_v;old->wm=phase.wsrc_m;
                old->ready=phase.tile_packed_ready;old->sv=phase.svc_kv_v;old->sm=phase.svc_kv_m;
                old->jready=phase.svc_job_ready;old->jdone=phase.svc_job_done;
                old->pending=phase.svc_own_pending;
                std::copy_n(phase.wsrc_w.data(),530,old->ww.begin());
                std::copy_n(phase.svc_kv_w.data(),530,old->sw.begin());
                phase.clk=0;phase.eval();old->prepared=true;
            }catch(...){old->stopped=true;throw;}
        },
        [edge](bool released){edge(released,true);},
        [edge](bool released){edge(released,false);},
        [old](){return old->stopped;}};
}
} // namespace dsrom_s81_minimum
