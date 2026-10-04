#pragma once
#include "fullshape_context.hpp"
#include <array>
#include <cstdint>
#include <limits>
#include <stdexcept>

namespace qwen_combined {
// Testbench times are femtoseconds. They are explicit stimulus parameters,
// not timing closure or a conversion of software elapsed time to silicon time.
struct ClockSpec {
    uint64_t period_fs, first_rise_fs;
    void check() const {
        if (!period_fs || period_fs % 2 || !first_rise_fs)
            throw std::invalid_argument("positive even period and positive first rising edge required");
    }
};
struct Edges {
    uint64_t time_fs;
    bool core_changed, service_changed, core_high, service_high;
    bool core_rise() const { return core_changed && core_high; }
    bool service_rise() const { return service_changed && service_high; }
};
class ClockDriver {
    ClockSpec core_, service_;
    uint64_t next_core_, next_service_, now_=0, core_edges_=0, service_edges_=0;
    bool core_high_=false, service_high_=false;
    static uint64_t add(uint64_t a, uint64_t b) {
        if (b > std::numeric_limits<uint64_t>::max()-a)
            throw std::overflow_error("clock time overflow");
        return a+b;
    }
public:
    ClockDriver(ClockSpec core, ClockSpec service):core_(core),service_(service),
        next_core_(core.first_rise_fs),next_service_(service.first_rise_fs) {
        core.check();service.check();
    }
    Edges next() {
        const auto t=next_core_<next_service_?next_core_:next_service_;
        Edges e{t,next_core_==t,next_service_==t,core_high_,service_high_};
        // Advance both calendars before mutating either level, including ties.
        auto nc=next_core_,ns=next_service_;
        if(e.core_changed) nc=add(nc,core_.period_fs/2);
        if(e.service_changed) ns=add(ns,service_.period_fs/2);
        if(e.core_changed)e.core_high=!core_high_;
        if(e.service_changed)e.service_high=!service_high_;
        core_high_=e.core_high;service_high_=e.service_high;
        next_core_=nc;next_service_=ns;now_=t;
        core_edges_+=e.core_rise();service_edges_+=e.service_rise();
        return e;
    }
    // Binding owns one enclosing Verilated model, its time precision conversion,
    // actual CDC, all memory and payload ports. All changed clocks are assigned
    // BEFORE the single enclosing eval, so simultaneous edges have no host order.
    template<class Binding> Edges step(Binding& b) {
        auto e=next();b.set_time_fs(e.time_fs);
        b.drive_clocks(e.core_high,e.service_high);b.eval();return e;
    }
    uint64_t time_fs() const {return now_;}
    uint64_t core_rises() const {return core_edges_;}
    uint64_t service_rises() const {return service_edges_;}
};

// clk drives core, sequencer AND canonical REAL_MEM service. Independent
// hclk drives HBM controllers; the actual top owns request/response CDC.
// Snapshots are read from the actual enclosing RTL BEFORE a clock transition.
// They never generate memory responses, ready, drains, or the kv_arm register.
struct RankPins {
    bool reset_n,stage_start,core_start,kv_arm,kv_layer_start;
    bool service_reset_n,service_start;
    unsigned layer,pos,token,service_layer,service_pos;
    bool stage_done,kv_ok,write_drained,row_drained,fault;
};
class LayerFence {
    bool active_=false, expected_arm_=false, arm_known_=false;
    unsigned layer_=0,pos_=0,token_=0,core_starts_=0,kv_starts_=0,service_starts_=0;
public:
    void begin(unsigned layer,unsigned pos,unsigned token) {
        if(active_)throw std::logic_error("previous layer has not retired");
        Context{0,layer==255?0:layer,pos,token}.check();
        if(layer>=layers && layer!=255)throw std::invalid_argument("layer outside fullshape");
        active_=true;layer_=layer;pos_=pos;token_=token;
        core_starts_=kv_starts_=service_starts_=0;
    }
    void observe(const RankPins& p,const Edges& e) {
        if(p.fault)throw std::runtime_error("actual core/service fault");
        if(e.core_rise()) {
            if(!p.reset_n) {expected_arm_=false;arm_known_=true;}
            else {
                if(arm_known_ && p.kv_arm!=expected_arm_)
                    throw std::runtime_error("kv_arm differs from source per-layer recurrence");
                if(p.kv_layer_start!=(p.core_start && p.kv_arm && p.layer!=255))
                    throw std::runtime_error("KV layer start differs from source arm/core_start");
                if(p.stage_start && !active_)throw std::runtime_error("unowned stage start");
                if(p.core_start || p.stage_start) {
                    if(!active_ || p.layer!=layer_ || p.pos!=pos_ || p.token!=token_)
                        throw std::runtime_error("core stage identity mismatch");
                }
                if(p.core_start)++core_starts_;
                if(p.kv_layer_start && ++kv_starts_!=1)
                    throw std::runtime_error("KV rearmed within same layer");
                // Exactly ot_qwen_rom_rt_die_w12_rm: start wins over core_start.
                expected_arm_=p.stage_start?true:(p.core_start?false:p.kv_arm);
                arm_known_=true;
            }
        }
        if(e.core_rise() && p.service_reset_n && p.service_start) {
            if(!active_ || layer_==255 || p.service_layer!=layer_ || p.service_pos!=pos_)
                throw std::runtime_error("service start has wrong layer/position");
            if(++service_starts_!=1)throw std::runtime_error("duplicate accepted service start");
        }
    }
    bool can_retire(const RankPins& p) const {
        if(!active_ || p.fault || !p.stage_done || !core_starts_)return false;
        if(layer_==255)return kv_starts_==0 && service_starts_==0;
        return kv_starts_==1 && service_starts_==1 && p.kv_ok && p.write_drained && p.row_drained;
    }
    void retire(const RankPins& p) {
        if(!can_retire(p))throw std::runtime_error("layer done without actual KV ACK/row drain");
        active_=false;
    }
};

// Fullshape driver for the selected enclosing top. Binding must implement:
// check_geometry() (actual TP/G/SW/NW + REAL_MEM source selection), set_stage,
// pulse_stage_start(bool), sample(rank), set_time_fs, drive_clocks, eval.
// No payload handler, arithmetic, or readiness authority lives in this driver.
// There is no timeout/run cap; hardware faults fail immediately, finite waits
// remain in the actual model and are visible to the owning runtime.
template<class Binding> class CombinedDriver {
    Binding& b_;ClockDriver clocks_;std::array<LayerFence,ranks> fences_;
    bool active_=false,pulse_=false;
public:
    CombinedDriver(Binding& b,ClockSpec core,ClockSpec service):b_(b),clocks_(core,service) {
        b_.check_geometry();b_.drive_clocks(false,false);b_.pulse_stage_start(false);b_.eval();
    }
    void begin(unsigned layer,unsigned pos,unsigned token,bool drive_start=true) {
        if(active_)throw std::logic_error("stage overlap");
        Context{0,layer==255?0:layer,pos,token}.check();
        if(layer>=layers && layer!=255)throw std::invalid_argument("invalid layer");
        for(auto& f:fences_)f.begin(layer,pos,token);
        b_.set_stage(layer,pos,token);b_.pulse_stage_start(drive_start);b_.eval();
        active_=true;pulse_=drive_start;
    }
    Edges step() {
        std::array<RankPins,ranks> p;
        for(unsigned r=0;r<ranks;++r)p[r]=b_.sample(r);
        auto e=clocks_.next();
        for(unsigned r=0;r<ranks;++r)fences_[r].observe(p[r],e);
        b_.set_time_fs(e.time_fs);b_.drive_clocks(e.core_high,e.service_high);b_.eval();
        if(pulse_ && e.core_rise()) {b_.pulse_stage_start(false);b_.eval();pulse_=false;}
        return e;
    }
    bool ready_to_retire() const {
        if(!active_)return false;
        for(unsigned r=0;r<ranks;++r)if(!fences_[r].can_retire(b_.sample(r)))return false;
        return true;
    }
    void retire() {
        if(!ready_to_retire())throw std::runtime_error("TP4 layer completion not drained");
        for(unsigned r=0;r<ranks;++r)fences_[r].retire(b_.sample(r));
        active_=false;
    }
    const ClockDriver& clocks() const {return clocks_;}
};
} // namespace qwen_combined
