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

#ifdef DSROM_S81_HEAD_WINNER_BINDING_HEADER
#include DSROM_S81_HEAD_WINNER_BINDING_HEADER
#include "s81_minimum_prefix_io.hpp"
// Borrow the existing one-word output stage at the native pad/join sink.
// I5 must already be enrolled/begun by REAL source command acceptance. Caller
// retains the actual root/join output until this returns true and must not
// recapture it after acceptance. This writes canonical LOGITS, not a winner VM
// alias. The existing batch owns tags/offer/positive matched bank ACKs.
inline bool dsrom_s81_publish_minimum_head_logit(
    DsromS81MinimumRuntime& runtime,DsromS81MinimumPrefixOutputBatch& batch,
    uint64_t identity,unsigned rank,unsigned local_row,
    uint32_t actual_join_tag,uint32_t actual_join_bits,bool actual_join_valid) {
    if(!runtime.identity||*runtime.identity!=identity||runtime.rank!=int(rank)||
       rank>=4||local_row>=32320||!actual_join_valid||
       actual_join_tag!=(((rank*32320+local_row)<<13)|34u))
        throw std::runtime_error("native HEAD logit lacks actual matching root/join/context");
    S81EmbeddingOutput output{};output.vm_valid=1;output.vm_identity=identity;
    output.vm_address=486848+local_row;output.vm_data[0]=actual_join_bits;
    if(!batch.pending())batch.capture(4892,output,1,true);
    else if(!batch.retains(output,1))
        throw std::runtime_error("native HEAD changed held logit before matched VM ACK");
    return batch.progress(); // acceptance alone does not release the native root
}

// Existing caller's native HEAD continuation. Borrow the four REAL publication
// homes; neither files nor a declared extent authorize the reducer. Construct
// once before shared cold reset. The returned Hubble binding owns the existing
// reader; caller invokes drive/settle/sample/edge/after_edge, then consumed ONLY
// after its actual StagePoller accepted(result) and all enclosing fences.
template<class Top>
auto dsrom_s81_join_minimum_head_result_source(
    DsromS81MinimumRuntime& runtime,Top& top,
    DsromS81NativeResultTerminal terminal,uint64_t accepted_sequence,
    const std::array<dsrom_s81_minimum::PrefixPublication*,4>& publications,
    const std::array<DsromS81MinimumSourceIo,4>& actual_rank_io) {
    constexpr unsigned producer=4892,base=486848,rows=32320;
    if(!runtime.context||runtime.identity||terminal.offer.identity>=(1ull<<47)||
       terminal.source_node.empty())
        throw std::runtime_error("native HEAD result join requires cold actual terminal context");
    for(unsigned r=0;r<4;++r) {
        if(!publications[r]||!actual_rank_io[r].read_word||!actual_rank_io[r].span_lease)
            throw std::runtime_error("native HEAD requires four actual publication/read homes");
        for(unsigned q=0;q<r;++q)if(publications[q]==publications[r])
            throw std::runtime_error("native HEAD cannot alias rank publication homes");
    }
    auto argmax=std::make_shared<DsromS81NativeHeadArgmax>(
        runtime,terminal.offer.identity,actual_rank_io,base);
    auto participant=argmax->participant();
    for(const auto& old:runtime.participants)if(old.name==participant.name)
        throw std::runtime_error("native HEAD argmax participant already enrolled");
    auto prepare=participant.prepare;
    auto started=std::make_shared<bool>(false);
    const uint64_t identity=terminal.offer.identity;
    participant.prepare=[prepare,argmax,started,publications,actual_rank_io,identity,accepted_sequence]
        (const DsromS81PairResult& snapshot) {
        prepare(snapshot); // SAME shared-edge participant; no private eval/tick
        if(*started)return;
        for(unsigned r=0;r<4;++r) {
            if(publications[r]->fault())throw std::runtime_error("native HEAD logits publication fault");
            if(!publications[r]->complete(identity,producer)||
               !actual_rank_io[r].span_lease(identity,base,rows))return;
        }
        if(argmax->inputs_ready()) {
            argmax->start(accepted_sequence);*started=true;
        }
    };
    auto reader=std::make_shared<DsromS81WaveNativeResultRead<Top>>(
        top,terminal,accepted_sequence,true);
    auto binding=dsrom_s81_bind_native_head_winner(
        top,argmax,reader,std::move(terminal),accepted_sequence,true);
    runtime.participants.push_back(std::move(participant));
    return binding; // never infer END, final_ready, retirement or consumption
}
#endif
