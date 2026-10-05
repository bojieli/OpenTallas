#include "s81_wavefront_c8_group_step.hpp"
#include <vector>
#include <cassert>

// Source dispatch bookkeeping unit only; no native RTL simulation claimed.
struct PortFixture {
    bool valid=false,has_context=false,retired=false,restored=false;
    uint64_t identity=0;
    uint32_t token=0;
    uint16_t entry=0;
    bool fault(){return false;}
    bool c8_ready(){return !has_context;}
    void c8_restored(bool v){restored=v;}
    void c8_offer(bool v,uint32_t t,uint32_t p,uint32_t u,uint16_t e,uint16_t pc) {
        valid=v;token=t;entry=pc;identity=(uint64_t(e)<<31)|(uint64_t(u)<<21)|p;
    }
    bool c8_context(uint64_t& i,uint32_t& t,uint16_t& e) {
        i=identity;t=token;e=entry;return has_context;
    }
    bool c8_retired(uint64_t& i){i=identity;return retired;}
};
struct RuntimeFixture {int stage=2;std::vector<PortFixture*> dies;};
int main() {
    constexpr uint64_t id=(uint64_t(3)<<31)|(uint64_t(5)<<21)|9;
    std::array<DsromC8SourceOffer,4> offers{{
        {11,17,9,5,3,13,id},{9,17,9,5,3,14,id},
        {8,17,9,5,3,15,id},{10,17,9,5,3,16,id}}};
    unsigned accepted=0;
    DsromS81C8GroupStep step(offers,[&](const auto& offer){assert(offer.identity==id);accepted++;});
    std::array<PortFixture,4> ports{};
    RuntimeFixture runtime;for(auto& p:ports)runtime.dies.push_back(&p);
    unsigned restores=0,drains=0;
    auto restore=[&](const auto&){restores++;return true;};
    bool visible=false;
    auto drain=[&](const auto&){drains++;return visible;};
    assert(step.before_edge(runtime,restore,drain));
    assert(!accepted); // offered requests have not crossed a shared edge
    for(auto& p:ports){assert(p.valid);p.has_context=true;}
    step.after_edge();assert(!step.complete()&&accepted==4);
    assert(step.before_edge(runtime,restore,drain));assert(restores==4);
    for(auto& p:ports){assert(p.restored);p.retired=true;}
    step.after_edge();
    assert(step.before_edge(runtime,restore,drain));assert(!step.complete()&&drains==4);
    step.after_edge();visible=true;
    assert(!step.before_edge(runtime,restore,drain)&&step.complete());
    assert(accepted==4); // restoration/retires never create new accept entries
    bool refused=false;try{step.after_edge();}catch(const std::runtime_error&){refused=true;}
    assert(refused); // no clock/acceptance after completed group
    offers[3]=offers[0];refused=false;
    try{DsromS81C8GroupStep duplicate(offers);}catch(const std::runtime_error&){refused=true;}
    assert(refused);
    // Old ready/offer alone must not insert a RESULT generation when the
    // native post-edge context did not actually latch the offered tuple.
    std::array<PortFixture,4> unlatched{};
    RuntimeFixture missing;for(auto& p:unlatched)missing.dies.push_back(&p);
    unsigned false_accepts=0;
    const std::array<DsromC8SourceOffer,4> valid{{
        {8,17,9,5,3,13,id},{9,17,9,5,3,14,id},
        {10,17,9,5,3,15,id},{11,17,9,5,3,16,id}}};
    DsromS81C8GroupStep checked(valid,[&](const auto&){false_accepts++;});
    assert(checked.before_edge(missing,restore,drain));
    refused=false;try{checked.after_edge();}catch(const std::runtime_error&){refused=true;}
    assert(refused&&checked.fault()&&!false_accepts);
}
