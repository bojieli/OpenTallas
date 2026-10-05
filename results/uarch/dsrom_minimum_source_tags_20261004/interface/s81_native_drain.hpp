#pragma once
#include <array>
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <stdexcept>
#include <vector>
#include <utility>
#include "dsrom_c8_source_dispatch.hpp"

// Software observer of the existing native host/RTL events. No clock, grant,
// ready, write ACK or reset is driven here. Never use host queue empty as proof.
struct DsromS81DrainSample {
    bool offer_accept=false, field_live=false, field_drained=false;
    bool vm_visible=false, retire=false, fault=false, warm_reset=false;
    uint64_t offered_identity=0, field_identity=0, retire_identity=0;
    uint32_t token=0, vm_commits=0;
    uint16_t entry=0;
    uint8_t pop_ucie=0, pop_board=0, return_ucie=0, return_board=0;
};

class DsromS81NativeDrain {
public:
    struct Span {uint32_t address,words;};
private:
    struct Binding {DsromC8SourceOffer offer;bool field;std::vector<Span> spans;};
    std::vector<Binding> bindings;
    struct Owner {
        bool accepted=false, field_seen=false, retired=false, visible=false;
        uint64_t identity=0, commits=0;
        uint32_t token=0;
        uint16_t entry=0;
        bool needs_field=false;
        std::vector<Span> spans;
    };
    struct Copy {
        uint64_t identity;
        bool injected=false, received=false, consumed=false, reversed=false, reverse_injected=false;
    };
    int stage;
    bool stopped=false;
    std::array<Owner,4> owners{};
    std::deque<Copy> links[4][4][2];
    std::deque<Copy> ckv[4][4];
    std::array<DsromS81DrainSample,4> before{};
    [[noreturn]] void fail(const char* reason) {
        stopped=true; throw std::runtime_error(reason);
    }
    void rank(int r) { if(r<0 || r>=4)fail("native drain rank bounds"); }
    bool transport_empty() const {
        for(int s=0;s<4;s++)for(int d=0;d<4;d++) {
            if(!ckv[s][d].empty())return false;
            for(int p=0;p<2;p++)if(!links[s][d][p].empty())return false;
        }
        return true;
    }
    bool group_complete() const {
        if(stopped || !transport_empty())return false;
        const auto& first=owners[0];
        for(const auto& o:owners)
            if(!o.accepted || !o.retired || !o.visible ||
               o.identity!=first.identity || o.token!=first.token)return false;
        for(const auto& o:owners)if(o.needs_field) {
            uint64_t expected=0;for(const auto& s:o.spans)expected+=s.words;
            if(!o.field_seen || !expected || o.commits!=expected)return false;
        }
        return true;
    }
    void matching(int s,int d) {
        rank(s);rank(d);
        if(s==d || !owners[s].accepted || !owners[d].accepted ||
           owners[s].identity!=owners[d].identity || owners[s].token!=owners[d].token)
            fail("native transport lacks matched accepted source/destination contexts");
    }
    void pop(int s,int d,int p) {
        matching(s,d);
        auto& q=links[s][d][p];
        for(auto& c:q)if(!c.consumed) {
            if(!c.received)fail("native parity pop has no accepted receive copy");
            c.consumed=true;trim(q);return;
        }
        fail("native parity pop without owned packet");
    }
    static void trim(std::deque<Copy>& q) {
        while(!q.empty() && q.front().received && q.front().consumed && q.front().reversed)
            q.pop_front();
    }
public:
    explicit DsromS81NativeDrain(int physical_stage):stage(physical_stage) {
        if(stage<0 || stage>=81)fail("native drain stage bounds");
    }
    void declare(DsromC8SourceOffer offer,bool field,std::vector<Span> spans) {
        if(offer.die_id/4!=stage)fail("receipt binding belongs to another physical stage");
        for(const auto& b:bindings)if(b.offer.die_id==offer.die_id &&
            b.offer.identity==offer.identity && b.offer.entry==offer.entry)
            {if(b.offer.token!=offer.token || b.field!=field)fail("ambiguous source receipt binding");return;}
        for(const auto& s:spans)if(!s.words || uint64_t(s.address)+s.words>(1u<<19))
            fail("source output VM19 span bounds");
        for(size_t i=0;i<spans.size();i++)for(size_t j=0;j<i;j++)
            if(uint64_t(spans[i].address)<uint64_t(spans[j].address)+spans[j].words &&
               uint64_t(spans[j].address)<uint64_t(spans[i].address)+spans[i].words)
                fail("compiled source output spans alias");
        bindings.push_back({offer,field,std::move(spans)});
    }
    void before_edge(const std::array<DsromS81DrainSample,4>& samples) {
        if(stopped)fail("native drain quarantined");
        bool admitting=false;
        for(const auto& e:samples)admitting=admitting || e.offer_accept;
        if(group_complete() && admitting)owners={};
        before=samples;
        for(int r=0;r<4;r++) {
            const auto& e=samples[r];auto& o=owners[r];
            if(e.fault || (e.warm_reset && o.accepted))fail("native drain fault/reset preserves accepted debt");
            if(e.offer_accept) {
                if(o.accepted)fail("new admission overlaps unresolved native owner");
                o.accepted=true;o.identity=e.offered_identity;o.token=e.token;o.entry=e.entry;
                const Binding* found=nullptr;
                for(const auto& b:bindings)if(b.offer.die_id==4*stage+r &&
                    b.offer.identity==o.identity && b.offer.token==o.token && b.offer.entry==o.entry)found=&b;
                if(!found)fail("native acceptance lacks literal source-program receipt binding");
                o.needs_field=found->field;o.spans=found->spans;
            }
            if(e.vm_commits) {
                if(!o.accepted || e.field_identity!=o.identity)
                    fail("native VM acceptance has no retained field owner");
                o.commits+=e.vm_commits;
            }
            if(e.field_live) {
                if(!o.accepted || e.field_identity!=o.identity)
                    fail("native field acceptance owner mismatch");
                o.field_seen=true;
            }
        }
    }
    void after_edge(const std::array<DsromS81DrainSample,4>& samples) {
        for(int r=0;r<4;r++) {
            const auto& e=samples[r];auto& o=owners[r];
            if(e.fault || (e.warm_reset && o.accepted))fail("native edge fault retains all copy debt");
            if(e.field_live) {
                if(!o.accepted || e.field_identity!=o.identity)fail("native field owner changed");
                o.field_seen=true;
            }
            if(e.retire) {
                if(!o.accepted || e.retire_identity!=o.identity)fail("foreign native retirement");
                o.retired=true;
            }
            o.visible=o.accepted && e.field_identity==o.identity && e.field_drained &&
                      !e.field_live && e.vm_visible;
        }
        // Mark writes accepted on THIS edge before attributing native pops;
        // a source FIFO with a same-edge lookahead remains correctly causal.
        for(int s=0;s<4;s++)for(int d=0;d<4;d++)if(s!=d) {
            for(int p=0;p<2;p++)for(auto& c:links[s][d][p])
                if(c.injected)c.received=true;
            auto& q=ckv[s][d];
            while(!q.empty() && q.front().injected)q.pop_front();
        }
        // Credit bits sampled BEFORE the rising edge are literal accepted
        // parity-FIFO pops (CL_RELAY=0); post-edge predictions are not receipts.
        for(int d=0;d<4;d++)for(int s=0;s<4;s++)if(s!=d) {
            unsigned bits=(s==(d^1)) ? before[d].pop_ucie :
                          ((before[d].pop_board>>(2*(s%2)))&3);
            for(int p=0;p<2;p++)if(bits&(1u<<p))pop(s,d,p);
        }
        // Reverse line delivery merely stages an input. Release its retained
        // copy only when the original sender actually accepts that credit on
        // this rising edge (cr_in is unconditionally added by native RTL).
        for(int s=0;s<4;s++)for(int d=0;d<4;d++)if(s!=d) {
            unsigned bits=(d==(s^1)) ? before[s].return_ucie :
                          ((before[s].return_board>>(2*(d%2)))&3);
            for(int p=0;p<2;p++)if(bits&(1u<<p)) {
                auto& q=links[s][d][p];bool found=false;
                for(auto& c:q)if(!c.reversed) {
                    if(!c.reverse_injected || !c.consumed)fail("reverse credit lacks native consumer receipt");
                    c.reversed=true;found=true;break;
                }
                if(!found)fail("native reverse credit without retained packet debt");
                trim(q);
            }
        }
    }
    void link_sent(int s,int d,int parity) {
        matching(s,d);if(parity<0 || parity>1)fail("native packet parity");
        links[s][d][parity].push_back({owners[s].identity});
    }
    void link_injected(int s,int d,int parity) {
        matching(s,d);auto& q=links[s][d][parity];
        for(auto& c:q)if(!c.injected){c.injected=true;return;}
        fail("foreign native link delivery");
    }
    void reverse_arrived(int source,int destination,unsigned parity_bits) {
        matching(source,destination);
        for(int p=0;p<2;p++)if(parity_bits&(1u<<p)) {
            auto& q=links[source][destination][p];bool found=false;
            for(auto& c:q)if(!c.reverse_injected){c.reverse_injected=true;found=true;break;}
            if(!found)fail("foreign/duplicate reverse parity receipt");
            trim(q);
        }
    }
    void ckv_sent(int s,int d) {matching(s,d);ckv[s][d].push_back({owners[s].identity});}
    void ckv_injected(int s,int d) {
        matching(s,d);for(auto& c:ckv[s][d])if(!c.injected){c.injected=true;return;}
        fail("foreign native CKV delivery");
    }
    bool drained(const DsromC8SourceOffer& offer) const {
        int r=offer.die_id-4*stage;
        if(r<0 || r>=4 || stopped)return false;
        const auto& o=owners[r];
        return o.identity==offer.identity && o.token==offer.token && o.entry==offer.entry && group_complete();
    }
    bool source_span_lease(int die,uint64_t identity,uint32_t address,size_t words) const {
        int r=die-4*stage;
        if(r<0 || r>=4 || !words || uint64_t(address)+words>(1u<<19) || !group_complete())return false;
        const auto& o=owners[r];if(o.identity!=identity || !o.needs_field)return false;
        // Cover the requested retained range by actual compiled output spans;
        // an identity match or unrelated unchanged VM word is insufficient.
        uint64_t at=address,end=uint64_t(address)+words;
        while(at<end) {
            uint64_t next=at;
            for(const auto& s:o.spans)if(s.address<=at && at<uint64_t(s.address)+s.words)
                next=std::max(next,uint64_t(s.address)+s.words);
            if(next==at)return false;
            at=next;
        }
        return true;
    }
};
