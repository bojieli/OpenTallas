#pragma once
#include "s81_minimum_source_bindings.hpp"

// Existing SourceIo for FOUR real rank VMs: L20.I47 SV[446816,447328)
// and SEL[365024,365536), held under the same identity47/native publication.
// Existing publisher/tag callbacks receive actual native output bits BEFORE
// offer; visible is only positive same-target native ACK publication.
DsromS81PrefixNativeEngine dsrom_s81_bind_native_top512(
    DsromS81MinimumRuntime&,uint64_t identity,
    const std::array<DsromS81MinimumSourceIo,4>&,
    std::function<void(unsigned rank,unsigned producer,const S81EmbeddingOutput&)> captured,
    // Optional release notification ONLY after all64 real native load strobes.
    std::function<void(unsigned rank)> inputs_consumed={});
