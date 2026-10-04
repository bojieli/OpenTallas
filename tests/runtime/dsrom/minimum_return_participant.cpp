// New participant test using existing real branch/root models and bounded raw
// seeds. Not a source phase, numerical full-field or VM publication campaign.
#include "verilated.h"
#include "Vretn.h"
#include "Vroot.h"
#include "s81_minimum_return_participant.hpp"
#include <cassert>
#include <iostream>
using namespace dsrom_s81_minimum;
int main() {
    VerilatedContext ctx;ctx.threads(1);
    DsromS81MinimumRuntime runtime{};runtime.context=&ctx;
    runtime.stage=0;runtime.rank=0;runtime.pair=0;
    long cycles=0;runtime.cycle=[&](){return cycles;};
    NativeReturnParticipant<Vretn,Vroot> ret(runtime,
        [](const ReturnPhaseBinding& b,const CaptureOwner& s){
            std::array<uint32_t,8> tag{};
            // Explicit UNIT-test owner tuple only, not a production TAG227 layout.
            tag[0]=uint32_t(b.identity);tag[1]=s.element_address;tag[2]=s.row;
            return tag;
        });
    auto p=ret.participant();
    p.prepare({});p.rising(false);p.falling(false);
    runtime.identity=17;
    ReturnPhaseBinding b{};b.stage=0;b.rank=0;b.pair=0;b.root=0;
    b.identity=17;b.phrom0=uint64_t(2)<<46;b.phrom1=2;b.format=1;
    b.output_base=1024;b.output_position_stride=2;b.emitted_key="unit-test-only";
    b.source_matrix_sha256=std::string(64,'a');b.cfg_path="unit-test-only";
    b.region_pair_begin=0;b.region_pair_end=18;b.branch_a_leaf=0;b.branch_b_leaf=1;b.component_rows={0,1};
    ret.admit(b);
    DsromS81PairResult r{};r.valid=3;r.segment_counts=2|(2<<5);r.segments=1<<5;
    r.values=uint64_t(0x40000000)<<32|0x3f800000; // 1+2 ->3
    p.prepare(r);p.rising(true);p.falling(true);cycles++;
    r.rows=1|(1<<16);r.values=0x8000000080000000ull; // retained adder canonicalizes sum zero to +0
    p.prepare(r);p.rising(true);p.falling(true);cycles++;
    for(unsigned i=0;i<80 && ret.received()!=2;i++) {
        const auto captured_before_prepare=ret.received();
        p.prepare({});
        assert(ret.received()==captured_before_prepare); // no pre-edge capture forwarding
        p.rising(true);p.falling(true);cycles++;
    }
    assert(!ret.fault() && ret.expected()==2 && ret.received()==2);
    assert(ret.committed()==0 && !ret.local_drained());
    auto commands=ret.supply({});
    assert(commands[0] && commands[0]->source.row==0);
    assert(commands[0]->word.data[0]==0x40400000);
    // Actual root completion supplies a pending command; absence of ACK
    // cannot retire it. Acceptance exposes the second row but is not visible.
    ret.accepted(0,*commands[0]);
    auto next=ret.supply({});
    assert(next[0] && next[0]->source.row==1 && next[0]->word.data[1]==0);
    assert(ret.committed()==0 && !ret.local_drained());
    ret.warm_quarantine();assert(ret.fault() && ret.received()==2 && ret.committed()==0);
    bool refused=false;try{ret.supply({});}catch(...){refused=true;}
    assert(refused);
    std::cout<<"PASS SEEDED_NATIVE_RETURN_PARTICIPANT rows=2 no_VM_ACK_no_retirement cycles="<<cycles<<"\n";
}
