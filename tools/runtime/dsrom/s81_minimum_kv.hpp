#pragma once
#include "s81_minimum_prefix.hpp"
#include <memory>
#include <optional>
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
    // Zero is a legal captured value. Native descriptor inputs_ready/ready,
    // not the numeric generation, authorize the consumer.
    std::function<uint16_t()> generation;
    std::function<void()> drive_native_ports;
    bool stopped=false;
    bool consumed=false;
    bool staged_debt=false,stream_active=false;
    uint16_t staged_generation=0;
    bool target_engine=false;
    bool old_kv_accept=false,old_staged=false,old_stream_go=false,old_done=false;
    uint16_t old_generation=0;
    std::optional<DsromS81PrefixOperation> held_consumer;
    bool held_go=false;
    bool mux_bound=false;
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
            // Rejoin settled low-edge producer/backend/consumer pins. The
            // join is port wiring only; it must not advance descriptor state.
            drive_native_ports();
            wire_blocks();blocks.eval();window.eval();
            require(!blocks.fault&&!window.fault,"native packed KV producer/service fault");
            if(blocks.cap_v)
                require(blocks.cap_ready,"actual QE packed output cannot be dropped");
            if(window.start_v)
                require_packed_kv_window(generation(),window.start_user,
                                        window.start_first,window.start_count);
            // The composed S81 caller is target-context only. Standalone
            // producer debug hooks above do not authorize a pos0 token build.
            if(target_engine) {
                if(window.start_v)
                    require(window.start_first==1048448&&window.start_count==128,
                            "S81 composed WINDOW must use real history at position 1048575");
                if(blocks.issue)
                    require(blocks.issue_abs_row==1048575,
                            "S81 native current-row write is not at target position");
                if(window.prime_v)
                    require(window.prime_row>=1048448&&window.prime_row<=1048575,
                            "S81 primed history is outside selected target WINDOW");
            }
            // Freeze actual pre-edge handshakes before Nash evaluates ME or
            // any other shared participant takes its rising edge.
            old_kv_accept=bool(window.kv_v&&window.kv_ready);
            old_staged=window.staged_v;old_stream_go=window.stream_go;
            old_done=window.done;old_generation=generation();
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            require(!stopped,"packed KV provider quarantined");
            // Only the canonical host's shared edge clocks these two models.
            // Attention, QE and HBM remain their existing owners' participants.
            require(released || (!staged_debt&&!stream_active),
                    "reset would erase admitted packed WINDOW debt");
            blocks.rst_n=released;window.rst_n=released;
            if(released) {
                require(prepared_cycle==runtime.cycle(),"packed KV missing pre-edge prepare");
                consumed=old_kv_accept;
                if(old_staged) {
                    require(!staged_debt&&!stream_active,
                            "packed WINDOW staged over held generation");
                    staged_generation=old_generation;staged_debt=true;
                }
                if(staged_debt||stream_active)
                    require(old_generation==staged_generation,
                            "packed WINDOW generation changed with retained debt");
                if(old_stream_go) {
                    require(staged_debt&&!stream_active&&(!target_engine||held_go),
                            "packed WINDOW stream lacks staged native response");
                    staged_debt=false;stream_active=true;
                }
                if(old_done) {
                    require(stream_active,"packed WINDOW completion lacks accepted stream");
                    stream_active=false;staged_generation=0;
                    held_consumer.reset();held_go=false;
                }
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
    // Maxwell's NativeHbm clocks ONLY HBM. This is the single borrowed C8
    // mux clock owner; its native journal samples the same prepared ports.
    // Register once on the canonical runtime, independently of nested ME/KV.
    // The caller's port-only join settles WINDOW/CKV/mux/HBM before snapshots;
    // NativeHbm.prepare runs after those source inputs, before ANY rising.
    template<class NativeKvRopeMux,class NativeBackend>
    DsromS81MinimumParticipant mux_participant(NativeKvRopeMux& mux,NativeBackend& backend) {
        require(!mux_bound&&mux.contextp()==runtime.context,
                "C8 mux requires one canonical shared-edge owner");
        require(backend.initialized(),"C8 mux requires actual native history initialization");
        mux_bound=true;
        auto self=this->shared_from_this();
        return {"native-c8-kv-rope-mux",
            [self,&mux,&backend](const auto&){
                require(!self->fault()&&backend.initialized(),
                        "C8 mux missing live initialized source");
                mux.clk=0;mux.eval();
                require(!mux.fault,"native C8 mux preparation fault");
            },
            [self,&mux,&backend](bool released){
                // This minimum vehicle permits only initial shared cold reset,
                // never a warm reset that can erase native mux/CKV ownership.
                require(released||(!self->runtime.identity&&backend.drained()&&
                                   !self->staged_debt&&!self->stream_active),
                        "C8 mux reset would erase admitted context/debt");
                mux.rst_n=released;mux.clk=1;mux.eval();
                require(!mux.fault,"native C8 mux edge fault");
            },
            [&mux](bool released){mux.rst_n=released;mux.clk=0;mux.eval();},
            [self,&mux](){return self->fault()||bool(mux.fault);}};
    }
    // The selected512 producer is the EXISTING native CKV die service, not
    // WINDOW's compatibility merger (which binds selected_count to zero).
    // It owns VM-selected IDs, ordered row staging, FP4 encoding and TP4
    // all-gather. Its owner clocks it and supplies the native VM/AG callbacks.
    // Preserve its independent C8 client beside the WINDOW w_* client above.
    template<class NativeCkvService,class NativeKvRopeMux>
    void wire_selected_backend(NativeCkvService& ckv,NativeKvRopeMux& mux) {
        require(ckv.contextp()==runtime.context&&mux.contextp()==runtime.context,
                "selected CKV service/mux must share canonical context");
        static_assert(sizeof(ckv.c_addr)==sizeof(mux.c_addr),
                      "selected CKV four-stack addresses must match native mux");
        static_assert(sizeof(ckv.c_tag)==sizeof(mux.c_tag),
                      "selected CKV tags must match native C8 client");
        mux.c_v=ckv.c_v;mux.c_addr=ckv.c_addr;mux.c_len=ckv.c_len;
        mux.c_tag=ckv.c_tag;mux.c_we=ckv.c_we;
        mux.c_wdata=ckv.c_wdata;mux.c_wstrb=ckv.c_wstrb;
        mux.c_srdy=ckv.c_srdy;
        ckv.c_rdy=mux.c_rdy;ckv.c_wr_done=mux.c_wr_done;
        ckv.c_sv=mux.c_sv;ckv.c_stag=mux.c_stag;
        ckv.c_sbeat=mux.c_sbeat;ckv.c_sdata=mux.c_sdata;
        require(!ckv.fault&&!mux.fault,"native selected CKV service/backend fault");
    }
    // Exact selected ot_hdc_v41x_att_adapt PACKED_KV=1 external ports.
    // There is no host expansion, floating arithmetic or padding-history read.
    template<class Attention> void wire_attention(Attention& attention) {
        static_assert(sizeof(attention.packed_kv_w)==530*sizeof(uint32_t),
                      "selected attention must expose full 16960-bit packed KV");
        attention.packed_kv_v=window.kv_v;attention.packed_kv_m=window.kv_m;
        for(unsigned i=0;i<530;i++)attention.packed_kv_w[i]=window.kv_w[i];
        attention.packed_kv_fault=fault();
        window.kv_ready=attention.packed_kv_ready;
    }
    // Staging is asserted by the native schedule only after actual sector
    // read responses. Its row-valid bits require code AND scale m_wr_done.
    bool staged()const{return !fault()&&staged_debt&&generation()==staged_generation;}
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
    // Consume the EXISTING engine interface used by Nash's real_kv argument.
    // The supplied owner binds actual selected-history descriptors, publication
    // visibility and native lifecycle; this provider adds no address allocator
    // or source ABI. Its participant owns neither the ME leaf nor the ATT cut.
    // Enroll the returned engine ONLY nested inside Nash's ME participant,
    // never also enroll participant() or the descriptor owner separately.
    DsromS81PrefixNativeEngine engine(DsromS81PrefixNativeEngine owner) {
        require(!owner.participant.name.empty()&&owner.participant.prepare&&
                owner.participant.rising&&owner.participant.falling&&
                owner.participant.fault&&owner.ready&&owner.idle&&
                owner.inputs_ready&&owner.drive,
                "packed WINDOW needs actual source descriptor/lifecycle callbacks");
        require(!target_engine,"packed WINDOW engine bound twice");
        target_engine=true;
        auto self=this->shared_from_this();
        auto source=std::make_shared<DsromS81PrefixNativeEngine>(std::move(owner));
        return {{"actual-packed-window-kv",
            [self,source](const auto& r){source->participant.prepare(r);self->prepare();},
            [self,source](bool reset){self->rising(reset);source->participant.rising(reset);},
            [self,source](bool reset){self->falling(reset);source->participant.falling(reset);},
            [self,source](){return self->fault()||source->participant.fault();}},
            // Keep pre-edge readiness asserted through the driven GO pulse;
            // the shared rising edge moves staged ownership into active debt.
            [self,source](){return self->held_consumer&&!self->stream_active&&self->staged()&&
                                  source->ready()&&!source->participant.fault();},
            // Terminal drain only. Staged rows retain native ownership and
            // therefore cannot be presented as an idle source before ME GO.
            [self,source](){return !self->stream_active&&!self->staged_debt&&
                                  !self->held_consumer&&source->idle()&&
                                  !self->fault()&&!source->participant.fault();},
            [self,source](const auto& op){
                require(!self->fault()&&!source->participant.fault(),
                        "packed WINDOW source authority fault");
                if(self->held_go||self->stream_active)return false;
                if(self->held_consumer)
                    require(self->held_consumer->index==op.index&&
                            self->held_consumer->unit==op.unit&&
                            self->held_consumer->instruction==op.instruction,
                            "packed WINDOW held consumer changed before GO");
                // This is actual descriptor authorization for THIS literal
                // operation, not a lease derived from a generation number.
                if(!source->inputs_ready(op)||!source->ready()||!self->staged())return false;
                self->held_consumer=op;
                return true;
            },
            [self,source](const auto& op,bool go){
                if(go)require(self->held_consumer&&!self->held_go&&
                              self->held_consumer->index==op.index&&
                              self->held_consumer->unit==op.unit&&
                              self->held_consumer->instruction==op.instruction&&
                              self->staged()&&!self->stream_active&&source->ready()&&
                              !source->participant.fault(),
                              "ME GO lacks committed native WINDOW generation");
                source->drive(op,go);self->window.stream_go=go;
                if(go)self->held_go=true;
            }};
    }
};
} // namespace dsrom_s81_minimum
