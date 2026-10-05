#pragma once
#include "s81_minimum_prefix.hpp"
#include "s81_minimum_return_participant.hpp"
#include "s81_prefix_publication.hpp"

// Provider functions are mandatory link dependencies. This is the selected
// source's composition surface, not a second PairDrive/model/clock ABI.
struct DsromS81MinimumSourceTags {
    using Owner=std::array<uint32_t,8>;
    // ONE reservation namespace for embedding AND every actual prefix/cold
    // native write. Prefix providers call this on their sampled raw output
    // BEFORE publication.native_scalar; publication.record only retrieves that
    // already-reserved immutable MacroWrite, never allocates another tag.
    std::function<dsrom_s81_minimum::MacroWrite(const S81EmbeddingOutput&,unsigned)> record;
    std::function<Owner(uint64_t,uint32_t)> read_owner;
    // Root records reserve in the SAME namespace before field-bank acceptance.
    std::function<Owner(const dsrom_s81_minimum::ReturnPhaseBinding&,
                        const dsrom_s81_minimum::CaptureOwner&)> root_owner;
    // Reject tags absent from the held reservation ledger; no inferred accept
    // at record construction, native write observation, or macro ACK.
    std::function<void(unsigned,const dsrom_s81_minimum::MacroWrite&)> scalar_accept;
    std::function<void(uint32_t,const Owner&)> read_accept;
};

struct DsromS81MinimumSourceIo {
    std::function<std::optional<uint32_t>(uint64_t,uint32_t)> read_word;
    std::function<bool(uint64_t,uint32_t,unsigned)> span_lease;
    std::function<bool(const S81EmbeddingOutput&,unsigned)> offer,visible;
};

struct DsromS81MinimumPrefixBinding {
    DsromS81PrefixNativeEngine su,he;
    // Actual native SSX/PF bootstrap shares the host tick, never a host sum.
    DsromS81MinimumParticipant bootstrap;
    std::function<void()> start_bootstrap;
};

// Hubble owns reserved tags and advances the ledger ONLY in actual acceptance
// callbacks. record() reserves/returns held tags; it does not report acceptance.
DsromS81MinimumSourceTags dsrom_s81_bind_minimum_source_tags(
    DsromS81MinimumRuntime&,uint64_t identity);

// Arendt joins Hubble's selected SU and Peirce's HE/SSX/PF native participants.
// The caller owns PrefixPublication and the ONE target bank participant.
// Engines build those commands via the SAME Tags.record reservation closure,
// then sample native outputs into publication.native_scalar; cold bootstrap
// admits SSX/PF via publication.begin ONLY at actual native GO acceptance.
DsromS81MinimumPrefixBinding dsrom_s81_bind_minimum_prefix_engines(
    DsromS81MinimumRuntime&,uint64_t identity,
    dsrom_s81_minimum::PrefixPublication&,const DsromS81MinimumSourceIo&,
    const DsromS81MinimumSourceTags&);
