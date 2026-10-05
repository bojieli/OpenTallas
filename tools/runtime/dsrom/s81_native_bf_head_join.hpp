#pragma once
#include "s81_minimum_runtime.hpp"
#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <stdexcept>

namespace dsrom_s81_minimum {
// Borrow the ACTUAL ot_s81_native_head_tp4 model and Peirce's
// NativeBfHeadRoots type. This is host port wiring, not another engine, reader,
// command ABI or clock owner. Source keeps both roots until offer returns true.
// The existing native model still owns frame start, logit credit and result ACK.
// Pricing: no new RTL state/ports/cycles. Four host held input records plus
// pending/taken flags model the existing in_valid hold; they are not additional
// hardware credits. Native 16-seat logit storage/ports are already priced in
// dsrom_s81_native_head_carried. No numerical or physical gain is asserted.
template<class NativeTop,class Roots> class NativeBfHeadRootJoin {
    DsromS81MinimumRuntime& runtime;
    NativeTop& native;
    std::array<std::optional<Roots>,4> held;
    std::array<bool,4> taken{},fire{};
    const bool enabled;
    bool prepared=false,sampled=false,stopped=false;
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    static bool same(const Roots& a,const Roots& b) {
        return a.identity==b.identity&&a.request_sequence==b.request_sequence&&
            a.rank==b.rank&&a.local_row==b.local_row&&
            a.root4096==b.root4096&&a.root1024==b.root1024;
    }
    template<class Packed>
    static void put(Packed& p,unsigned offset,unsigned width,uint64_t value) {
        for(unsigned i=0;i<width;++i) {
            const uint32_t bit=uint32_t(1)<<((offset+i)%32);
            p[(offset+i)/32]=(p[(offset+i)/32]&~bit)|
                (((value>>i)&1)?bit:0);
        }
    }
    void healthy() const {
        require(!stopped&&!native.fault,"actual native head root join fault; held roots retained");
    }
public:
    NativeBfHeadRootJoin(DsromS81MinimumRuntime& rt,NativeTop& actual_native,bool enable=false)
        :runtime(rt),native(actual_native),enabled(enable) {
        require(rt.context&&native.contextp()==rt.context,
                "head root join requires actual shared native context");
    }
    // Pass directly as NativeBfHeadProducer's sink. Called between shared
    // edges by its existing advance(), never from prepare/rising/falling.
    bool offer(const Roots& roots) {
        if(!enabled)return false;
        try {
            healthy();require(!prepared&&!sampled,"head root offer during shared edge");
            require(roots.rank<4&&roots.local_row<32320&&roots.identity<(1ull<<47)&&
                runtime.identity&&*runtime.identity==roots.identity,
                "actual held head root source identity/rank/row required");
            const unsigned r=roots.rank;
            if(!held[r]) {held[r]=roots;taken[r]=false;return false;}
            require(same(*held[r],roots),"head producer changed roots before actual accepted edge");
            if(!taken[r])return false;
            held[r].reset();taken[r]=false;
            return true; // only a recorded real native rising acceptance
        } catch(...) {stopped=true;throw;}
    }
    void drive_before_edge() {
        if(!enabled)return;
        try {
            healthy();require(!prepared&&!sampled,"head root edge reused");
            native.in_valid=0;
            for(unsigned r=0;r<4;++r)if(held[r]&&!taken[r]) {
                const auto& c=*held[r];
                require(runtime.identity&&*runtime.identity==c.identity,
                        "accepted source context changed while roots held");
                put(native.in_owner,r*47,47,c.identity);
                put(native.in_sequence,r*64,64,c.request_sequence);
                put(native.in_row,r*17,17,r*32320+c.local_row);
                put(native.root4096,r*32,32,c.root4096);
                put(native.root1024,r*32,32,c.root1024);
                native.in_valid|=uint8_t(1u<<r);
            }
            prepared=true;
        } catch(...) {stopped=true;throw;}
    }
    // After actual leaf prepare settles low-clock ports, BEFORE it rises.
    void sample_before_edge() {
        if(!enabled)return;
        try {
            healthy();require(prepared&&!sampled,"head root edge not driven/settled");
            for(unsigned r=0;r<4;++r)fire[r]=((native.in_valid&native.in_ready)>>r)&1;
            sampled=true;
        } catch(...) {stopped=true;throw;}
    }
    // AFTER the existing native model's actual rising evaluation. No eval here.
    void after_edge() {
        if(!enabled)return;
        try {
            healthy();require(prepared&&sampled,"head root edge not sampled");
            for(unsigned r=0;r<4;++r)if(fire[r]) {
                require(held[r]&&!taken[r],"native head accepted unowned/duplicate roots");
                taken[r]=true;
            }
            prepared=false;sampled=false;
        } catch(...) {stopped=true;throw;}
    }
    bool fault() const {return enabled&&(stopped||bool(native.fault));}
    // Register FIRST, before the actual head leaf's existing clock owner.
    // This drives prepare, samples first rising, and records first falling
    // after all actual rising evaluations. It never clocks/evals the model.
    DsromS81MinimumParticipant participant() {
        return {"native-BF-head-root-accepted-join",
            [this](const DsromS81PairResult&) {
                if(!enabled)return;
                if(runtime.identity)drive_before_edge();
                else {
                    for(const auto& h:held)require(!h,"cold reset with held head roots");
                    native.in_valid=0;
                }
            },
            [this](bool released) {
                if(!released)require(!prepared&&!sampled,"reset with admitted head root debt");
                else if(prepared)sample_before_edge();
            },
            [this](bool released){if(released&&prepared)after_edge();},
            [this](){return fault();}
        };
    }
};
} // namespace dsrom_s81_minimum
