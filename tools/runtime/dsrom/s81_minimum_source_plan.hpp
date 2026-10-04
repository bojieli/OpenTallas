#pragma once
#include "s81_minimum_embedding.hpp"

class Vnative_vm;

// Source-owned orchestration, not another model/runtime ABI. The actual input,
// return/capture and receipt providers register on the canonical runtime before
// cold_start. Captured resources must remain owned by their callback closures.
struct DsromS81MinimumSourcePlan {
    uint32_t token=0,position=0,vm_base=0;
    uint64_t identity=0;
    std::string embedding_library,embedding_socket;
    DsromS81EmbeddingSink embedding_sink;
    // Constructs Arendt's prefix around this exact reader and registers its
    // real SU/HE, input sender, return and sole selected-bank participants.
    // Called BEFORE the single shared cold reset, not at prefix start time.
    std::function<void(DsromS81MinimumEmbedding&)> attach;
    // Start the native prefix using the factory's actual target-VM read route
    // (EmbeddingMacroSink::target_word). No reader-private VM copy, installed
    // XN or expected intermediate; the prefix publishes its actual outputs.
    std::function<void()> begin_prefix;
    // Source-owned sequencer drives the next cycle from actual native ports.
    std::function<void()> advance;
    // Terminal for the selected minimum component and its actual accepted
    // outputs. This cannot certify unproduced rows/roots or whole C8/all-copy.
    std::function<bool()> complete;
};

// Defined by the selected source factory, linked with the actual providers.
// No weak binder, default successful callbacks or dynamic missing-symbol path.
DsromS81MinimumSourcePlan dsrom_s81_bind_minimum_source(
    DsromS81MinimumRuntime&,std::shared_ptr<Vnative_vm>);
