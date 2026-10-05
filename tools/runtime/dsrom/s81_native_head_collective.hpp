#pragma once
#include "s81_minimum_runtime.hpp"
#include <array>
#include <cstdint>
#include <functional>
#include <memory>
#include <optional>
#include <stdexcept>
#include <utility>

// The existing native head ports, not a new ownership/command ABI. Identity is
// the actual held C8 identity; the enclosing source owner retains its sequence.
struct DsromS81NativeHeadRecord {
    std::array<uint32_t,16> data{};
    uint64_t identity=0;
    bool last=false;
};
struct DsromS81NativeHeadPorts {
    std::function<std::optional<DsromS81NativeHeadRecord>()> downstream;
    std::function<bool()> upstream_ready,final_ready,fault;
    std::function<void(const DsromS81NativeHeadRecord*,bool)> drive;
    std::function<void(const DsromS81NativeHeadRecord*)> final;
};

template<class Top>
DsromS81NativeHeadPorts dsrom_s81_native_head_ports(Top& top) {
    return {
        [&top]() -> std::optional<DsromS81NativeHeadRecord> {
            if(!top.head_dn_valid)return std::nullopt;
            DsromS81NativeHeadRecord r;
            for(unsigned i=0;i<16;++i)r.data[i]=top.head_dn_data[i];
            r.identity=uint64_t(top.head_dn_identity);r.last=top.head_dn_last;
            return r;
        },
        [&top](){return bool(top.head_up_ready);},
        [&top](){return bool(top.head_final_ready);},
        [&top](){return bool(top.fault);},
        [&top](const DsromS81NativeHeadRecord* r,bool ready) {
            top.head_up_valid=r!=nullptr;top.head_dn_ready=ready;
            top.head_up_last=r?r->last:false;
            top.head_up_identity=r?r->identity:0;
            for(unsigned i=0;i<16;++i)top.head_up_data[i]=r?r->data[i]:0;
        },
        [&top](const DsromS81NativeHeadRecord* r) {
            top.head_final_valid=r!=nullptr;
            top.head_final_identity=r?r->identity:0;
            for(unsigned i=0;i<16;++i)top.head_final_data[i]=r?r->data[i]:0;
        }
    };
}

// The minimum TOKEN runtime may bind the SAME selected head leaf directly,
// beside the retained pair/return archives, without compiling a whole core.
// Its write_* ports must be driven only by actual accepted native FP32 returns.
template<class NativeAmax>
DsromS81NativeHeadPorts dsrom_s81_native_head_amax_ports(NativeAmax& native) {
    return {
        [&native]() -> std::optional<DsromS81NativeHeadRecord> {
            if(!native.downstream_valid)return std::nullopt;
            DsromS81NativeHeadRecord r;
            for(unsigned i=0;i<16;++i)r.data[i]=native.downstream_data[i];
            r.identity=uint64_t(native.downstream_identity);r.last=native.downstream_last;
            return r;
        },
        [&native](){return bool(native.upstream_ready);},
        [&native](){return bool(native.final_ready);},
        [&native](){return bool(native.fault);},
        [&native](const DsromS81NativeHeadRecord* r,bool ready) {
            native.upstream_valid=r!=nullptr;native.downstream_ready=ready;
            native.upstream_last=r?r->last:false;
            native.upstream_identity=r?r->identity:0;
            for(unsigned i=0;i<16;++i)native.upstream_data[i]=r?r->data[i]:0;
        },
        [&native](const DsromS81NativeHeadRecord* r) {
            native.final_valid=r!=nullptr;native.final_identity=r?r->identity:0;
            for(unsigned i=0;i<16;++i)native.final_data[i]=r?r->data[i]:0;
        }
    };
}

