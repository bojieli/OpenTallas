#pragma once
#include "s81_minimum_runtime.hpp"
#include "s81_minimum_hbm_counters.hpp"
#include "VDsromS81Hbm.h"
#ifdef DSROM_S81_NATIVE_WINDOW_LA
#include "s81_minimum_window_la.hpp"
#endif
#include <memory>
#include <stdexcept>

// Caller owns the existing C8 mux; this participant clocks ONLY its native
// backend. Attach exactly once, before the shared cold reset/context admission.
// No model is built/clocked inside WINDOW or ME; no host response/write ACK.
namespace dsrom_s81_minimum {
class NativeHbm : public std::enable_shared_from_this<NativeHbm> {
    DsromS81MinimumRuntime& runtime;
    VDsromS81Hbm model;
    std::array<uint64_t,4> reads{},writes{};
    long prepared=-1;
    bool admitted=false;
    uint8_t accepted=0,returned=0,committed=0,write_mask=0;
    std::array<unsigned,4> lengths{},request_owner{},response_owner{};
    std::array<uint32_t,4> write_strobes{};
    NativeHbmTrafficCounters traffic_counters;
    std::function<void()> join;
#ifdef DSROM_S81_NATIVE_WINDOW_LA
    std::function<void()> wide_join;
    std::array<uint64_t,32> wide_reads{};
    std::array<unsigned,32> wide_lengths{};
    uint32_t wide_accepted=0,wide_returned=0;
#endif
public:
    explicit NativeHbm(DsromS81MinimumRuntime&,const std::string& instance);
    // Native sparse prior-history only; must precede shared cold_start/bind_context.
    void preload(const std::string& rank_history_directory);
    void preload_ckv(const std::string& rank_ckv_history_directory);
    NativeHbmTrafficSnapshot traffic()const;
    uint32_t capacity_words()const{return model.capacity_words;}
    bool ckv_initialized()const{return model.ckv_history_ready;}
    template<class Mux> void wire(Mux& mux) {
        static_assert(sizeof(mux.m_addr)==sizeof(model.m_addr),"HBM AW30 four-stack mismatch");
        static_assert(sizeof(mux.m_tag)==sizeof(model.m_tag),"HBM TAG16 four-stack mismatch");
        // C8 master tag high bits: 00 WINDOW, 01 CKV, 10 RoPE.
        // A caller omitting CKV init must not receive zero/default history.
        for(unsigned s=0;s<4;s++)
            if((mux.m_v&(1u<<s))&&((mux.m_tag>>(16*s+14))&3u)==1u&&
               !model.ckv_history_ready)
                throw std::runtime_error("actual CKV request before retained CKV history init");
        model.m_v=mux.m_v;model.m_we=mux.m_we;model.m_len=mux.m_len;model.m_tag=mux.m_tag;
        model.m_addr=mux.m_addr;model.m_wdata=mux.m_wdata;model.m_wstrb=mux.m_wstrb;
        model.s_rdy=mux.s_rdy;
#ifdef DSROM_S81_NATIVE_WINDOW_LA
        if(!wide_join)throw std::runtime_error("wide HBM requires actual WINDOW pin binding");
        wide_join();
#endif
        model.eval();
#ifdef DSROM_S81_NATIVE_WINDOW_LA
        wide_join();
#endif
        mux.m_rdy=model.m_rdy;mux.m_wr_done=model.m_wr_done;
        mux.s_v=model.s_v;mux.s_tag=model.s_tag;mux.s_beat=model.s_beat;mux.s_data=model.s_data;
        mux.eval();
        if(mux.fault||model.fault)throw std::runtime_error("native HBM/mux fault");
    }
    template<class Mux> void bind(Mux& mux) {
        if(join||mux.contextp()!=runtime.context)
            throw std::runtime_error("HBM requires one actual same-context borrowed C8 mux");
        join=[this,&mux](){wire(mux);};
    }
#ifdef DSROM_S81_NATIVE_WINDOW_LA
    // Pure pin join around the backend's existing low-edge eval. No new clock,
    // storage, response or write completion is owned by this binding.
    template<class Window> void bind_window_la(Window& window) {
        if(!join||wide_join||window.contextp()!=runtime.context||
           !model.window_la_enabled||model.window_la_stack!=0)
            throw std::runtime_error("WINDOW LA requires same-context enabled stack0 backend");
        require_window_la_ports(window,model);
        wide_join=[this,&window](){
            // Low-edge combinational settling only; sole provider owns clk.
            if(window.clk||model.clk)
                throw std::runtime_error("WINDOW LA join outside shared low edge");
            wire_window_la_response(window,model);
            window.eval();
            wire_window_la_request(window,model);
        };
    }
#endif
    bool drained()const {
        for(unsigned s=0;s<4;s++)if(reads[s]||writes[s])return false;
#ifdef DSROM_S81_NATIVE_WINDOW_LA
        for(auto debt:wide_reads)if(debt)return false;
#endif
        return true;
    }
    bool initialized()const{return model.history_ready;}
    DsromS81MinimumParticipant participant();
};
} // namespace dsrom_s81_minimum
