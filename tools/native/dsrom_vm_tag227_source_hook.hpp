#pragma once
#include "dsrom_vm_tag227.hpp"
namespace dsrom { namespace component_tag227 {
// Integration inputs, not derived from a guessed stage or truncated expert ID.
// Popper/Cicero bind these to the actual compiled selection and immutable offer.
struct SourceOffer {
    std::uint64_t identity47, token17;
    std::uint64_t compiled_stage, compiled_rank, accepted_pair, accepted_phase, accepted_entry;
};
inline ComponentContext context_from_source_offer(const SourceOffer& s) {
    ComponentContext c{s.identity47,s.token17,s.compiled_stage,s.compiled_rank,
                       s.accepted_pair,s.accepted_phase,s.accepted_entry};
    (void)pack({c,1,0,0});return c;
}
class SourceOfferHook {
    ComponentContext frozen_;
    AcceptedIdLedger ledger_;
    void match(const SourceOffer& s) const {
        if(pack({context_from_source_offer(s),0,0,0})!=pack({frozen_,0,0,0}))
            throw std::invalid_argument("COMPONENT_TAG227 held source offer changed");
    }
public:
    SourceOfferHook(const SourceOffer& actual,std::uint64_t era,std::uint64_t batch)
        :frozen_(context_from_source_offer(actual)),ledger_(frozen_,era,batch){}
    Tag227 tag_for_offer(const SourceOffer& actual)const {
        match(actual);return ledger_.offer_tag();
    }
    // Sample actual backend PRE-edge wr_accept_v[bank]/rd_accept_v, NOT wr_v,
    // queueing, busy, generic done or a modeled due edge. One call per acceptance.
    bool on_backend_accept(bool actual_rst_n,bool actual_accept,
                           const SourceOffer& actual,const Tag227& sampled_tag) {
        if(!actual_accept)return false;
        if(!actual_rst_n)throw std::logic_error("COMPONENT_TAG227 acceptance on reset edge");
        match(actual);ledger_.actual_accept(sampled_tag);return true;
    }
    // Caller proves matching visibility/retirement separately. Raw N+3 receipt
    // MUST NOT invoke this as qualified publication or release phase/bank credit.
    void on_qualified_retirement(const Tag227& returned){ledger_.qualified_retire(returned);}
    void next_batch(){ledger_.next_batch();}
    std::size_t outstanding()const{return ledger_.outstanding();}
};
}}
