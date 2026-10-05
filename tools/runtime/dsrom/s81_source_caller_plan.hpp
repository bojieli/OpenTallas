#pragma once
#include <array>
#include <functional>
#include <vector>
#include "s81_source_caller_hooks.hpp"
#include "s81_wavefront_c8_port_join.hpp"

// The existing source preparation process binds its StageProgramJoin entries
// and retained producers here. No context or activation is synthesized by the
// executable caller. These functions inspect/drive actual producer state;
// the caller alone advances the native destination clock.
struct DsromS81SourceRank {
    std::string source_node; // literal CanonicalS81Execution node, not inferred from entry
    DsromC8SourceOffer offer;
    std::vector<DsromS81SavedVmSpan> saved;
    DsromS81SourceCallerHooks::SourceLease retained_source_span;
    DsromS81SourceCallerHooks::Fence input_visible;
    DsromS81SourceCallerHooks::Fence remote_drained;
    DsromS81SourceCallerHooks::Fence all_copies_drained;
    // If the receipt owner needs explicit reservation, arm it after capturing
    // old VM spans. A native accepted-edge scoreboard needs no such callback.
    // Native acceptance is observed on the actual edge, not implied by begin.
    std::function<void(const DsromC8SourceOffer&)> begin;
    // Required for cold inputs with no preceding native VM producer. It must
    // write the accepted context's actual inputs, not comparison activations.
    // Also allowed alongside carries for other source-owned input services.
    DsromS81SourceCallerHooks::Fence restore_inputs;
};

struct DsromS81SourceGroup {
    std::array<DsromS81SourceRank,4> ranks;
};

struct DsromS81SourcePlan {
    std::vector<DsromS81SourceGroup> groups;
};

// Resolve ONLY the owner's already-bound plan. Physical die IDs come from
// its explicit endpoint association, not the logical serial stage. This is
// request association, never C8 acceptance, publication or endpoint admission.
inline DsromC8SourceOffer dsrom_s81_resolve_source_offer(
    const DsromS81SourcePlan& plan,const DsromS81WaveRequest& request) {
    if(plan.groups.empty())throw std::runtime_error("WAVE source plan is empty");
    const auto& first=plan.groups.front().ranks[0].offer;
    if(first.token!=request.token||first.position!=request.position||first.user!=request.user)
        throw std::runtime_error("WAVE request differs from bound source plan");
    for(const auto& group:plan.groups) {
        const int endpoint=group.ranks[0].offer.die_id/4;
        for(unsigned r=0;r<4;r++) {
            const auto& rank=group.ranks[r];const auto& offer=rank.offer;
            DsromC8SourceDispatch checked(offer);
            if(offer.die_id<0||offer.die_id/4!=endpoint||offer.die_id%4!=int(r)||
               offer.identity!=first.identity||offer.token!=first.token||
               offer.position!=first.position||offer.user!=first.user||offer.epoch!=first.epoch)
                throw std::runtime_error("WAVE source plan endpoint/context association differs");
            if(rank.source_node.empty()||!rank.input_visible||!rank.remote_drained||
               !rank.all_copies_drained||(!rank.restore_inputs&&rank.saved.empty())||
               (!rank.saved.empty()&&!rank.retained_source_span))
                throw std::runtime_error("WAVE source plan native provider association missing");
        }
    }
    return first;
}

// Implemented in the owner's actual producer translation unit, linked into
// the same caller SO. A missing producer is a link error, never a dummy ACK.
DsromS81SourcePlan dsrom_s81_bind_source(DsromS81Runtime& runtime);

// Arendt and Popper supply these disjoint producer/receipt implementations.
// The generated factory passes the literal SourceExecution node and offer.
void dsrom_s81_bind_inputs(DsromS81Runtime&,DsromS81SourceRank&,const char* source_node);
void dsrom_s81_bind_receipts(DsromS81Runtime&,DsromS81SourceRank&,const char* source_node);
