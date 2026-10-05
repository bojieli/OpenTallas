#pragma once
#include "s81_minimum_prefix.hpp"
#include <memory>
#include <optional>
#include <stdexcept>
#include <sstream>
#include <utility>
#include <tuple>

// Selected packed WINDOW + native selected CKV path. Wiring hooks for borrowed native
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
    bool selected_bound=false,selected_ready=false,selected_drained=false;
    bool selected_clock_bound=false;
    bool selected_valid=false,selected_accept=false;
    bool window_drained=false,old_full_drained=false;
    std::function<bool()> descriptor_drained;
    bool kvt_pending=false,kvt_visible=false,old_kvt_visible=false;
    uint32_t kvt_blocks_base=0;
    std::optional<DsromS81PrefixOperation> proposed_kvt,kvt_owner;
    bool old_kvt_issue=false;
    uint32_t old_blocks_written=0;
    std::optional<DsromS81PrefixOperation> proposed_ckv,ckv_owner;
    bool old_ckv_write=false,old_ckv_visible=false,ckv_visible=false;
    std::function<bool()> native_ckv_visible;

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
            old_kv_accept=selected_bound?selected_accept:bool(window.kv_v&&window.kv_ready);
            old_staged=window.staged_v;old_stream_go=window.stream_go;
            old_done=window.done;old_generation=generation();
            old_full_drained=!target_engine||
                (selected_bound&&selected_drained&&descriptor_drained());
            old_ckv_visible=ckv_owner&&native_ckv_visible&&native_ckv_visible();
            old_kvt_issue=blocks.issue&&blocks.issue_ready;
            old_blocks_written=window.blocks_written;
            old_kvt_visible=kvt_pending&&blocks.idle&&window.blk_ready&&
                uint32_t(window.blocks_written-kvt_blocks_base)==16;
        }catch(...){stopped=true;throw;}
    }
    void rising(bool released) {
        try {
            require(!stopped,"packed KV provider quarantined");
            // Only the canonical host's shared edge clocks these two models.
            // Attention, QE and HBM remain their existing owners' participants.
            require(released || (!staged_debt&&!stream_active&&(!kvt_pending||kvt_visible)&&(!ckv_owner||ckv_visible)),
                    "reset would erase admitted packed WINDOW debt");
            blocks.rst_n=released;window.rst_n=released;
            if(released) {
                require(prepared_cycle==runtime.cycle(),"packed KV missing pre-edge prepare");
                consumed=old_kv_accept;
                bool new_ckv=false;
                if(old_ckv_write) {
                    require(bool(proposed_ckv),"native CKV write lacks held quantizer operation");
                    new_ckv=!ckv_owner||ckv_owner->index!=proposed_ckv->index;
                    if(new_ckv) {
                        require(!ckv_owner||ckv_visible,"native CKV writer overwrites uncommitted row");
                        ckv_owner=proposed_ckv;ckv_visible=false;
                    } else require(ckv_owner->unit==proposed_ckv->unit&&
                                   ckv_owner->instruction==proposed_ckv->instruction,
                                   "native CKV held writer changed literal");
                }
                if(old_ckv_visible&&!new_ckv)ckv_visible=true;
                if(old_kvt_issue) {
                    require(proposed_kvt&&(!kvt_pending||kvt_visible),
                            "native KVT issue overlaps uncommitted current row");
                    kvt_owner=proposed_kvt;kvt_blocks_base=old_blocks_written;
                    kvt_pending=true;kvt_visible=false;
                }
                if(old_kvt_visible&&!old_kvt_issue)kvt_visible=true;
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
                    staged_debt=false;stream_active=true;window_drained=false;
                }
                if(old_done) {
                    require(stream_active,"packed WINDOW completion lacks accepted stream");
                    window_drained=true;
                }
                // WINDOW.done is only the first128 rows. Native service and
                // descriptor ownership must also drain before generation release.
                if(stream_active&&window_drained&&old_full_drained) {
                    stream_active=false;staged_generation=0;
                    held_consumer.reset();held_go=false;window_drained=false;
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
        if(qe.kvb_v)require(qe.kvb_src_addr<(1u<<19)&&
                           (qe.kvb_src_addr&31u)==0,
                           "native packed capture must name aligned actual VM source");
        blocks.cap_v=qe.kvb_v;blocks.cap_src_addr=qe.kvb_src_addr;
        for(unsigned i=0;i<8;i++)blocks.cap_codes[i]=qe.kvb_codes[i];
        blocks.cap_scale=qe.kvb_scale;
        require(!qe.kvb_fault,"actual QE packed capture fault");
    }
    // Hubble's distinct native ot_hdc_v41_qe quantizer, not the QAL/KVAL
    // field actor. Join OLD outputs before ANY native rising evaluation.
    template<class QuantizerPorts,class NativeCkvService>
    void wire_quantizer(QuantizerPorts& hooks,NativeCkvService& ckv) {
        require(hooks.native&&hooks.held_mode&&hooks.held_operation,
                "actual native QE quantizer hooks absent");
        const auto& qe=hooks.native();
        require(qe.contextp()==runtime.context&&ckv.contextp()==runtime.context&&
                qe.clk==0&&ckv.clk==0&&!qe.fault,
                "quantizer/CKV must borrow live SAME-context low edge");
        wire_qe(qe); // mode1 kvb payload is copied verbatim, with its fault.
        old_ckv_write=false;ckv.nw_we=0;
        if(!(qe.w_we&1u))return;
        const unsigned mode=hooks.held_mode();
        require(mode==qe.i_mode,"quantizer held native mode changed");
        if(mode!=3)return;
        const auto op=hooks.held_operation();
        require(op.unit==3&&runtime.identity&&qe.w_mask==0xffffffffu&&
                (qe.w_addr&31u)==0&&qe.w_addr>>9==1048575,
                "QDQ4E write lacks actual target row/held literal/mask");
        // Original ww_q_we[0] && qe_mode3 -> ckv_nw_* wiring. The
        // service's native row encoder consumes these BF16-bearing words.
        ckv.position_identity=*runtime.identity;
        ckv.nw_we=1;ckv.nw_addr=qe.w_addr;ckv.nw_data=qe.w_data;
        proposed_ckv=op;old_ckv_write=true;
    }
    // All ranks observe the actual committing owner of gid1048575 (rank3).
    // Nonowners must not manufacture completion from their local quiet state.
    template<class QuantizerPorts,class CommittingCkvService>
    void bind_quantizer_sink(QuantizerPorts& hooks,CommittingCkvService& committing_owner) {
        require(!native_ckv_visible&&!hooks.ckv_writes_visible&&
                committing_owner.contextp()==runtime.context,
                "native CKV visibility requires one actual committing owner");
        auto self=this->shared_from_this();
        native_ckv_visible=[self,&committing_owner]() {
            if(!committing_owner.own_visible_v)return false;
            require(!committing_owner.fault&&self->runtime.identity&&
                    committing_owner.own_visible_identity==*self->runtime.identity&&
                    committing_owner.own_visible_gid==1048575,
                    "native CKV commit identity/target row mismatch");
            return true; // native pulse only after ninth positive c_wr_done.
        };
        hooks.ckv_writes_visible=[self](const DsromS81PrefixOperation& op) {
            return !self->fault()&&self->ckv_visible&&self->ckv_owner&&
                   self->ckv_owner->index==op.index&&self->ckv_owner->unit==op.unit&&
                   self->ckv_owner->instruction==op.instruction;
        };
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
    // Borrow Hubble's actual decoded SU leaf and OLD go&&ready association.
    // This is the original core win_su_match/issue mapping, not a scalar KV
    // reconstruction. Position comes from the actual admitted source context.
    template<class SuPorts> void wire_su(SuPorts& hooks,uint32_t actual_position) {
        require(hooks.native&&hooks.held_operation&&hooks.accepts_on_current_shared_edge,
                "actual borrowed SU source hooks absent");
        blocks.issue=0;
        if(!hooks.accepts_on_current_shared_edge())return;
        const auto& su=hooks.native();
        const bool match=su.i_dst==3&&su.i_asrc==0&&su.i_nout==1&&
                         su.i_nin==512&&su.i_abase==blocks.cap_src_base;
        if(!match)return;
        auto op=hooks.held_operation();
        require(op.unit==2&&blocks.issue_ready&&su.i_orow<128&&
                actual_position<(1u<<20)&&(!target_engine||actual_position==1048575),
                "native WINDOW KVT GO lacks captured row/capacity/context");
        require(!kvt_pending||kvt_visible,"native KVT GO overwrites uncommitted row");
        proposed_kvt=op;
        blocks.issue_src_base=su.i_abase;blocks.issue_kvt_base=su.i_obase;
        blocks.issue_row=su.i_orow;blocks.issue_abs_row=actual_position;
        blocks.issue=1;
    }
    template<class SuPorts> void bind_su_sink(SuPorts& hooks) {
        require(!hooks.kv_write&&!hooks.kv_writes_visible,
                "native SU KV sink already has an owner");
        auto self=this->shared_from_this();
        hooks.kv_write=[self](const auto& su,const DsromS81PrefixOperation& op){
            const auto& owner=self->old_kvt_issue?self->proposed_kvt:self->kvt_owner;
            require(!self->fault()&&!su.fault&&owner&&owner->index==op.index&&
                    owner->unit==op.unit&&owner->instruction==op.instruction,
                    "native SU KV strobe lacks accepted packed WINDOW source");
            // Original win_scalar_suppress: packed block writes replace the
            // matching KVT scalar strobes. Observation grants no completion.
        };
        hooks.kv_writes_visible=[self](){return !self->fault()&&self->kvt_pending&&self->kvt_visible;};
    }
    template<class SuPorts>
    DsromS81PrefixNativeEngine su_engine(DsromS81PrefixNativeEngine owner,SuPorts& hooks) {
        require(owner.ready&&owner.idle&&owner.inputs_ready&&owner.drive&&hooks.native,
                "actual SU engine/borrowed native hooks absent");
        auto self=this->shared_from_this();
        auto source=std::make_shared<DsromS81PrefixNativeEngine>(std::move(owner));
        auto admission=[self,&hooks]() {
            const auto& su=hooks.native();
            const bool window_row=su.i_dst==3&&su.i_asrc==0&&su.i_nout==1&&su.i_nin==512;
            return !self->fault()&&(window_row?
                (su.i_abase==self->blocks.cap_src_base&&self->blocks.issue_ready&&
                 (!self->kvt_pending||self->kvt_visible)):bool(self->blocks.idle));
        };
        return {source->participant,
            [source,admission](){return source->ready()&&admission();},
            [self,source](){return source->idle()&&(!self->kvt_pending||self->kvt_visible);},
            [source,admission](const auto& op){return source->inputs_ready(op)&&admission();},
            [source,admission](const auto& op,bool go){
                if(go)require(admission(),"SU GO before real packed capture/write capacity");
                source->drive(op,go);
            }};
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
    // Sole service clock owner, borrowed from Arendt's rank-specific model.
    // Factory first settles actual index/VM, QE, TP4AG and C8 pins; this
    // participant snapshots ALL those input pins before ANY native rising.
    template<class NativeCkvService>
    DsromS81MinimumParticipant selected_participant(NativeCkvService& ckv) {
        require(!selected_clock_bound&&ckv.contextp()==runtime.context,
                "selected CKV requires one canonical shared-edge owner");
        selected_clock_bound=true;
        auto self=this->shared_from_this();
        auto inputs=[&ckv](){return std::make_tuple(ckv.sel_v,ckv.sel_vmword,ckv.nw_we,ckv.nw_addr,ckv.nw_data,ckv.vm_rq,ckv.c_rdy,ckv.c_wr_done,ckv.c_sv,ckv.c_stag,ckv.c_sbeat,ckv.c_sdata,ckv.ag_tx_ready,ckv.ag_rx_valid,ckv.ag_rx_rank,ckv.ag_rx_gid,ckv.ag_rx_row,ckv.job_v,ckv.kv_ready,ckv.position_identity);};
        auto old=std::make_shared<decltype(inputs())>(inputs());
        auto prepared=std::make_shared<bool>(false);
        auto restore=[&ckv,old](){std::tie(ckv.sel_v,ckv.sel_vmword,ckv.nw_we,ckv.nw_addr,ckv.nw_data,ckv.vm_rq,ckv.c_rdy,ckv.c_wr_done,ckv.c_sv,ckv.c_stag,ckv.c_sbeat,ckv.c_sdata,ckv.ag_tx_ready,ckv.ag_rx_valid,ckv.ag_rx_rank,ckv.ag_rx_gid,ckv.ag_rx_row,ckv.job_v,ckv.kv_ready,ckv.position_identity)=*old;};
        return {"borrowed-native-selected-CKV",
            [self,&ckv,inputs,old,prepared](const auto&){
                require(!*prepared&&!self->fault()&&!ckv.fault,
                        "native CKV duplicate/faulted pre-edge preparation");
                *old=inputs();*prepared=true;ckv.clk=0;ckv.eval();
            },
            [self,&ckv,restore,prepared](bool released){
                require(*prepared&&!self->fault()&&(!self->runtime.identity||released),
                        "native CKV edge lacks snapshot or resets admitted context");
                restore();
                const auto edge_addr=ckv.c_addr;
                const auto edge_tag=ckv.c_tag;
                const unsigned edge_request=ckv.c_v,edge_write=ckv.c_we;
                const unsigned edge_vm_re=ckv.vm_re,edge_vm_addr=ckv.vm_raddr;
                ckv.rst_n=released;ckv.clk=1;ckv.eval();
                if(ckv.fault){
                    self->stopped=true;
                    // Report existing native outputs and the OLD restored inputs
                    // at the failing edge. No repair, retry or invented authority.
                    std::ostringstream e;
                    e<<"native CKV edge fault rank="<<self->runtime.rank
                     <<" cycle="<<self->runtime.cycle()<<" fault_code="<<unsigned(ckv.fault_code)
                     <<" sel_v="<<unsigned(ckv.sel_v)<<" sel_vmword="<<ckv.sel_vmword
                     <<" vm_re="<<edge_vm_re<<" vm_raddr="<<edge_vm_addr
                     <<" nw_we="<<unsigned(ckv.nw_we)<<" nw_addr=0x"<<std::hex<<ckv.nw_addr
                     <<" c_v=0x"<<edge_request<<" c_we=0x"<<edge_write
                     <<" c_rdy=0x"<<unsigned(ckv.c_rdy)<<" c_wr_done=0x"<<unsigned(ckv.c_wr_done)
                     <<" c_tag=0x"<<edge_tag<<" c_sv=0x"<<unsigned(ckv.c_sv)
                     <<" c_stag=0x"<<ckv.c_stag<<" c_sbeat=0x"<<ckv.c_sbeat
                     <<" c_addr_words=";
                    for(unsigned w=0;w<4;w++)e<<(w?",":"")<<edge_addr[w];
                    e<<" vm_rq_words=";
                    for(unsigned w=0;w<16;w++)e<<(w?",":"")<<ckv.vm_rq[w];
                    e<<" ag_rx_valid=0x"<<unsigned(ckv.ag_rx_valid)
                     <<" ag_rx_rank=0x"<<ckv.ag_rx_rank<<" ag_rx_gid=0x"<<ckv.ag_rx_gid;
                    throw std::runtime_error(e.str());
                }
            },
            [&ckv,restore,prepared](bool released){
                restore();ckv.rst_n=released;ckv.clk=0;ckv.eval();*prepared=false;
            },
            [self,&ckv](){return self->fault()||bool(ckv.fault);}};
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
    // Full640 uses Boole's actual native phase outputs, not WINDOW alone.
    // The phase participant clocks its own model and snapshots these pins
    // after this low-edge join. Arendt's service retains its own clock owner.
    template<class Attention,class NativePhase,class NativeCkvService>
    void wire_selected_attention(Attention& attention,NativePhase& phase,NativeCkvService& ckv) {
        require(phase.contextp()==runtime.context&&ckv.contextp()==runtime.context&&
                phase.clk==0&&ckv.clk==0,"selected source join requires shared low edge");
        static_assert(sizeof(attention.packed_kv_w)==sizeof(phase.win_service_w)&&
                      sizeof(phase.svc_kv_w)==sizeof(ckv.kv_w),
                      "native selected packed source must retain full 16960 bits");
        const bool old_ready=attention.packed_kv_ready;
        phase.window_source_start=window.start_v&&window.start_ready;
        phase.wsrc_v=window.kv_v;phase.wsrc_m=window.kv_m;phase.wsrc_w=window.kv_w;
        phase.tile_packed_ready=old_ready;
        phase.svc_kv_v=ckv.kv_v;phase.svc_kv_m=ckv.kv_m;phase.svc_kv_w=ckv.kv_w;
        phase.svc_job_ready=ckv.job_ready;phase.svc_job_done=ckv.job_done;
        phase.svc_own_pending=ckv.own_pending;phase.eval();
        attention.packed_kv_v=phase.win_service_v;attention.packed_kv_m=phase.win_service_m;
        attention.packed_kv_w=phase.win_service_w;attention.packed_kv_fault=fault()||ckv.fault;
        window.kv_ready=phase.wsrc_ready;
        ckv.kv_ready=phase.svc_kv_ready;ckv.job_v=phase.svc_job_v;
        selected_bound=true;
        selected_valid=phase.win_service_v;
        selected_accept=phase.win_service_v&&old_ready;
        selected_ready=ckv.rows_ready&&!ckv.own_pending&&!ckv.fault;
        selected_drained=!phase.ckv_ph&&!phase.ckv_job_pend&&!ckv.own_pending&&
                         ckv.reuse_ready&&!ckv.vm_busy&&!ckv.kv_v&&!ckv.job_v;
        require(!ckv.fault,"native selected CKV source fault");
    }
    // Staging is asserted by the native schedule only after actual sector
    // read responses. Its row-valid bits require code AND scale m_wr_done.
    bool staged()const{return !fault()&&staged_debt&&generation()==staged_generation;}
    bool packed_valid()const{return !fault()&&(selected_bound?selected_valid:bool(window.kv_v));}
    bool current_row_visible()const{return !fault()&&kvt_pending&&kvt_visible;}
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
        descriptor_drained=source->idle;
        return {{"actual-packed-window-kv",
            [self,source](const auto& r){
                // A pending literal requests descriptor capture/staging; it is
                // not GO authority. Keep the actual owner progressing before
                // it snapshots start/prime, even while WINDOW is not ready.
                if(self->held_consumer&&!self->held_go&&!self->stream_active){
                    require(!self->fault()&&!source->participant.fault(),
                            "pending packed WINDOW source authority fault");
                    source->inputs_ready(*self->held_consumer);
                    source->drive(*self->held_consumer,false);
                }
                source->participant.prepare(r);self->prepare();
            },
            [self,source](bool reset){self->rising(reset);source->participant.rising(reset);},
            [self,source](bool reset){self->falling(reset);source->participant.falling(reset);},
            [self,source](){return self->fault()||source->participant.fault();}},
            // Keep pre-edge readiness asserted through the driven GO pulse;
            // the shared rising edge moves staged ownership into active debt.
            [self,source](){return self->held_consumer&&!self->stream_active&&self->staged()&&
                                  self->selected_bound&&self->selected_ready&&self->current_row_visible()&&
                                  source->ready()&&!source->participant.fault();},
            // Terminal drain only. Staged rows retain native ownership and
            // therefore cannot be presented as an idle source before ME GO.
            [self,source](){return !self->stream_active&&!self->staged_debt&&
                                  !self->held_consumer&&source->idle()&&
                                  self->selected_bound&&self->selected_drained&&
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
                // Ask the real descriptor owner to capture THIS literal before
                // waiting for WINDOW staging. Retaining a pending request grants
                // no readiness, native generation or operand lease by itself.
                const bool authorized=source->inputs_ready(op);
                self->held_consumer=op;
                return authorized&&source->ready()&&self->staged()&&
                       self->selected_bound&&self->selected_ready&&self->current_row_visible();
            },
            [self,source](const auto& op,bool go){
                if(go)require(self->held_consumer&&!self->held_go&&
                              self->held_consumer->index==op.index&&
                              self->held_consumer->unit==op.unit&&
                              self->held_consumer->instruction==op.instruction&&
                              self->staged()&&!self->stream_active&&source->ready()&&
                              self->selected_bound&&self->selected_ready&&self->current_row_visible()&&
                              !source->participant.fault(),
                              "ME GO lacks committed native WINDOW generation");
                source->drive(op,go);self->window.stream_go=go;
                if(go)self->held_go=true;
            }};
    }
};
} // namespace dsrom_s81_minimum
