#include "s81_wavefront_result_origin.hpp"
#include <cassert>

// Boundary bookkeeping unit only: literal ports/ledger rows are fixtures,
// not native controller execution, accepted-source qualification or visibility.
struct Ports {
    bool wf_result_v=false,wf_result_final=false;
    uint32_t wf_result_user=8,wf_result_pos=17;
    bool wf_request=false,wf_stage_accepted=false,wf_reject=false,wf_squash=false,wf_stage_done=false;
    uint32_t wf_token=0,wf_pos=0,wf_user=99,wf_stage_next_token=0,wf_stage_next_val=0;
    uint32_t tok_user=77; // deliberately unrelated, never consulted by provider
};
static bool refuses(const std::function<void()>& f) {
    try{f();}catch(const std::runtime_error&){return true;}return false;
}
int main() {
    Ports p;
    using Origin=DsromS81WaveResultOrigin;
    const Origin old{(uint64_t(3)<<31)|(uint64_t(8)<<21)|17,8,17};
    std::vector<Origin> accepted{old};
    unsigned lookups=0;
    auto lookup=[&](const DsromS81WaveResultKey& key) {
        ++lookups;assert(key.user==8&&key.position==17);return accepted;
    };
    DsromS81WaveResultOriginProvider<Ports> off(p,lookup);
    p.wf_result_v=p.wf_result_final=true;
    assert(!off()&&lookups==0);
    DsromS81WaveResultOriginProvider<Ports> provider(p,lookup,true);
    p.wf_result_final=false;assert(!provider()&&lookups==0); // partial result
    p.wf_result_final=true;assert(provider()->identity==old.identity);
    accepted.clear();assert(refuses([&]{provider();})); // missing/stale ledger
    accepted={old,old};assert(refuses([&]{provider();})); // duplicate
    accepted={old,Origin{old.identity+(uint64_t(1)<<31),8,17}};
    assert(refuses([&]{provider();})); // two retained generations, no newest guess
    accepted={old};accepted[0].identity^=1;assert(refuses([&]{provider();}));
    accepted={old};accepted[0].user=9;assert(refuses([&]{provider();}));
    accepted={old};accepted[0].position=18;assert(refuses([&]{provider();}));
    accepted={old};accepted[0].identity|=uint64_t(1)<<47;assert(refuses([&]{provider();}));
    accepted={old};p.wf_result_user=1024;assert(refuses([&]{provider();}));p.wf_result_user=8;
    // Use EXACT Arch caller: pre-edge OLD RESULT belongs to user8/epoch3,
    // while stage user4 completes and new user5 issues on the same edge.
    unsigned starts=0,retires=0,squashes=0;
    bool full_stage=false;
    DsromS81WaveC8PortJoin<Ports> join(p,
        [](const auto& r){return DsromC8SourceOffer{0,r.token,r.position,r.user,7,2,
                      (uint64_t(7)<<31)|(uint64_t(r.user)<<21)|r.position};},
        [&](const auto&,const auto&){++starts;},
        [&](const auto& r,const auto& offer)->std::optional<DsromS81WaveStageResult>{
            if(!full_stage)return std::nullopt;
            return DsromS81WaveStageResult{r.sequence,offer.identity,13,0x3f800000};},
        [&](const auto&){++retires;},[&]{return provider();},
        [&](const auto& owner,bool reject,bool squash){
            assert(owner.identity==old.identity&&owner.user==8&&owner.position==17);
            assert(!reject&&squash);++squashes;},true);
    p.wf_result_v=false;p.wf_request=true;p.wf_token=12;p.wf_pos=9;
    join.drive();join.sample_before_edge();p.wf_user=4;join.after_edge();
    assert(starts==1&&join.pending());
    full_stage=true;p.wf_stage_accepted=true;p.wf_token=13;p.wf_pos=10;
    p.wf_result_v=p.wf_result_final=true;
    join.drive();join.sample_before_edge();
    // Native ports change on the actual edge; callback must use the saved OLD sample.
    p.wf_user=5;p.wf_result_user=9;p.wf_result_pos=33;p.tok_user=77;
    p.wf_squash=true;join.after_edge();
    assert(starts==2&&retires==1&&squashes==1&&join.pending());
    join.warm_quarantine();assert(join.pending()&&join.fault());
}
