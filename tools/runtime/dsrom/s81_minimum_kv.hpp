#pragma once
#include "s81_minimum_runtime.hpp"
#include <memory>
#include <stdexcept>
#include <utility>

// Selected packed WINDOW path only. These are wiring hooks for borrowed native
// window_kv_blocks + window_attn_source models, NOT a second memory, producer,
// descriptor allocator, write journal, backend or attention/ME wrapper.
// Factory supplies its existing HBM/owner-safe service and cached history.
// No constructor initialization of KV contents or synthetic write completion.
namespace dsrom_s81_minimum {
void require_packed_kv_window(uint16_t native_generation,unsigned native_user,
    uint32_t native_first,unsigned native_count);

template<class Blocks,class Window>
class PackedKvProvider : public std::enable_shared_from_this<PackedKvProvider<Blocks,Window>> {
    DsromS81MinimumRuntime& runtime;
    Blocks& blocks;
    Window& window;
    // The existing descriptor owner retains the actual native generation.
    // We do not assign/increment it or grant consumer ownership in software.
    std::function<uint16_t()> generation;
    std::function<void()> drive_native_ports;
    bool stopped=false;
    bool consumed=false;
    long prepared_cycle=-1;

    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    void prepare() {
        try {
            require(!stopped,"packed KV provider quarantined");
            require(prepared_cycle!=runtime.cycle(),"packed KV prepared twice on shared edge");
            prepared_cycle=runtime.cycle();consumed=false;
            // Owner wires real QE/KVT commands, all FOUR tagged native backend
            // channels, committed m_wr_done, and Nash's descriptor/ready pins.
            // This callback must neither clock a model nor synthesize ACKs.
            drive_native_ports();
            blocks.clk=0;window.clk=0;
            blocks.eval();window.eval();
            wire_blocks();
            blocks.eval();window.eval();
            require(!blocks.fault&&!window.fault,"native packed KV producer/service fault");
            if(blocks.cap_v)
                require(blocks.cap_ready,"actual QE packed output cannot be dropped");
            if(window.start_v)
                require_packed_kv_window(generation(),window.start_user,
                                        window.start_first,window.start_count);
            if(window.kv_v)
                require(generation()!=0,"packed KV lacks actual descriptor generation");
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            require(!stopped,"packed KV provider quarantined");
            // Only the canonical host's shared edge clocks these two models.
            // Attention, QE and HBM remain their existing owners' participants.
            blocks.rst_n=released;window.rst_n=released;
            if(released) {
                require(prepared_cycle==runtime.cycle(),"packed KV missing pre-edge prepare");
                consumed=bool(window.kv_v&&window.kv_ready);
            }
            blocks.clk=1;window.clk=1;
            blocks.eval();window.eval();
            require(!blocks.fault&&!window.fault,"native packed KV edge fault");
        }catch(...){stopped=true;throw;}
    }
    void falling(bool released) {
        blocks.rst_n=released;window.rst_n=released;
        blocks.clk=0;window.clk=0;blocks.eval();window.eval();
        // Do not update Nash's pre-edge data after his rising evaluation.
        // Its next prepare copies the now-settled native packed output.
        // The canonical cold_start does not increment runtime.cycle().
        if(!released) {prepared_cycle=-1;consumed=false;}
    }
public:
    PackedKvProvider(DsromS81MinimumRuntime& r,Blocks& b,Window& w,
        std::function<uint16_t()> native_generation,std::function<void()> actual_port_join)
    :runtime(r),blocks(b),window(w),generation(std::move(native_generation)),
     drive_native_ports(std::move(actual_port_join)) {
        require(r.context&&r.cycle&&generation&&drive_native_ports,
                "actual shared runtime/generation/backend port join required");
        require(b.contextp()==r.context&&w.contextp()==r.context,
                "packed KV models must use the SAME canonical context");
    }
    // Call on the sampled actual QE20 output, with no host decode/re-encode.
    template<class Qe> void wire_qe(const Qe& qe) {
        if(qe.kvb_v)require(qe.kvb_src_addr>=55232&&qe.kvb_src_addr<55744&&
                           (qe.kvb_src_addr&31u)==0,
                           "selected L0.I20 native packed capture address differs");
        blocks.cap_v=qe.kvb_v;blocks.cap_src_addr=qe.kvb_src_addr;
        for(unsigned i=0;i<8;i++)blocks.cap_codes[i]=qe.kvb_codes[i];
        blocks.cap_scale=qe.kvb_scale;
        require(!qe.kvb_fault,"actual QE packed capture fault");
    }
    // issue/issue_src_base/issue_kvt_base/issue_row/issue_abs_row are driven by
    // the actual SU21/KVT instruction owner. Never infer them from a VM write.
    void wire_blocks() {
        blocks.blk_ready=window.blk_ready;
        window.blk_v=blocks.blk_v;window.blk_row=blocks.blk_row;
        window.blk_idx=blocks.blk_idx;
        for(unsigned i=0;i<8;i++)window.blk_codes[i]=blocks.blk_codes[i];
        window.blk_scale=blocks.blk_scale;
        // blk_user comes from the actual descriptor/context owner, not zero.
    }
    // Existing ot_chip_v41x_kv_rope_reqmux[_c8] WINDOW client. Keep all four
    // channels, native length/tag/beat and independent responses intact.
    // The borrowed mux's existing C8 journal and backend remain clock owners;
    // w_wr_done is routed committed visibility, NEVER w_rdy or acceptance.
    // No per-load polling loop, new transaction queue, or credit=1 restriction.
    template<class NativeKvRopeMux> void wire_backend(NativeKvRopeMux& mux) {
        static_assert(sizeof(window.m_addr)==sizeof(mux.w_addr),
                      "actual native four-stack address widths must match");
        static_assert(sizeof(window.m_tag)==sizeof(mux.w_tag),
                      "actual native tagged WINDOW client widths must match");
        mux.w_v=window.m_v; mux.w_addr=window.m_addr; mux.w_len=window.m_len;
        mux.w_tag=window.m_tag; mux.w_we=window.m_we;
        mux.w_wdata=window.m_wdata; mux.w_wstrb=window.m_wstrb;
        mux.w_srdy=window.s_rdy;
        window.m_rdy=mux.w_rdy; window.m_wr_done=mux.w_wr_done;
        window.s_v=mux.w_sv; window.s_tag=mux.w_stag;
        window.s_beat=mux.w_sbeat; window.s_data=mux.w_sdata;
        require(!mux.fault,"actual native WINDOW/RoPE backend mux fault");
    }
    // Raw 4*16*265 bits from native WINDOW merge to Nash PACKED_KV=1.
    // There is no host expansion, floating arithmetic or padding-history read.
    template<class Attention> void wire_attention(Attention& attention) {
        static_assert(sizeof(attention.kv_w)==530*sizeof(uint32_t),
                      "selected attention must expose full 16960-bit packed KV");
        attention.kv_v=window.kv_v;attention.kv_m=window.kv_m;
        for(unsigned i=0;i<530;i++)attention.kv_w[i]=window.kv_w[i];
        window.kv_ready=attention.kv_ready;
        if(window.kv_v)require(generation()!=0,"missing native packed KV generation");
    }
    // Staging is asserted by the native schedule only after actual sector
    // read responses. Its row-valid bits require code AND scale m_wr_done.
    bool staged()const{return !fault()&&window.staged_v;}
    bool packed_valid()const{return !fault()&&window.kv_v;}
    bool packed_accepted_on_last_edge()const{return !fault()&&consumed;}
    uint16_t native_generation()const{return generation();}
    bool fault()const{return stopped||blocks.fault||window.fault;}
    DsromS81MinimumParticipant participant() {
        auto self=this->shared_from_this();
        return {"actual-packed-window-kv",
            [self](const DsromS81PairResult&){self->prepare();},
            [self](bool reset){self->rising(reset);},
            [self](bool reset){self->falling(reset);},
            [self](){return self->fault();}};
    }
};
} // namespace dsrom_s81_minimum
