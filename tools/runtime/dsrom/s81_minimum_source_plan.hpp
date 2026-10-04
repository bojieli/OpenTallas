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
    // Explicit representative-entry path: no embedding reader/model is made.
    // The factory owns the same native input writer and actual ACK authority.
    std::function<void()> attach_seeded,initialize_seeded;
    std::function<bool()> seeded_inputs_visible;
    // Start the native prefix using the factory's actual target-VM read route
    // (EmbeddingMacroSink::target_word). No reader-private VM copy, installed
    // XN or expected intermediate; the prefix publishes its actual outputs.
    std::function<void()> begin_prefix;
    // Source-owned sequencer drives the next cycle from actual native ports.
    std::function<void()> advance;
    // Terminal for the selected minimum component and its actual accepted
    // outputs. This cannot certify unproduced rows/roots or whole C8/all-copy.
    std::function<bool()> complete;
    // Factory snapshots the actual native counters around its L20 operation
    // interval. Called only after real terminal drain; no rate inference here.
    std::function<void(const std::string&)> write_measurements;
};

// Defined by the selected source factory, linked with the actual providers.
// No weak binder, default successful callbacks or dynamic missing-symbol path.
DsromS81MinimumSourcePlan dsrom_s81_bind_minimum_source(
    DsromS81MinimumRuntime&,std::shared_ptr<Vnative_vm>);

#ifdef DSROM_S81_L20_KV_ENCLOSING
#include "s81_minimum_l20_kv_factory.hpp"
// Called once before cold admission, using the real TP4 owner factory. These
// engines replace the caller's existing SU/ME slots, not extra clock owners.
void dsrom_s81_join_minimum_l20_kv_source(
    std::shared_ptr<dsrom_s81_minimum::L20KvFactory>,
    const std::array<DsromS81MinimumRuntime*,4>&,
    std::array<DsromS81PrefixNativeEngine,4>& su,
    std::array<DsromS81PrefixNativeEngine,4>& me);
std::shared_ptr<dsrom_s81_minimum::L20KvFactory> dsrom_s81_join_minimum_l20_kv_source(
    std::array<dsrom_s81_minimum::L20KvRankBinding,4>,
    std::function<void(const std::array<dsrom_s81_minimum::L20NativeCkv,4>&)>,
    std::array<DsromS81PrefixNativeEngine,4>& su,
    std::array<DsromS81PrefixNativeEngine,4>& me);

#endif