// Finite one-record deterministic-release lines, as in the retained W15
// runtime transport. Caller supplies its actual selected latency in SHARED
// edge units; no zero-latency default or physical timing claim is supplied.
// Do not also connect these head ports to another collector/clock participant.
class DsromS81NativeHeadCollective {
    struct Seat { std::optional<DsromS81NativeHeadRecord> record;uint64_t due=0; };
    std::array<DsromS81NativeHeadPorts,4> ports;
    const uint64_t identity;
    const std::array<uint64_t,3> link_latency;
    const std::array<uint64_t,4> final_latency;
    std::array<Seat,3> links;
    std::optional<DsromS81NativeHeadRecord> global;
    std::array<uint64_t,4> global_due{};
    std::array<bool,4> delivered{};
    std::array<bool,3> up_fire{};
    std::array<bool,4> final_fire{},dn_ready{};
    std::array<std::optional<DsromS81NativeHeadRecord>,4> dn_fire;
    uint64_t edge=0;
    std::optional<uint64_t> previous_edge;
    bool enabled,driven=false,sampled=false,stopped=false,finished=false;
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    void healthy() const {
        require(!stopped,"native head collective quarantined; accepted records retained");
        for(const auto& p:ports)require(!p.fault(),"actual native head/core fault");
    }
    void check(const DsromS81NativeHeadRecord& r) const {
        require(r.identity==identity && r.last && ((r.data[0]>>16)&15)==6 &&
                (r.data[5]&1) && r.data[4]<129280,
                "native head record has wrong held owner/type/global ID");
    }
    static uint64_t due(uint64_t now,uint64_t latency) {
        require(now<=UINT64_MAX-latency,"native head transport cycle overflow");
        return now+latency;
    }
public:
    DsromS81NativeHeadCollective(std::array<DsromS81NativeHeadPorts,4> actual_ports,
        uint64_t actual_held_identity,std::array<uint64_t,3> actual_link_latency,
        std::array<uint64_t,4> actual_final_latency,bool enable=false)
        :ports(std::move(actual_ports)),identity(actual_held_identity),
         link_latency(actual_link_latency),final_latency(actual_final_latency),enabled(enable) {
        require(identity<(1ull<<47),"actual held C8 identity bounds");
        for(const auto& p:ports)require(p.downstream&&p.upstream_ready&&p.final_ready&&
            p.fault&&p.drive&&p.final,"four actual native head port bindings required");
        for(auto n:link_latency)require(n>0,"actual carried-link latency required");
        for(auto n:final_latency)require(n>0,"actual global delivery latency required");
    }
    // Caller ordering: drive -> settle ALL native models -> sample -> ONE
    // existing shared rising edge -> after_edge. Never eval/tick/reset here.
    void drive_before_edge(uint64_t actual_shared_cycle) {
        if(!enabled)return;
        try {
            healthy();require(!driven&&!sampled,"head transport edge reused");
            require(!previous_edge||(*previous_edge!=UINT64_MAX&&actual_shared_cycle==*previous_edge+1),
                    "head transport must observe every actual shared edge");
            edge=actual_shared_cycle;
            for(unsigned r=0;r<4;++r) {
                const auto* up=r&&links[r-1].record&&edge>=links[r-1].due ?
                    &*links[r-1].record:nullptr;
                dn_ready[r]=!finished && (r<3?!links[r].record:!global);
                ports[r].drive(up,dn_ready[r]);
                ports[r].final(global&&!delivered[r]&&edge>=global_due[r]?&*global:nullptr);
            }
            driven=true;
        } catch(...) {stopped=true;throw;}
    }
    void sample_before_edge() {
        if(!enabled)return;
        try {
            healthy();require(driven&&!sampled,"head transport edge not driven/settled");
            for(unsigned r=0;r<4;++r) {
                dn_fire[r]=dn_ready[r]?ports[r].downstream():std::nullopt;
                if(dn_fire[r])check(*dn_fire[r]);
                if(r)up_fire[r-1]=links[r-1].record&&edge>=links[r-1].due&&ports[r].upstream_ready();
                final_fire[r]=global&&!delivered[r]&&edge>=global_due[r]&&ports[r].final_ready();
            }
            sampled=true;
        } catch(...) {stopped=true;throw;}
    }
    void after_edge() {
        if(!enabled)return;
        try {
            healthy();require(driven&&sampled,"head transport edge was not sampled");
            for(unsigned r=0;r<3;++r) {
                if(up_fire[r])links[r].record.reset();
                if(dn_fire[r]) {
                    require(!links[r].record,"native carried link overwrote accepted frame");
                    links[r].record=dn_fire[r];links[r].due=due(edge,link_latency[r]);
                }
            }
            if(dn_fire[3]) {
                require(!global,"native global collector overwrote retained frame");
                global=dn_fire[3];
                for(unsigned r=0;r<4;++r)global_due[r]=due(edge,final_latency[r]);
            }
            for(unsigned r=0;r<4;++r)if(final_fire[r])delivered[r]=true;
            finished=global&&delivered[0]&&delivered[1]&&delivered[2]&&delivered[3];
            previous_edge=edge;driven=false;sampled=false;
        } catch(...) {stopped=true;throw;}
    }
    bool complete() const {return enabled&&finished&&!fault();}
    bool fault() const {if(stopped)return true;for(const auto& p:ports)if(p.fault())return true;return false;}
    void warm_quarantine(){stopped=true;} // retain all held native records
};

