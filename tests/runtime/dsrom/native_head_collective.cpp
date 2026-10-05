#include "s81_native_head_collective.hpp"
#include <cassert>

// Transport-only source connection check. These port fixtures do not model
// arithmetic, produce trained logits or qualify the native head/TOKEN.
struct Ports {
    bool native_head_selected=true,native_result_selected=true,fault=false;
    bool head_dn_valid=false,head_dn_last=true,head_dn_ready=false;
    bool head_up_valid=false,head_up_last=false,head_up_ready=true;
    bool head_final_valid=false,head_final_ready=true;
    uint64_t head_dn_identity=0,head_up_identity=0,head_final_identity=0;
    std::array<uint32_t,16> head_dn_data{},head_up_data{},head_final_data{};
};
int main() {
    std::array<Ports,4> p;
    const uint64_t owner=0x12345678901ull;
    std::array<uint32_t,16> packet{};
    packet[0]=6u<<16;packet[3]=0x80000000;packet[4]=96800;packet[5]=1;
    for(auto& r:p){r.head_dn_identity=owner;r.head_dn_data=packet;}
    p[0].head_dn_valid=true;
    auto c=dsrom_s81_bind_native_head_collective(p[0],p[1],p[2],p[3],owner,
                                                {2,3,2},{3,2,1,1},true);
    std::array<unsigned,4> final_acks{},up_acks{};
    std::array<bool,3> output_next{};
    for(uint64_t edge=0;edge<24;++edge) {
        p[2].head_final_ready=edge>=20;
        for(unsigned r=1;r<4;++r) {
            if(output_next[r-1])p[r].head_dn_valid=true;
            output_next[r-1]=false;
        }
        c.drive_before_edge(edge); // actual caller settles before sample
        c.sample_before_edge();
        for(unsigned r=0;r<4;++r) {
            if(p[r].head_dn_valid&&p[r].head_dn_ready)p[r].head_dn_valid=false;
            if(p[r].head_up_valid&&p[r].head_up_ready) {
                assert(p[r].head_up_identity==owner&&p[r].head_up_data==packet);
                assert((edge==std::array<uint64_t,4>{0,2,6,9}[r]));
                assert(p[r].head_up_last);++up_acks[r];
                output_next[r-1]=true;
            }
            if(p[r].head_final_valid&&p[r].head_final_ready) {
                assert(p[r].head_final_identity==owner&&p[r].head_final_data==packet);
                assert((edge==std::array<uint64_t,4>{13,12,20,11}[r]));
                ++final_acks[r];
            }
        }
        c.after_edge();
        if(edge<20)assert(!c.complete());
    }
    assert(c.complete()&&!c.fault());
    for(unsigned r=0;r<4;++r)assert(final_acks[r]==1);
    for(unsigned r=1;r<4;++r)assert(up_acks[r]==1);
    // A foreign retained identity is refused on the actual send edge.
    std::array<Ports,4> wrong;
    for(auto& r:wrong){r.head_dn_data=packet;r.head_dn_identity=owner+1;}
    wrong[0].head_dn_valid=true;
    auto bad=dsrom_s81_bind_native_head_collective(wrong[0],wrong[1],wrong[2],wrong[3],
                                                owner,{1,1,1},{1,1,1,1},true);
    bad.drive_before_edge(0);
    bool caught=false;
    try{bad.sample_before_edge();}catch(const std::runtime_error&){caught=true;}
    assert(caught&&bad.fault());
    // Default off does not drive ports or require the hardware opt-in.
    for(auto& r:wrong){r.native_head_selected=false;r.native_result_selected=false;}
    auto off=dsrom_s81_bind_native_head_collective(wrong[0],wrong[1],wrong[2],wrong[3],
                                                owner,{1,1,1},{1,1,1,1});
    off.drive_before_edge(0);off.sample_before_edge();off.after_edge();
    assert(!off.complete());
    // Bind the existing runtime callbacks without introducing another clock.
    DsromS81MinimumRuntime runtime{};long cycle=0;
    runtime.cycle=[&](){return cycle;};
    auto shared=std::make_shared<DsromS81NativeHeadCollective>(std::move(off));
    auto participant=dsrom_s81_native_head_collective_participant(runtime,shared,owner);
    participant.prepare({});participant.rising(false);participant.falling(false);
    runtime.identity=owner;
    participant.prepare({});participant.rising(true);participant.falling(true);++cycle;
    assert(!participant.fault()&&!shared->complete());
}
