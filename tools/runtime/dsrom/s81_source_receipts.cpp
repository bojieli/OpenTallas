#include "s81_source_caller_plan.hpp"

// Compile with Popper's actual drain-runtime successor API. Its callbacks are
// driven by native accepted contexts, VM events, link parity credits and CKV
// receive edges. The base scheduler intentionally has no such authority.
void dsrom_s81_bind_receipts(DsromS81Runtime& runtime,DsromS81SourceRank& rank,
                           const char* source_node) {
    if(!source_node || !*source_node || !runtime.remote_drained || !runtime.all_copies_drained)
        throw std::runtime_error("actual source node and native receipt authorities required");
    rank.remote_drained=[&runtime](const DsromC8SourceOffer& offer) {
        if(!runtime.remote_drained)throw std::runtime_error("native remote receipt authority removed");
        return runtime.remote_drained(offer);
    };
    rank.all_copies_drained=[&runtime](const DsromC8SourceOffer& offer) {
        if(!runtime.all_copies_drained)throw std::runtime_error("native allcopy receipt authority removed");
        return runtime.all_copies_drained(offer);
    };
    // The source span's retained address/version lease is a separate authority
    // supplied by its actual producer. Neither remote drain nor an identity
    // match authorizes a source VM read or address reuse.
    if(!rank.saved.empty() && !rank.retained_source_span)
        throw std::runtime_error("carried source lacks retained VM range/version lease");
}
