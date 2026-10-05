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

#include "s81_minimum_prefix_io.hpp"

// Opt-in actual-port carry. The enclosing caller supplies the emitted writer
// association and accepted-edge observers; no producer index, admission, ACK,
// context-restored pulse or clock is manufactured here. Do not combine this
// path with the legacy Workspace setup writes for the same destination.
class DsromS81SourceIoTransferHooks {
public:
    using Fence=DsromS81SourceCallerHooks::Fence;
    struct Binding {
        DsromS81SavedVmSpan span;
        DsromS81MinimumSourceIo source,destination;
        dsrom_s81_minimum::PrefixPublication* publication;
        std::optional<unsigned> enrolled_writer;
        // True only after this emitted writer's real native admission. The
        // provider has already enrolled its exact extents and called begin.
        std::function<bool(const DsromC8SourceOffer&,unsigned)> writer_admitted;
        // Samples acceptance of THIS held payload by the actual transfer
        // writer, with its unchanged source/destination association.
        std::function<bool(const DsromC8SourceOffer&,unsigned,
                           const S81EmbeddingOutput&,unsigned)> transfer_accepted;
    };
private:
    DsromC8SourceOffer owner;
    std::vector<Binding> bindings;
    std::vector<std::unique_ptr<DsromS81MinimumPrefixOutputBatch>> batches;
    Fence context,input_visible,remote_drained,all_copies_drained;
    size_t selected=0;
    unsigned offset=0,read=0,count=0;
    S81EmbeddingOutput held{};
    bool captured=false,stopped=false;

    void matching(const DsromC8SourceOffer& o) const {
        if(o.die_id!=owner.die_id||o.identity!=owner.identity||o.token!=owner.token||
           o.position!=owner.position||o.user!=owner.user||o.epoch!=owner.epoch||o.entry!=owner.entry)
            throw std::runtime_error("SourceIo transfer changed accepted destination association");
    }
    bool sources_retained() const {
        for(const auto& b:bindings) {
            if(b.publication->fault())throw std::runtime_error("transfer publication quarantined");
            if(!b.source.span_lease(b.span.producer_identity,b.span.producer_address,
                                    unsigned(b.span.words)))return false;
        }
        return true;
    }
    bool published() const {
        if(selected!=bindings.size())return false;
        for(const auto& b:bindings)
            if(!b.publication->complete(owner.identity,*b.enrolled_writer)||
               !b.destination.span_lease(owner.identity,b.span.destination_address,
                                          unsigned(b.span.words)))return false;
        return true;
    }
public:
    DsromS81SourceIoTransferHooks(DsromS81MinimumRuntime& runtime,
        DsromC8SourceOffer offer,std::vector<Binding> actual,
        const DsromS81MinimumSourceTags& tags,Fence positive_context,
        Fence actual_input_visible,Fence actual_remote,Fence actual_allcopy)
        :owner(offer),bindings(std::move(actual)),context(std::move(positive_context)),
         input_visible(std::move(actual_input_visible)),remote_drained(std::move(actual_remote)),
         all_copies_drained(std::move(actual_allcopy)) {
        DsromC8SourceDispatch checked(owner);
        if(bindings.empty()||!context||!input_visible||!remote_drained||!all_copies_drained)
            throw std::runtime_error("SourceIo transfer lacks actual context/publication/receipt providers");
        for(size_t i=0;i<bindings.size();++i) {
            const auto& b=bindings[i];const auto& s=b.span;
            if(!s.producer||s.producer_die<0||s.producer_die>=324||
               s.producer->stage!=s.producer_die/4||s.producer->dies.size()!=4||
               !s.producer->dies.at(s.producer_die%4)||s.producer_identity>=(1ull<<47)||
               !s.words||uint64_t(s.producer_address)+s.words>(1u<<19)||
               uint64_t(s.destination_address)+s.words>(1u<<19)||
               !b.source.read_word||!b.source.span_lease||!b.destination.span_lease||
               !b.publication||!b.enrolled_writer||*b.enrolled_writer>=(1u<<14)||
               !b.writer_admitted||!b.transfer_accepted)
                throw std::runtime_error("SourceIo transfer lacks emitted source/destination/writer tuple");
            for(size_t j=0;j<i;++j) {
                const auto& p=bindings[j].span;
                if(uint64_t(s.destination_address)<uint64_t(p.destination_address)+p.words&&
                   uint64_t(p.destination_address)<uint64_t(s.destination_address)+s.words)
                    throw std::runtime_error("SourceIo transfer destination ranges overlap");
            }
            batches.emplace_back(new DsromS81MinimumPrefixOutputBatch(
                runtime,owner.identity,*b.publication,b.destination,tags));
        }
    }
    // Called by the existing shared-clock participant/caller; never ticks.
    // At most one qualified source word or one held batch progresses per call.
    bool restore(const DsromC8SourceOffer& offer) {
        try {
            matching(offer);
            if(stopped)throw std::runtime_error("SourceIo transfer quarantined");
            if(!sources_retained()||!context(owner))return false;
            if(selected==bindings.size())return published()&&input_visible(owner);
            auto& b=bindings[selected];auto& batch=*batches[selected];
            if(!b.writer_admitted(owner,*b.enrolled_writer))return false;
            if(captured) {
                if(!batch.progress())return false;
                offset+=count;read=count=0;captured=false;
                if(offset==b.span.words){++selected;offset=0;}
                return selected==bindings.size()&&published()&&input_visible(owner);
            }
            if(!count) {
                count=unsigned(std::min<size_t>(16,b.span.words-offset));
                held={};held.vm_valid=true;held.vm_identity=owner.identity;
                held.vm_address=b.span.destination_address+offset;
            }
            if(read<count) {
                auto word=b.source.read_word(b.span.producer_identity,b.span.producer_address+offset+read);
                if(!word)return false;
                held.vm_data[read++]=*word; // native qualified raw bits, no FP conversion
                return false;
            }
            // Real writer acceptance is required; a read/lease or declaration
            // alone cannot create native_scalar or reserve its write tag.
            if(!b.transfer_accepted(owner,*b.enrolled_writer,held,count))return false;
            batch.capture(*b.enrolled_writer,held,count,true);captured=true;
            return false;
        }catch(...){stopped=true;throw;}
    }
    bool drain(const DsromC8SourceOffer& offer) {
        try {
            matching(offer);
            if(stopped)throw std::runtime_error("SourceIo transfer quarantined");
            // The original producer's published lease is not released by
            // destination admission, first ACK, setup completion or idle.
            return sources_retained()&&context(owner)&&published()&&input_visible(owner)&&
                   remote_drained(owner)&&all_copies_drained(owner);
        }catch(...){stopped=true;throw;}
    }
};
