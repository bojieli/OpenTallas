#pragma once
#include "s81_minimum_runtime.hpp"
#include "s81_embedding_abi.h"
#include <memory>

// The sink retains a real 16-word native reader payload. offer() is finite
// admission to the actual target adapter; visible() must match the retained
// identity/address/data and all target old-owner ACKs. Admission alone cannot
// release the native reader or establish an input lease.
struct DsromS81EmbeddingSink {
    std::function<bool(const S81EmbeddingOutput&)> offer;
    std::function<bool(const S81EmbeddingOutput&)> visible;
    std::function<bool()> fault;
};

class DsromS81MinimumEmbedding {
    struct State;
    std::shared_ptr<State> state;
public:
    DsromS81MinimumEmbedding(DsromS81MinimumRuntime&, const std::string& library,
                            const std::string& socket, uint32_t token,
                            uint32_t position, uint64_t identity, uint32_t base,
                            DsromS81EmbeddingSink);
    // Call after shared cold_start and actual runtime context admission.
    void start();
    bool complete() const;
    uint32_t committed_words() const;
    // Actual native VM read, available only after target matched publication.
    // This is raw H, not the native prefix's normalized XN field input.
    uint32_t word(uint32_t address) const;
};
