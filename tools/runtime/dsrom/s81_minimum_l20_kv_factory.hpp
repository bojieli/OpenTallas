#pragma once
#include "s81_minimum_prefix_providers.hpp"
#include "s81_minimum_su256_ports.hpp"
#include "s81_minimum_qe_quantizer.hpp"
#include <array>
#include <memory>
#include <variant>
class VDsromAttention;
#ifdef DSROM_S81_SIM_ONLY_ATT_ENDPOINT
#include "s81_sim_only_attention_endpoint.hpp"
using DsromS81AttentionEndpoint=DsromS81SimOnlyAttentionEndpoint;
#else
class VDsromAttEngine;
using DsromS81AttentionEndpoint=VDsromAttEngine;
#endif
class VDsromWindowBlocks;
#ifdef DSROM_S81_NATIVE_WINDOW_LA
class VDsromS81WindowLa;
using VDsromPackedWindow=VDsromS81WindowLa;
#else
class VDsromPackedWindow;
#endif
class VDsromS81CkvRank0;
class VDsromS81CkvRank1;
class VDsromS81CkvRank2;
class VDsromS81CkvRank3;
namespace dsrom_s81_minimum {
using L20NativeCkv=std::variant<std::shared_ptr<VDsromS81CkvRank0>,
    std::shared_ptr<VDsromS81CkvRank1>,std::shared_ptr<VDsromS81CkvRank2>,
    std::shared_ptr<VDsromS81CkvRank3>>;
struct L20KvRankBinding {
    DsromS81MinimumRuntime* runtime=nullptr;
    uint64_t identity=0;
    PrefixPublication* publication=nullptr;
    DsromS81MinimumSourceIo io;
    DsromS81MinimumSourceTags tags;
    DsromS81NativeSuPorts* su=nullptr;
    DsromS81NativeQeQuantizerPorts* quantizer=nullptr;
    std::shared_ptr<VDsromAttention> adapter;
    std::shared_ptr<DsromS81AttentionEndpoint> endpoint;
    // Existing native descriptor authority; never a generated host lease.
    DsromS81PrefixNativeEngine descriptor;
    std::function<uint16_t()> native_generation;
    // Actual source owner drives descriptor, authorized priming/user/region
    // pins. Called on the shared low edge, never a private clock/reset.
    std::function<void(VDsromPackedWindow&,VDsromWindowBlocks&)> join_window_owner;
    // Positive Popper global512 publication at VM447360; lease is checked too.
    std::function<bool()> selected_ids_published;
    std::function<uint32_t(unsigned)> source_dynamic;
    std::string prior_hbm_directory,prior_ckv_directory;
};
// Component constructors reuse completed models. No runtime auto-enrollment:
// caller nests returned engines and registers each separate participant once.
class L20KvFactory {
    struct Impl;
    std::shared_ptr<Impl> impl;
public:
    // DSROM_S81_SIM_ONLY_KV_SOURCE=1 permits explicitly labeled missing
    // descriptor/prime and TP4 callbacks in this existing factory. Supplied
    // callbacks remain authoritative. Fallback captures actual source literal
    // index as a SIM_ONLY tag, not native desc_gen; payloads remain native.
    // TP4 callback binds existing native transport directly to these actual
    // service ports. It MUST supply real ag_tx_ready/peer inputs, never tied1.
    L20KvFactory(std::array<L20KvRankBinding,4>,
        std::function<void(const std::array<L20NativeCkv,4>&)> actual_tp4_join,
        bool enable_native=false);
    DsromS81PrefixNativeEngine real_kv(unsigned rank)const;
    DsromS81PrefixNativeEngine attention(unsigned rank)const;
    DsromS81PrefixNativeEngine bind_su(unsigned rank,DsromS81PrefixNativeEngine)const;
    std::vector<DsromS81MinimumParticipant> participants()const;
    void join();
    bool drained()const;
    const std::array<L20NativeCkv,4>& services()const;
};
// Existing minimum caller dispatches this actual four-rank component run.
int run_minimum_l20_kv(DsromS81MinimumRuntime&,const char* output);
} // namespace dsrom_s81_minimum
