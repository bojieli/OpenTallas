#pragma once
#include "s81_minimum_runtime.hpp"
#include <memory>
#include <stdexcept>
#include <type_traits>

// Exact existing V41_ATT_CUT buses (att_adapt.sv and the retained W17 runtime
// att_propagate mapping), H16/D512/TD32/NL4/PWORDS1. Borrow both native models;
// this participant clocks ONLY the attention endpoint. ME owns the adapter.
// Call join() at the END of the enclosing packed-provider's port-only join,
// before it freezes OLD handshakes. No model is evaluated on a private tick.
template<class Adapter,class Endpoint>
class DsromS81MinimumAttentionCut : public std::enable_shared_from_this<
    DsromS81MinimumAttentionCut<Adapter,Endpoint>> {
    DsromS81MinimumRuntime& runtime;
    Adapter& adapter;
    Endpoint& endpoint;
    long prepared=-1;
    bool stopped=false;
    template<class Bus> static bool bit(const Bus& b,unsigned i) {
        if constexpr(std::is_integral<Bus>::value)return (uint64_t(b)>>i)&1u;
        else return (b[i/32]>>(i%32))&1u;
    }
    template<class Bus> static void bit(Bus& b,unsigned i,bool value) {
        if constexpr(std::is_integral<Bus>::value) {
            const uint64_t mask=uint64_t(1)<<i;
            b=(uint64_t(b)&~mask)|(value?mask:0);
        } else {
            const uint32_t mask=uint32_t(1)<<(i%32);
            b[i/32]=(b[i/32]&~mask)|(value?mask:0);
        }
    }
    template<class To,class From> static bool copy(To& to,unsigned a,
        const From& from,unsigned b,unsigned n) {
        bool changed=false;
        unsigned i=0;
        // HOST-only exact copy of aligned wide-bus portions. Model input
        // values, changed detection, settle calls and all clock edges stay
        // identical. propagate() copies between distinct borrowed models.
        if constexpr(!std::is_integral<To>::value && !std::is_integral<From>::value) {
            if((a%32)==0 && (b%32)==0) {
                for(;n-i>=32;i+=32) {
                    const uint32_t value=from[(b+i)/32];
                    changed|=value!=to[(a+i)/32];to[(a+i)/32]=value;
                }
            }
        }
        for(;i<n;++i) {
            bool value=bit(from,b+i);changed|=value!=bit(to,a+i);bit(to,a+i,value);
        }
        return changed;
    }
    bool propagate() {
        bool changed=false;unsigned a=0;
        auto take=[&](auto& dst,unsigned n){changed|=copy(dst,0,adapter.att_to,a,n);a+=n;};
        take(endpoint.pv_cr,1);take(endpoint.p_w,512);take(endpoint.p_v,1);
        take(endpoint.sc_cr,1);take(endpoint.kv_w,16960);take(endpoint.kv_m,4);
        take(endpoint.kv_v,1);take(endpoint.q_w,8192);take(endpoint.q_v,1);
        take(endpoint.job_t,16);take(endpoint.job_v,1);
        if(a!=25690)throw std::runtime_error("selected ATT input bus extent differs");
        unsigned b=0;
        auto put=[&](const auto& src,unsigned n){changed|=copy(adapter.att_from,b,src,0,n);b+=n;};
        put(endpoint.pv_f,1024);put(endpoint.pv_y,32768);put(endpoint.pv_c,8);
        put(endpoint.pv_v,1);put(endpoint.sc_v,1);put(endpoint.sc_f,64);
        put(endpoint.sc_y,2048);put(endpoint.sc_m,4);put(endpoint.sc_row,16);
        put(endpoint.p_ready,1);put(endpoint.kv_ready,1);put(endpoint.q_ready,1);
        put(endpoint.job_ready,1);
        if(b!=35938)throw std::runtime_error("selected ATT output bus extent differs");
        return changed;
    }
public:
    DsromS81MinimumAttentionCut(DsromS81MinimumRuntime& r,Adapter& a,Endpoint& e)
    :runtime(r),adapter(a),endpoint(e) {
        if(!r.context||!r.cycle||a.contextp()!=r.context||e.contextp()!=r.context)
            throw std::runtime_error("ATT cut requires borrowed SAME-context actual models");
        static_assert(sizeof(a.att_to)==803*sizeof(uint32_t),"ATT adapter input width");
        static_assert(sizeof(a.att_from)==1124*sizeof(uint32_t),"ATT adapter output width");
        static_assert(sizeof(e.q_w)==256*sizeof(uint32_t),"ATT D512 query width");
        static_assert(sizeof(e.kv_w)==530*sizeof(uint32_t),"ATT full packed rows width");
        static_assert(sizeof(e.p_w)==16*sizeof(uint32_t),"ATT PWORDS1 probability width");
        static_assert(sizeof(e.sc_y)==64*sizeof(uint32_t),"ATT H16/NL4 scores width");
        static_assert(sizeof(e.pv_y)==1024*sizeof(uint32_t),"ATT 64-tile PV width");
    }
    void join() {
        try {
            if(stopped)throw std::runtime_error("ATT cut quarantined");
            if(adapter.clk||endpoint.clk)
                throw std::runtime_error("ATT cut port join must precede shared rising evaluation");
            // Same 64-settle guard as the existing W17 attention host; no
            // clock, ready override, added pipeline, or numerical substitution.
            for(unsigned i=0;i<64;++i) {
                bool changed=propagate();endpoint.eval();adapter.eval();
                if(!changed&&!propagate())return;
            }
            throw std::runtime_error("actual ATT cut combinational join did not settle");
        }catch(...){stopped=true;throw;}
    }
    DsromS81MinimumParticipant participant() {
        auto self=this->shared_from_this();
        return {"native-full-shape-ATT-cut",
            [self](const auto&){
                if(self->prepared==self->runtime.cycle())
                    throw std::runtime_error("ATT endpoint prepared twice");
                self->endpoint.clk=0;self->join();self->prepared=self->runtime.cycle();
            },
            [self](bool released){
                if(!released&&self->runtime.identity)
                    throw std::runtime_error("ATT cut reset after context admission would erase native debt");
                if(released&&self->prepared!=self->runtime.cycle())
                    throw std::runtime_error("ATT endpoint lacks pre-edge input capture");
                // Input fields were frozen in prepare. Do NOT propagate here:
                // the adapter may already have evaluated this SAME rising edge.
                self->endpoint.rst_n=released;self->endpoint.clk=1;self->endpoint.eval();
            },
            [self](bool released){
                self->endpoint.rst_n=released;self->endpoint.clk=0;self->endpoint.eval();
                if(!released)self->prepared=-1;
            },
            [self](){return self->stopped||bool(self->adapter.fault);}};
    }
};
