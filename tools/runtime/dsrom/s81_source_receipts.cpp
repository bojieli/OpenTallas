#include "s81_source_caller_plan.hpp"

// Compile with the actual drain-runtime successor. Declaration binds literal
// native program outputs; only accepted native contexts/writes/copies/reverse
// edges make its receipt and source-span queries positive.
void dsrom_s81_bind_receipts(DsromS81Runtime& runtime,DsromS81SourceRank& rank,
                           const char* source_node) {
    if(!source_node||!*source_node||rank.source_node!=source_node||
       !runtime.bind_receipt||!runtime.remote_drained||!runtime.all_copies_drained||
       rank.offer.die_id<0||rank.offer.die_id>=324||runtime.stage!=rank.offer.die_id/4||
       runtime.dies.size()!=4||!runtime.dies.at(rank.offer.die_id%4))
        throw std::runtime_error("actual literal source/offer and native receipt authorities required");
    const auto owner=rank.offer;
    DsromC8SourceDispatch checked(owner);
    auto matching=[owner](const DsromC8SourceOffer& o) {
        if(o.die_id!=owner.die_id||o.identity!=owner.identity||o.token!=owner.token||
           o.position!=owner.position||o.user!=owner.user||o.epoch!=owner.epoch||o.entry!=owner.entry)
            throw std::runtime_error("native receipt query changed retained source offer");
    };
    // Retain actual source associations, not a mutable reference to a reused
    // SourceRank. No source lease is inferred from capture visibility/idle.
    const auto saved=rank.saved;
    auto supplied=rank.retained_source_span;
    for(const auto& s:saved) {
        if(!s.producer||s.producer_die<0||s.producer_die>=324||
           s.producer->stage!=s.producer_die/4||s.producer->dies.size()!=4||
           !s.producer->dies.at(s.producer_die%4)||s.producer_identity>=(1ull<<47)||
           !s.words||uint64_t(s.producer_address)+s.words>(1u<<19)||
           uint64_t(s.destination_address)+s.words>(1u<<19)||
           (!supplied&&!s.producer->source_span_lease))
            throw std::runtime_error("carried source lacks actual retained writer/range/version lease");
    }
    if(!saved.empty())rank.retained_source_span=[saved,supplied](int die,uint64_t id,
                                                              uint32_t address,size_t words) {
        if(!words||uint64_t(address)+words>(1u<<19))return false;
        DsromS81Runtime* producer=nullptr;
        for(const auto& s:saved) {
            if(s.producer_die!=die||s.producer_identity!=id||address<s.producer_address||
               uint64_t(address)+words>uint64_t(s.producer_address)+s.words)continue;
            if(producer&&producer!=s.producer)
                throw std::runtime_error("ambiguous retained physical source runtime");
            producer=s.producer;
        }
        if(!producer)return false;
        // Preserve a stronger publication/reader-held provider when supplied.
        if(supplied)return supplied(die,id,address,words);
        if(!producer->source_span_lease)
            throw std::runtime_error("native source-span authority removed");
        return producer->source_span_lease(die,id,address,words);
    };
    // Must precede the offer's actual accept edge. This does not reserve or
    // acknowledge anything; the native book rejects unbound/invalid programs.
    runtime.bind_receipt(owner,source_node);
    rank.remote_drained=[&runtime,matching](const DsromC8SourceOffer& offer) {
        matching(offer);
        if(!runtime.remote_drained)throw std::runtime_error("native remote receipt authority removed");
        return runtime.remote_drained(offer);
    };
    rank.all_copies_drained=[&runtime,matching](const DsromC8SourceOffer& offer) {
        matching(offer);
        if(!runtime.all_copies_drained)throw std::runtime_error("native allcopy receipt authority removed");
        return runtime.all_copies_drained(offer);
    };
}
