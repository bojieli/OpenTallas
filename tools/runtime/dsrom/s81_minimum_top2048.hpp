#pragma once
#include "s81_minimum_source_bindings.hpp"

// Existing SourceIo for FOUR real rank VMs: L20.I52 CBSV[482720,484768)
// and CBSEL[480672,482720), held under the same identity47/native publication.
// Existing publisher/tag callbacks receive actual native output bits BEFORE
// offer; visible is only positive same-target native ACK publication.
DsromS81PrefixNativeEngine dsrom_s81_bind_native_top2048(
    DsromS81MinimumRuntime&,uint64_t identity,
    const std::array<DsromS81MinimumSourceIo,4>&,
    std::function<void(unsigned rank,unsigned producer,const S81EmbeddingOutput&)> captured,
    // Optional release notification ONLY after all256 real native load strobes.
    std::function<void(unsigned rank)> inputs_consumed={});
