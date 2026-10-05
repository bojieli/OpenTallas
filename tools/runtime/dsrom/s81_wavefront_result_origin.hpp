#pragma once
#include <vector>
#include "s81_wavefront_c8_port_join.hpp"

// Actual OLD registered RESULT before its processing edge, not a new epoch.
struct DsromS81WaveResultKey {
    uint32_t user,position;
};

template<class Top> class DsromS81WaveResultOriginProvider {
public:
    // Borrow the actual accepted-source ledger: return its matching retained
    // RESULT generation/order, including legitimate stale squashed results.
    // Reject retired/replayed entries at the ledger; never choose newest epoch.
    // Zero/multiple candidates fail closed here, including duplicate entries.
    // No insertion/deletion/credit/visibility is authorized by this lookup.
    using Lookup=std::function<std::vector<DsromS81WaveResultOrigin>(const DsromS81WaveResultKey&)>;
private:
    Top& top;
    Lookup lookup;
    bool enabled;
    static void require(bool value,const char* why) {
        if(!value)throw std::runtime_error(why);
    }
public:
    DsromS81WaveResultOriginProvider(Top& t,Lookup accepted_owner,bool enable=false):
        top(t),lookup(std::move(accepted_owner)),enabled(enable) {
        require(bool(lookup),"WAVE RESULT requires actual accepted-source owner lookup");
    }
    // Use as Arch's ResultOrigin callback in sample_before_edge(), after settling
    // and BEFORE the sole caller's clock. The returned value survives that edge
    // in Arch's existing incoming snapshot; cur_user/tok_user are never read.
    std::optional<DsromS81WaveResultOrigin> operator()() const {
        if(!enabled||!top.wf_result_v||!top.wf_result_final)return std::nullopt;
        const DsromS81WaveResultKey old{uint32_t(top.wf_result_user),uint32_t(top.wf_result_pos)};
        require(old.user<(1u<<10)&&old.position<(1u<<21),"old RESULT wire bounds");
        const auto candidates=lookup(old);
        require(candidates.size()==1,"old RESULT accepted-source owner missing/ambiguous/duplicate");
        const auto owner=candidates.front();
        require(owner.identity<(uint64_t(1)<<47)&&owner.user==old.user&&owner.position==old.position&&
                ((owner.identity>>21)&1023)==old.user&&
                (owner.identity&((uint64_t(1)<<21)-1))==old.position,
                "old RESULT differs from accepted source ID47/user/position");
        return owner;
    }
};
