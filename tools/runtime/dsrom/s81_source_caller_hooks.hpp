#pragma once
#include <functional>
#include <memory>
#include <stdexcept>
#include <utility>
#include <vector>
#include "dsrom_s81_scheduler_api.hpp"
#include "dsrom_s81_workspace.hpp"

// Included by Cicero's actual dsrom_s81_source_main. These are native-model
// callbacks, not an input provider, allocator, clock, or visibility authority.
// The caller supplies saved source spans from its actual program/context and
// retains their producer runtimes. There is deliberately no bootstrap from
// expected activations, initial vm_init, empty spans, or a zero-filled image.
struct DsromS81SavedVmSpan {
    DsromS81Runtime* producer;
    int producer_die;
    uint64_t producer_identity;
    uint32_t producer_address;
    uint32_t destination_address;
    size_t words;
};

class DsromS81SourceCallerHooks {
public:
    using SourceLease = std::function<bool(int,uint64_t,uint32_t,size_t)>;
    using Fence = std::function<bool(const DsromC8SourceOffer&)>;
private:
    DsromS81Runtime& target;
    DsromC8SourceOffer owner;
    std::vector<DsromS81SavedVmSpan> spans;
    std::vector<std::unique_ptr<DsromS81Workspace>> carry;
    SourceLease retained_source_span;
    Fence input_visible, remote_drained, all_copies_drained;
    bool observed_retirement=false;
    bool sources_captured=false;

    static DieBase& native(DsromS81Runtime& runtime,int physical_die) {
        if(physical_die<0 || physical_die>=324 || runtime.stage!=physical_die/4 ||
           runtime.dies.size()!=4 || !runtime.dies.at(physical_die%4))
            throw std::runtime_error("source callback native physical stage/rank mismatch");
        return *runtime.dies.at(physical_die%4);
    }
    void matching(const DsromC8SourceOffer& offered) const {
        if(offered.die_id!=owner.die_id || offered.identity!=owner.identity ||
           offered.token!=owner.token || offered.position!=owner.position ||
           offered.user!=owner.user || offered.epoch!=owner.epoch || offered.entry!=owner.entry)
            throw std::runtime_error("source callback differs from retained program/context offer");
    }
public:
    DsromS81SourceCallerHooks(DsromS81Runtime& destination,DsromC8SourceOffer offer,
                             std::vector<DsromS81SavedVmSpan> saved,
                             SourceLease source_lease,Fence actual_input_visible,
                             Fence actual_remote_drain,Fence actual_allcopy_drain)
        : target(destination),owner(offer),spans(std::move(saved)),
          retained_source_span(std::move(source_lease)),input_visible(std::move(actual_input_visible)),
          remote_drained(std::move(actual_remote_drain)),all_copies_drained(std::move(actual_allcopy_drain)) {
        DsromC8SourceDispatch checked_offer(owner); // original bounds/identity codec
        native(target,owner.die_id);
        if(spans.empty() || !retained_source_span || !input_visible ||
           !remote_drained || !all_copies_drained)
            throw std::runtime_error("actual saved source spans and all source authorities required");
        for(size_t i=0;i<spans.size();i++) {
            const auto& s=spans[i];
            if(!s.producer)throw std::runtime_error("saved source producer runtime missing");
            native(*s.producer,s.producer_die);
            // Workspace enforces nonempty VM19 extents and full ID47 bounds.
            carry.emplace_back(new DsromS81Workspace(s.producer_die,s.producer_identity,
                s.producer_address,owner.die_id,owner.identity,s.destination_address,s.words));
            for(size_t j=0;j<i;j++) {
                const auto& previous=spans[j];
                if(uint64_t(s.destination_address)<uint64_t(previous.destination_address)+previous.words &&
                   uint64_t(previous.destination_address)<uint64_t(s.destination_address)+s.words)
                    throw std::runtime_error("saved source destination spans overlap");
            }
        }
    }

    bool capture_sources() {
        if(sources_captured)return true;
        // Call BEFORE accepting the next target offer: source and target may
        // be the same native group. The new C8 context replaces its visible
        // identity, so reading old-context words afterward is not authorized.
        // All producer/lease checks precede any destination writes.
        for(const auto& s:spans) {
            auto& producer=native(*s.producer,s.producer_die);
            if(producer.fault() || !producer.capture_visible(s.producer_identity) ||
               !retained_source_span(s.producer_die,s.producer_identity,s.producer_address,s.words))
                return false;
        }
        for(size_t i=0;i<spans.size();i++) {
            const auto& s=spans[i];
            auto& producer=native(*s.producer,s.producer_die);
            // capture invokes the actual vm_word DPI, never an expected file.
            if(!carry[i]->capture(producer,s.producer_die,retained_source_span))return false;
        }
        sources_captured=true;
        return true;
    }

    bool restore(const DsromC8SourceOffer& offered) {
        matching(offered);
        if(!sources_captured)return false; // never recapture after target offer
        auto& destination=native(target,owner.die_id);
        uint64_t identity;uint32_t token;uint16_t entry;
        if(!destination.c8_context(identity,token,entry))return false;
        if(identity!=owner.identity || token!=owner.token || entry!=owner.entry)
            throw std::runtime_error("workspace target lacks matching actual retained context");
        for(auto& workspace:carry) {
            // Native DPI checks target identity/quiet/no live ROM write, writes
            // the actual VM, then verifies that exact native word by readback.
            workspace->load(destination,owner.die_id,1u<<19);
            if(!workspace->setup_complete())return false;
        }
        // Setup is not the enclosing input lease/visibility fence. The caller
        // drives c8_context_restored only from this combined result.
        return input_visible(owner);
    }

    bool drain(const DsromC8SourceOffer& offered) {
        matching(offered);
        auto& die=native(target,owner.die_id);
        uint64_t identity;
        if(die.c8_retired(identity)) {
            if(identity!=owner.identity)throw std::runtime_error("foreign source retirement");
            observed_retirement=true;
        }
        if(die.fault())throw std::runtime_error("native source drain fault");
        return observed_retirement && die.capture_visible(owner.identity) &&
               remote_drained(owner) && all_copies_drained(owner);
    }
};
