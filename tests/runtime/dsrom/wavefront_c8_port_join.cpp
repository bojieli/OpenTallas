#include "s81_wavefront_c8_port_join.hpp"
#include <cassert>

// Caller state-machine unit test. These literal ports are NOT a substitute
// controller or a native WAVE behavioral/physical qualification.
struct Ports {
    bool wf_request=false,wf_stage_accepted=false,wf_reject=false,wf_squash=false,wf_stage_done=false;
    uint32_t wf_token=0,wf_pos=0,wf_user=0,wf_stage_next_token=0,wf_stage_next_val=0;
};
int main() {
    Ports p;
    unsigned started=0,retired=0,invalidated=0;
    bool visible=false;
    bool incoming_result=false;
    unsigned consumed=0;
    uint64_t last_identity=0;
    DsromS81WaveC8PortJoin<Ports> join(p,
        [](const auto& r) {
            return DsromC8SourceOffer{0,r.token,r.position,r.user,3,7,
                (uint64_t(3)<<31)|(uint64_t(r.user)<<21)|r.position};
        },
        [&](const auto& r,const auto& offer) {
            assert(r.user==4+started);last_identity=offer.identity;started++;
        },
        [&](const auto& r,const auto& o)->std::optional<DsromS81WaveStageResult> {
            if(!visible)return std::nullopt;
            return DsromS81WaveStageResult{r.sequence,o.identity,13,0x3f800000};
        },
        [&](const auto& r){assert(r.identity==last_identity);retired++;},
        [&]()->std::optional<DsromS81WaveResultOrigin>{
            if(!incoming_result)return std::nullopt;
            return DsromS81WaveResultOrigin{(uint64_t(3)<<31)|(uint64_t(8)<<21)|17,8,17};
        },
        [&](const auto& owner,bool reject,bool squash) {
            assert(owner.user==8&&owner.position==17&&reject&&!squash);invalidated++;
        },true,[&](const auto& owner){assert(owner.user==8&&owner.position==17);consumed++;});
    // Pre-edge user is stale. The native controller updates it on issue edge.
    p.wf_request=true;p.wf_token=12;p.wf_pos=9;p.wf_user=2;
    join.drive();join.sample_before_edge();p.wf_user=4;join.after_edge();
    assert(started==1&&join.pending());
    p.wf_request=false;join.drive();assert(!p.wf_stage_done);
    join.sample_before_edge();join.after_edge();assert(!retired);
    visible=true;join.drive();assert(p.wf_stage_done);
    join.sample_before_edge();join.after_edge();assert(!retired); // no acceptance
    // Actual acceptance and a NEW request may share the edge. Rejection
    // belongs to incoming result user8, not the newly issued user5.
    p.wf_stage_accepted=true;p.wf_request=true;p.wf_token=13;p.wf_pos=10;
    incoming_result=true;
    join.drive();join.sample_before_edge();p.wf_user=5;p.wf_reject=true;
    join.after_edge();assert(retired==1&&started==2&&invalidated==1&&consumed==1&&join.pending());
    join.warm_quarantine();assert(join.pending()&&join.fault());
    bool refused=false;try{join.drive();}catch(const std::runtime_error&){refused=true;}
    assert(refused);
}
