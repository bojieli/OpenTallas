#pragma once
#include "s81_minimum_source_bindings.hpp"

struct DsromS81L20CollectiveLiteral {
    DsromS81PrefixOperation operation;
    unsigned src,dst,n,mode,rnd,seq;
};
// Exact 13 non-TOPK instructions from Arch's demand-r5 L20 census.
const std::array<DsromS81L20CollectiveLiteral,13>& dsrom_s81_l20_collective_literals();
// Caller supplies four distinct rank SourceIo owners, actual accepted-command
// publication.begin and native captured-output tag reservation callbacks.
// Dispatch participant ONCE on the SAME shared 833ps caller clock: either
// nested in the existing Prefix sequencer OR runtime.participants, never both.
// idle includes all four rank positive VM visibility receipts, not leaf idle.
DsromS81PrefixNativeEngine dsrom_s81_bind_native_l20_collective(
    DsromS81MinimumRuntime&,uint64_t identity,
    const std::array<DsromS81MinimumSourceIo,4>&,
    std::function<void(unsigned rank,unsigned pc)> accepted,
    std::function<void(unsigned rank,unsigned pc,const S81EmbeddingOutput&)> captured,
    bool opt_in=false);
