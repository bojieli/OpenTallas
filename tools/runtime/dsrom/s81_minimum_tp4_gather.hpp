#pragma once
#include "s81_minimum_source_bindings.hpp"

// Same held runtime/context, existing SourceIo and publisher reservation
// namespace. Caller binds each ACTUAL rank, never repeats rank0 as a peer.
struct DsromS81NativeGather {
    DsromS81MinimumParticipant participant;
    std::function<void(unsigned pc)> start;
    std::function<bool()> complete;
};
DsromS81NativeGather dsrom_s81_bind_native_tp4_gather(
    DsromS81MinimumRuntime&,uint64_t identity,
    const std::array<DsromS81MinimumSourceIo,4>&,
    // Begin the literal publisher extent at actual native GO acceptance.
    std::function<void(unsigned rank,unsigned pc)> accepted,
    // Reserve existing tags/record actual native output before SourceIo.offer.
    std::function<void(unsigned rank,unsigned pc,const S81EmbeddingOutput&)> captured);
