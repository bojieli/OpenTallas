#pragma once
#include "s81_minimum_source_bindings.hpp"
#include <memory>

// Head-only service after actual I5 logits, before existing I6/ReadResult.
// Native SELECT64 per rank -> existing TOP2048 n64/k1/stride32320.
// No replacement literal ISA, dot arithmetic, output oracle or private tick.
struct DsromS81HeadArgmaxResult {
    uint64_t identity=0,sequence=0;
    uint32_t global_id=0,bits=0;
};
class DsromS81NativeHeadArgmax {
    struct Impl;
    std::shared_ptr<Impl> state;
public:
    // SourceIo must read the actual produced FP32 LOGITS home on each rank.
    // Construct/register before the caller's ONE shared cold reset.
    DsromS81NativeHeadArgmax(DsromS81MinimumRuntime&,uint64_t identity,
        const std::array<DsromS81MinimumSourceIo,4>&,uint32_t actual_logits_base);
    DsromS81MinimumParticipant participant();
    bool inputs_ready()const;
    void start(uint64_t actual_sequence);
    std::optional<DsromS81HeadArgmaxResult> result()const;
    // Call ONLY when the existing END/ReadResult consumer really accepts it.
    void acknowledge(const DsromS81HeadArgmaxResult& actual_accepted);
    bool idle()const;
    bool fault()const;
};