// Call with *actual Die<DIE>::d for ranks0..3, before DieBase erases the type.
template<class T0,class T1,class T2,class T3>
DsromS81NativeHeadCollective dsrom_s81_bind_native_head_collective(
    T0& r0,T1& r1,T2& r2,T3& r3,uint64_t held_identity,
    std::array<uint64_t,3> link_latency,std::array<uint64_t,4> final_latency,
    bool enable=false) {
    if(enable&&(!r0.native_head_selected||!r1.native_head_selected||
                !r2.native_head_selected||!r3.native_head_selected||
                !r0.native_result_selected||!r1.native_result_selected||
                !r2.native_result_selected||!r3.native_result_selected))
        throw std::runtime_error("selected native head and existing result exports required");
    return DsromS81NativeHeadCollective({dsrom_s81_native_head_ports(r0),
        dsrom_s81_native_head_ports(r1),dsrom_s81_native_head_ports(r2),
        dsrom_s81_native_head_ports(r3)},held_identity,link_latency,final_latency,enable);
}

// Register FIRST in runtime.participants, before the actual head leaf/core
// participants. Its prepare drives links; leaf prepare settles their low-clock
// combinational ports. Its rising samples all OLD ports before any leaf rises;
// falling retires the sampled transfers after ALL native rising evaluations.
// Thus this joins the existing shared tick rather than clocking another loop.
inline DsromS81MinimumParticipant dsrom_s81_native_head_collective_participant(
    DsromS81MinimumRuntime& runtime,
    std::shared_ptr<DsromS81NativeHeadCollective> collective,
    uint64_t held_identity) {
    if(!collective||!runtime.cycle)
        throw std::runtime_error("actual head collector and shared runtime cycle required");
    auto prepared=std::make_shared<bool>(false);
    return {"native-head-TP4-global-collector",
        [&runtime,collective,prepared,held_identity](const DsromS81PairResult&) {
            if(*prepared)throw std::runtime_error("head collector shared edge reused");
            if(!runtime.identity)return; // the one actual cold reset, before admission
            if(*runtime.identity!=held_identity||runtime.cycle()<0)
                throw std::runtime_error("head collector lost actual admitted source context");
            collective->drive_before_edge(uint64_t(runtime.cycle()));*prepared=true;
        },
        [collective,prepared](bool released) {
            if(!released) {
                if(*prepared)throw std::runtime_error("reset would clear admitted head transport debt");
            } else if(*prepared)collective->sample_before_edge();
        },
        [collective,prepared](bool released) {
            if(released&&*prepared){collective->after_edge();*prepared=false;}
        },
        [collective](){return collective->fault();}
    };
}
