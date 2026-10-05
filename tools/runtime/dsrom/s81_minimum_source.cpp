#include "s81_minimum_source_plan.hpp"
#ifdef DSROM_S81_L20_KV_ENCLOSING
#include "s81_minimum_l20_kv_factory.hpp"
// Entry implemented by the existing KV owner; no Runtime/Plan layout change.
namespace dsrom_s81_minimum {
int run_minimum_l20_kv(DsromS81MinimumRuntime&,const char* output);
}
#endif
#include "Vnative_vm.h"
#include <cstdio>
#include <filesystem>
#include <stdexcept>
#include <tuple>
#include <utility>

#ifdef DSROM_S81_HEAD_WINNER_BINDING_HEADER
#include "VDsromS81CoreEnd.h"
#include "VDsromS81CoreEnd___024root.h"
#include <array>
#include <fstream>
#include <regex>
#include <sstream>
#include <vector>
// Internal construction overload agreed with the factory. No Runtime/Plan ABI.
DsromS81MinimumSourcePlan dsrom_s81_bind_minimum_source(
    DsromS81MinimumRuntime&,std::shared_ptr<Vnative_vm>,
    std::shared_ptr<VDsromS81CoreEnd>);

namespace {
class HeadEndCore {
    DsromS81MinimumRuntime& runtime;
    std::shared_ptr<VDsromS81CoreEnd> core;
    std::vector<std::array<uint32_t,64>> program;
    uint32_t producer_pc=0,end_pc=0,first_pc=0;
    uint64_t owner=0;
    bool armed=false,started=false,dot_accepted=false,final_taken=false;
    bool end_seen=false,terminal=false,stopped=false;
    std::array<uint32_t,16> final_frame{};
    std::function<void()> begin_dot;
    static void require(bool ok,const char* why) {
        if(!ok)throw std::runtime_error(why);
    }
    static std::string read(const std::filesystem::path& path) {
        std::ifstream in(path);require(bool(in),"literal HEAD program file unavailable");
        std::ostringstream out;out<<in.rdbuf();
        require(!in.bad(),"literal HEAD program file read failed");return out.str();
    }
    static uint32_t number(const std::string& json,const std::string& key) {
        // Only the unique scalar fields of the existing emitted schema are read.
        const std::regex re("\\\""+key+"\\\"\\s*:\\s*([0-9]+)");
        const auto b=std::sregex_iterator(json.begin(),json.end(),re);
        require(b!=std::sregex_iterator(),"literal HEAD program scalar missing");
        auto next=b;++next;require(next==std::sregex_iterator(),"ambiguous HEAD program scalar");
        const auto n=std::stoull((*b)[1].str());
        require(n<16384,"literal HEAD PC outside PAW14");return uint32_t(n);
    }
    static uint32_t field(const std::array<uint32_t,16>& words,unsigned bit,unsigned width) {
        uint64_t v=words[bit/32];
        if(bit%32 && bit/32+1<words.size())v|=uint64_t(words[bit/32+1])<<32;
        return uint32_t(v>>(bit%32)) & (width==32?0xffffffffu:((1u<<width)-1));
    }
    bool capture_sticky_fault() const {
        return core->rootp->ot_dsrom_s81_actual_core_end__DOT__g_rom__DOT__u_spine__DOT__u_capture__DOT__sticky_fault;
    }
    void healthy(bool settled_preedge=true) {
        // capture_fault includes combinational NEXT-edge invalid terms.
        // After a push the newly valid head has no ACK until LOW preparation;
        // only settled OLD inputs may be checked for edge admission. RTL
        // sticky_fault retains EVERY invalid accepted edge for post-edge checks.
        if(stopped||core->fault||capture_sticky_fault()||(settled_preedge&&core->capture_fault)) {
            const auto* r=core->rootp;
            std::ostringstream detail;
            detail << "actual HEAD core fault; accepted ownership retained"
                << " cycle=" << runtime.cycle()
                << " pc=" << unsigned(r->ot_dsrom_s81_actual_core_end__DOT__pc)
                << " state=" << unsigned(r->ot_dsrom_s81_actual_core_end__DOT__st)
                << " core_fault=" << unsigned(core->fault)
                << " capture_fault=" << unsigned(core->capture_fault)
                << " capture_sticky_fault=" << unsigned(capture_sticky_fault())
                << " settled_preedge=" << unsigned(settled_preedge)
                << " adapter_fault=" << unsigned(r->ot_dsrom_s81_actual_core_end__DOT__g_rom__DOT__a_fault)
                << " spine_fault=" << unsigned(r->ot_dsrom_s81_actual_core_end__DOT__g_rom__DOT__sp_fault)
                << " head_fault=" << unsigned(r->ot_dsrom_s81_actual_core_end__DOT__head_fault)
                << " native_fault=" << unsigned(r->ot_dsrom_s81_actual_core_end__DOT__g_native_head__DOT__u_head__DOT__native_fault)
                << " range_fault=" << unsigned(r->ot_dsrom_s81_actual_core_end__DOT__g_native_head__DOT__u_head__DOT__range_fault)
                << " nonfinite=" << unsigned(r->ot_dsrom_s81_actual_core_end__DOT__g_native_head__DOT__u_head__DOT__nonfinite)
                << " command_accepted=" << dot_accepted
                << " final_accepted=" << final_taken;
            throw std::runtime_error(detail.str());
        }
    }
    void unsupported() {
        // These service endpoints have accepted NO commands. They are not an
        // idle substitute for live engines: any request is refused before edge.
        require(!core->service_me0_go&&!core->service_su_go&&!core->service_qe_go&&
                !core->service_xu_go&&!core->service_he_go&&!core->coll_go&&
                !core->rope_pf_v&&!core->att_packed_issue&&!core->kvd_v,
                "HEAD I5/I6 requested an unbound actual core service");
    }
public:
    HeadEndCore(DsromS81MinimumRuntime& rt,std::shared_ptr<VDsromS81CoreEnd> model)
        :runtime(rt),core(std::move(model)) {
        const char* dir=std::getenv("DSROM_S81_NATIVE_HEAD_PROGRAM_DIR");
        require(dir&&*dir,"HEAD_END requires emitted literal HEAD program directory");
        const auto root=std::filesystem::path(dir);
        const auto json=read(root/"head_program.json");
        require(json.find("dsrom.s81.head.source-program.v1")!=std::string::npos,
                "HEAD_END requires canonical emitted HEAD source schema");
        producer_pc=number(json,"producer_pc14");end_pc=number(json,"end_pc14");
        require(producer_pc>=5&&end_pc==producer_pc+1,"literal HEAD I5/I6 PC mismatch");
        first_pc=producer_pc-5;
        const std::regex pc_re("\\\"source_pc\\\"\\s*:\\s*([0-9]+)");
        const std::regex word_re("\\\"word_hex\\\"\\s*:\\s*\\\"([0-9a-fA-F]{512})\\\"");
        std::vector<std::string> words;
        unsigned i=0;
        for(auto it=std::sregex_iterator(json.begin(),json.end(),pc_re);it!=std::sregex_iterator();++it,++i)
            require(std::stoull((*it)[1].str())==first_pc+i,"HEAD literal PCs not contiguous");
        require(i==7,"HEAD requires all seven source instructions");
        for(auto it=std::sregex_iterator(json.begin(),json.end(),word_re);it!=std::sregex_iterator();++it)
            words.push_back((*it)[1].str());
        require(words.size()==7,"HEAD literal word count mismatch");
        std::istringstream hex(read(root/"head_prog.hex"));std::string word;
        for(i=0;i<7;++i) {
            require(bool(hex>>word)&&word==words[i],"HEAD image differs from literal source words");
            std::array<uint32_t,64> packed{};
            for(unsigned j=0;j<64;++j)packed[j]=uint32_t(std::stoul(word.substr(512-8*(j+1),8),nullptr,16));
            program.push_back(packed);
        }
        require(!(hex>>word),"HEAD image contains unexpected instructions");
        // All input pins are explicit before the factory attaches live providers.
        // This runs only before cold reset; never erases an accepted obligation.
        core->clk=0;
        core->rst_n=0;
        core->service_me0_ready=0;
        core->service_me0_idle=0;
        core->service_me0_wrom_re=0;
        core->service_me0_kv_re=0;
        core->service_me0_x_re=0;
        core->service_me0_ov=0;
        core->service_me0_o_we=0;
        core->service_me0_am_any=0;
        core->service_me0_fault=0;
        core->service_su_ready=0;
        core->service_su_idle=0;
        core->service_su_vi_re=0;
        core->service_su_wrom_re=0;
        core->service_su_vm_we=0;
        core->service_su_kv_we=0;
        core->service_su_red_we=0;
        core->service_su_fault=0;
        core->service_qe_ready=0;
        core->service_qe_idle=0;
        core->service_qe_vi_re=0;
        core->service_qe_xr_re=0;
        core->service_qe_w_we=0;
        core->service_qe_kvb_v=0;
        core->service_qe_kvb_scale=0;
        core->service_qe_kvb_fault=0;
        core->service_qe_qr_re=0;
        core->service_qe_fault=0;
        core->service_xu_ready=0;
        core->service_xu_idle=0;
        core->service_xu_vr_re=0;
        core->service_xu_xr_re=0;
        core->service_xu_vw_we=0;
        core->service_xu_w_we=0;
        core->service_xu_cr_re=0;
        core->service_xu_er_re=0;
        core->service_xu_fault=0;
        core->service_he_ready=0;
        core->service_he_idle=0;
        core->service_he_w_re=0;
        core->service_he_x_re=0;
        core->service_he_o_we=0;
        core->service_he_fault=0;
        core->head_up_valid=0;
        core->head_up_last=0;
        core->head_dn_ready=0;
        core->head_final_valid=0;
        core->capture_reset_request=0;
        core->start=0;
        core->rom_ffault=0;
        core->prime_v=0;
        core->prime_first=0;
        core->cfg_me_xs=0;
        core->pikw_rdy=0;
        core->att_packed_kv_v=0;
        core->att_packed_kv_m=0;
        core->att_packed_kv_fault=0;
        core->win_blk_ready=0;
        core->coll_busy=0;
        core->coll_fault=0;
        core->q_ok=0;
        core->m0_select=0;
        core->m0_ok=0;
        core->kv_ok=0;
        core->rope_pf_rdy=0;
        core->rope_pf_done=0;
        core->rope_pf_fault=0;
        core->service_me0_progress=0;
        core->service_xu_sel_first=0;
        core->entry=0;
        core->prime_cid=0;
        core->service_me0_wrom_addr=0;
        for(unsigned j=0;j<4;++j)core->service_me0_kv_addr[j]=0;
        for(unsigned j=0;j<4;++j)core->service_me0_x_addr[j]=0;
        for(unsigned j=0;j<4;++j)core->service_me0_o_addr[j]=0;
        for(unsigned j=0;j<64;++j)core->service_me0_o_data[j]=0;
        core->service_me0_am_idx=0;
        core->service_me0_am_val=0;
        for(unsigned j=0;j<8;++j)core->service_su_vi_addr[j]=0;
        core->service_su_vm_re=0;
        for(unsigned j=0;j<30;++j)core->service_su_vm_addr[j]=0;
        core->service_su_cr_re=0;
        for(unsigned j=0;j<30;++j)core->service_su_cr_addr[j]=0;
        for(unsigned j=0;j<8;++j)core->service_su_wrom_addr[j]=0;
        for(unsigned j=0;j<8;++j)core->service_su_vm_waddr[j]=0;
        for(unsigned j=0;j<8;++j)core->service_su_vm_wdata[j]=0;
        for(unsigned j=0;j<8;++j)core->service_su_kv_waddr[j]=0;
        for(unsigned j=0;j<8;++j)core->service_su_kv_wdata[j]=0;
        for(unsigned j=0;j<8;++j)core->service_su_red_addr[j]=0;
        for(unsigned j=0;j<8;++j)core->service_su_red_data[j]=0;
        core->service_qe_vi_addr=0;
        core->service_qe_xr_addr=0;
        core->service_qe_w_addr=0;
        core->service_qe_w_mask=0;
        for(unsigned j=0;j<32;++j)core->service_qe_w_data[j]=0;
        core->service_qe_kvb_src_addr=0;
        for(unsigned j=0;j<8;++j)core->service_qe_kvb_codes[j]=0;
        core->service_qe_qr_addr=0;
        core->service_xu_vr_addr=0;
        core->service_xu_xr_addr=0;
        core->service_xu_vw_addr=0;
        core->service_xu_vw_data=0;
        core->service_xu_w_addr=0;
        core->service_xu_w_mask=0;
        for(unsigned j=0;j<32;++j)core->service_xu_w_data[j]=0;
        core->service_xu_cr_addr=0;
        core->service_xu_er_addr=0;
        for(unsigned j=0;j<4;++j)core->service_he_w_addr[j]=0;
        for(unsigned j=0;j<8;++j)core->service_he_x_addr[j]=0;
        core->service_he_o_addr=0;
        core->service_he_o_mask=0;
        for(unsigned j=0;j<32;++j)core->service_he_o_data[j]=0;
        for(unsigned j=0;j<16;++j)core->head_up_data[j]=0;
        for(unsigned j=0;j<16;++j)core->head_final_data[j]=0;
        for(unsigned j=0;j<76;++j)core->capture_root_rows[j]=0;
        for(unsigned j=0;j<4;++j)core->capture_vm_accept[j]=0;
        core->token=0;
        core->pos=0;
        for(unsigned j=0;j<64;++j)core->rom_xq[j]=0;
        core->rom_vq=0;
        for(unsigned j=0;j<276;++j)core->rom_fr[j]=0;
        for(unsigned j=0;j<1124;++j)core->att_from[j]=0;
        for(unsigned j=0;j<64;++j)core->prog_q[j]=0;
        for(unsigned j=0;j<32;++j)core->wrom_q[j]=0;
        for(unsigned j=0;j<256;++j)core->ewrom_q[j]=0;
        for(unsigned j=0;j<24;++j)core->hrom_q[j]=0;
        core->cfg_ik_base=0;
        core->idx_user_base_sec=0;
        for(unsigned j=0;j<64;++j)core->mb_q[j]=0;
        for(unsigned j=0;j<16;++j)core->xs_vi_q[j]=0;
        for(unsigned j=0;j<64;++j)core->xs_rd_q[j]=0;
        for(unsigned j=0;j<64;++j)core->hb_q[j]=0;
        core->ikh_req_rdy=0;
        core->ikh_rsp_v=0;
        for(unsigned j=0;j<16;++j)core->ikh_rsp_tag[j]=0;
        for(unsigned j=0;j<4;++j)core->ikh_rsp_beat[j]=0;
        for(unsigned j=0;j<256;++j)core->ikh_rsp_data[j]=0;
        for(unsigned j=0;j<4;++j)core->pikh_req_rdy[j]=0;
        for(unsigned j=0;j<4;++j)core->pikh_rsp_v[j]=0;
        for(unsigned j=0;j<64;++j)core->pikh_rsp_tag[j]=0;
        for(unsigned j=0;j<16;++j)core->pikh_rsp_beat[j]=0;
        for(unsigned j=0;j<1024;++j)core->pikh_rsp_data[j]=0;
        for(unsigned j=0;j<136;++j)core->qrom_q[j]=0;
        for(unsigned j=0;j<9;++j)core->erom_q[j]=0;
        for(unsigned j=0;j<64;++j)core->crom_q[j]=0;
        for(unsigned j=0;j<64;++j)core->kv_q[j]=0;
        for(unsigned j=0;j<530;++j)core->att_packed_kv_w[j]=0;
        for(unsigned j=0;j<4;++j)core->vx_q[j]=0;
        for(unsigned j=0;j<32;++j)core->vs_q[j]=0;
        for(unsigned j=0;j<8;++j)core->vi_q[j]=0;
        core->vq_q=0;
        core->vr_q=0;
        for(unsigned j=0;j<32;++j)core->wqr_q[j]=0;
        for(unsigned j=0;j<8;++j)core->vh_q[j]=0;
        for(unsigned j=0;j<32;++j)core->wxr_q[j]=0;
        for(unsigned j=0;j<64;++j)core->vsl_q[j]=0;
        core->service_me0_o_mask=0;
        core->head_up_identity=0;
        core->head_final_identity=0;
        core->capture_identity=0;
        core->xcrom_q=0;
    }
    void bind(DsromS81MinimumSourcePlan& plan) {
        require(plan.position==1048575&&plan.identity<(1ull<<47),"HEAD actual owner/position required");
        owner=plan.identity;begin_dot=plan.begin_prefix;
        // The existing capture and native rank0 reducer latch this source owner
        // at accepted I5; bind it before arming the real core command.
        core->capture_identity=owner;
        require(bool(begin_dot),"HEAD native DOT acceptance callback absent");
        plan.begin_prefix=[this,token=plan.token,position=plan.position] {
            require(!armed&&!started&&!dot_accepted&&!terminal,"HEAD core start repeated");
            owner_check();core->token=token;core->pos=position;core->entry=producer_pc;
            armed=true;
        };
    }
    void owner_check() {
        require(runtime.identity&&*runtime.identity==owner,"HEAD core owner differs from shared context");
    }
    DsromS81MinimumParticipant participant() {
        return {"actual-core-HEAD-I5-I6-END",
            [this](const DsromS81PairResult&) {
                try {
                    // Factory has driven live field/capture/final inputs; settle
                    // low only. There is exactly one shared rising/falling edge.
                    core->clk=0;core->rst_n=1;core->start=armed&&!started;
                    core->service_me0_idle=core->service_me0_ready=1;
                    core->service_su_idle=core->service_su_ready=1;
                    core->service_qe_idle=core->service_qe_ready=1;
                    core->service_xu_idle=core->service_xu_ready=1;
                    core->service_he_idle=core->service_he_ready=1;
                    core->eval();unsupported();
                    if(started) {owner_check();healthy();}
                }catch(...){stopped=true;throw;}
            },
            [this](bool reset_n) {
                try {
                    core->rst_n=reset_n;
                    // Reset has no independent local clock, and is cold only.
                    require(reset_n||!started,"warm HEAD reset with actual ownership");
                    if(reset_n) {
                        healthy();unsupported();
                        if(core->start) {require(armed&&!started,"duplicate HEAD acceptance");started=true;}
                        auto* r=core->rootp;
                        const bool dot=r->ot_dsrom_s81_actual_core_end__DOT__rom_m_go;
                        if(dot) {
                            require(started&&!dot_accepted&&
                                r->ot_dsrom_s81_actual_core_end__DOT__pc==producer_pc&&
                                r->ot_dsrom_s81_actual_core_end__DOT__me_amax&&
                                r->ot_dsrom_s81_actual_core_end__DOT__rom_ready_w,
                                "HEAD DOT not accepted under actual I5/source ready");
                            dot_accepted=true;begin_dot();
                        }
                        for(unsigned j=0;j<4;++j)
                            require(core->rom_we[j]==core->capture_vm_accept[j],
                                "live HEAD capture lacks SAME-edge actual VM acceptance");
                        if(core->head_final_valid&&core->head_final_ready) {
                            require(dot_accepted&&!final_taken&&uint64_t(core->head_final_identity)==owner,
                                    "duplicate/wrong-owner actual HEAD final acceptance");
                            for(unsigned j=0;j<16;++j)final_frame[j]=core->head_final_data[j];
                            require(field(final_frame,16,4)==6&&field(final_frame,160,1)==1&&
                                    field(final_frame,128,32)<129280&&
                                    ((field(final_frame,96,32)>>23)&255)!=255,
                                    "actual HEAD final packet kind/ID/finite payload");
                            final_taken=true;
                        }
                        if(r->ot_dsrom_s81_actual_core_end__DOT__st==6&&
                           r->ot_dsrom_s81_actual_core_end__DOT__d_unit==0&&
                           r->ot_dsrom_s81_actual_core_end__DOT__d_ctl==0&&
                           r->ot_dsrom_s81_actual_core_end__DOT__waited) {
                            require(final_taken&&!end_seen&&
                                    r->ot_dsrom_s81_actual_core_end__DOT__pc==end_pc,
                                    "actual END precedes held HEAD acceptance or wrong literal PC");
                            end_seen=true;
                        }
                    }
                    const bool re=core->prog_re;const unsigned addr=core->prog_addr;
                    core->clk=1;core->eval();
                    // These pulses were consumed on the ONE real rising edge.
                    // Do not reinterpret OLD root-valid/VM-accept against the
                    // post-NBA FIFO count: a push fills CAPACITY1 and a pop
                    // empties it. Keep payload/owners and sticky faults intact.
                    for(unsigned root=0;root<128;++root) {
                        const unsigned valid_bit=root*69+68;
                        core->rom_fr[valid_bit/32]&=~(uint32_t(1)<<(valid_bit%32));
                    }
                    for(unsigned j=0;j<4;++j)core->capture_vm_accept[j]=0;
                    core->eval(); // same HIGH clock: combinational settle only
                    // Synchronous program read: CAP sees OLD prog_q. Update
                    // after the edge, preserving real FETCH/WAIT/CAP chronology.
                    if(reset_n&&re) {
                        require(addr>=producer_pc&&addr<=end_pc,"HEAD core fetched outside literal I5/I6");
                        for(unsigned j=0;j<64;++j)core->prog_q[j]=program.at(addr-first_pc)[j];
                    }
                    if(reset_n) {
                        healthy(false);
                        if(core->done) {
                            require(end_seen&&final_taken&&core->next_token==field(final_frame,128,32)&&
                                    core->next_val==field(final_frame,96,32)&&core->capture_drained,
                                    "real END output/ownership differs from accepted native HEAD");
                            terminal=true;
                        }
                    }
                }catch(...){stopped=true;throw;}
            },
            [this](bool reset_n) {core->rst_n=reset_n;core->start=0;core->clk=0;core->eval();},
            [this] {return stopped||bool(core->fault)||capture_sticky_fault();}};
    }
    bool complete()const{return terminal;}
    uint32_t winner()const{return core->next_token;}
    uint32_t value()const{return core->next_val;}
};
}
#endif

namespace {
template<class Function,class Keep> void retain(Function& function,const Keep& keep) {
    if(!function)return;
    auto original=std::move(function);
    function=[original=std::move(original),keep](auto&&... args)->decltype(auto) {
        return original(std::forward<decltype(args)>(args)...);
    };
}
}

extern "C" int dsrom_s81_minimum_source_main(DsromS81MinimumRuntime& runtime,const char* output) {
    if(runtime.stage<0||runtime.stage>=81||runtime.rank<0||runtime.rank>=4||
       !runtime.context||!runtime.tick||!runtime.cold_start||
       !runtime.bind_context||!runtime.result||!runtime.cycle)
        throw std::runtime_error("actual selected S81 native runtime required");
    // Dispatch before constructing any old source VM, plan, or participant.
    // The existing KV owner constructs all four rank homes and owns the one
    // shared cold reset, real publications and native attention retirement.
    const char* attention_mode=std::getenv("DSROM_S81_NATIVE_L20_ATT");
    if(attention_mode&&std::string(attention_mode)!="0"&&std::string(attention_mode)!="1")
        throw std::runtime_error("NATIVE_L20_ATT selector must be explicit 0 or 1");
    if(attention_mode&&std::string(attention_mode)=="1") {
#ifdef DSROM_S81_L20_KV_ENCLOSING
        return dsrom_s81_minimum::run_minimum_l20_kv(runtime,output);
#else
        throw std::runtime_error("NATIVE_L20_ATT requires the selected native KV enclosing source");
#endif
    }
    const char* head_mode=std::getenv("DSROM_S81_NATIVE_HEAD_END");
    const bool head_end=head_mode&&std::string(head_mode)=="1";
#ifndef DSROM_S81_HEAD_WINNER_BINDING_HEADER
    if(head_end)throw std::runtime_error("HEAD_END requires actual selected raw-core archive/header");
#else
    std::shared_ptr<VDsromS81CoreEnd> actual_core;
    std::shared_ptr<HeadEndCore> head;
    if(head_end) {
        const char* arg=runtime.context->commandArgsPlusMatch("OT_ROM_DIR=");
        if(!arg||!*arg)throw std::runtime_error("HEAD_END requires actual +OT_ROM_DIR field/key/stream source");
        const std::string rom_arg(arg);const auto equal=rom_arg.find('=');
        if(equal==std::string::npos||equal+1==rom_arg.size())
            throw std::runtime_error("HEAD_END field/key/stream directory is empty");
        const auto rom_dir=std::filesystem::path(rom_arg.substr(equal+1));
        for(const char* name:{"spine_phase.hex","spine_stream.hex","spine_keys.hex"}) {
            const auto file=rom_dir/name;
            if(!std::filesystem::is_regular_file(file)||!std::filesystem::file_size(file))
                throw std::runtime_error("HEAD_END literal field/key/stream image unavailable");
        }
        actual_core=std::make_shared<VDsromS81CoreEnd>(runtime.context,"source_actual_core_end");
        head=std::make_shared<HeadEndCore>(runtime,actual_core);
    }
#endif
    auto vm=std::make_shared<Vnative_vm>(runtime.context,"source_native_vm");
    // Factory owns actual participant resources and literal selected context,
    // source CFG/ROM and native prefix/return/capture/endpoint event binding.
    auto plan=std::make_shared<DsromS81MinimumSourcePlan>(
#ifdef DSROM_S81_HEAD_WINNER_BINDING_HEADER
        head_end?dsrom_s81_bind_minimum_source(runtime,vm,actual_core):
#endif
        dsrom_s81_bind_minimum_source(runtime,vm));
    const bool seeded=plan->position==1048575;
    const char* native_index=std::getenv("DSROM_S81_NATIVE_L20_INDEX");
    const bool index_component=native_index&&std::string(native_index)=="1";
    if(index_component&&(!seeded||runtime.rank!=3))
        throw std::runtime_error("current index component must use actual rank3 target context");
    // Canonical L20's real field/service allocation is stage37. TRACE_STAGE
    // annotations never authorize starting at an unrelated source context.
    if((head_end&&(!seeded||runtime.stage!=80))||
       (!head_end&&((seeded&&runtime.stage!=37)||(!seeded&&runtime.stage!=0))))
        throw std::runtime_error("source plan and actual canonical stage differ");
    if((seeded?(!plan->attach_seeded||!plan->initialize_seeded||!plan->seeded_inputs_visible):!plan->attach)||
       !plan->begin_prefix||!plan->advance||!plan->complete||plan->token>=129280||
       (seeded?plan->token!=16754:plan->position!=0)||plan->identity>=(1ull<<47))
        throw std::runtime_error("actual minimum source plan/input/publication providers required");
    std::shared_ptr<DsromS81MinimumEmbedding> embedding;
    if(seeded) {
        plan->attach_seeded();
    }else {
        embedding=std::make_shared<DsromS81MinimumEmbedding>(runtime,
            plan->embedding_library,plan->embedding_socket,plan->token,plan->position,
            plan->identity,plan->vm_base,plan->embedding_sink);
        auto embedding_participant=std::move(runtime.participants.back());
        runtime.participants.pop_back();
        runtime.participants.insert(runtime.participants.begin(),std::move(embedding_participant));
        plan->attach(*embedding);
    }
    if(runtime.participants.size()<2||!runtime.publication_ready||!runtime.publication_drained)
        throw std::runtime_error("actual source providers must attach before shared cold reset");
#ifdef DSROM_S81_HEAD_WINNER_BINDING_HEADER
    if(head_end) {
        head->bind(*plan);
        // Factory participants drive first; raw core settles/samples LAST.
        runtime.participants.push_back(head->participant());
    }
    auto keep=std::make_tuple(vm,plan,embedding,actual_core,head);
#else
    auto keep=std::make_tuple(vm,plan,embedding);
#endif
    // Host checks drain after this function returns. Retain model/factory
    // ownership in every callback that can survive the source entry stack.
    for(auto& participant:runtime.participants) {
        retain(participant.prepare,keep);retain(participant.rising,keep);
        retain(participant.falling,keep);retain(participant.fault,keep);
    }
    retain(runtime.publication_ready,keep);retain(runtime.publication_drained,keep);
    runtime.cold_start();
    runtime.bind_context(plan->identity);
    const long input_start=runtime.cycle();
    if(seeded) {
        plan->initialize_seeded();
        while(!plan->seeded_inputs_visible())runtime.tick();
    }else {
        embedding->start();
        while(!embedding->complete())runtime.tick();
    }
    const long input_end=runtime.cycle();
    plan->begin_prefix();
#ifdef DSROM_S81_HEAD_WINNER_BINDING_HEADER
    if(head_end) {
        // complete() is also the actual consumer ACK: do not poll it before END.
        while(!head->complete()) {plan->advance();runtime.tick();}
        if(!runtime.publication_drained(plan->identity)||!runtime.result().quiet||!plan->complete())
            throw std::runtime_error("real HEAD END precedes actual four-rank consumer drain");
    }else
#endif
    while(!plan->complete()) {
        plan->advance();
        runtime.tick();
    }
    // The selected component's actual publication authority is checked
    // independently of arithmetic quiet. A factory cannot turn bank-local zero
    // into retirement of unproduced roots or whole-C8/all-copy authority.
    if(!runtime.publication_drained(plan->identity)||!runtime.result().quiet)
        throw std::runtime_error("source terminal precedes native field/context publication drain");
    if(plan->position==1048575&&!plan->write_measurements)
        throw std::runtime_error("target L20 terminal lacks actual native measurement exporter");
    if(plan->write_measurements)plan->write_measurements(output);
#ifdef DSROM_S81_HEAD_WINNER_BINDING_HEADER
    if(head_end) {
        const auto result_path=std::filesystem::path(output)/"native_head_end.tsv";
        FILE* actual=fopen(result_path.c_str(),"wx");
        if(!actual)throw std::runtime_error("preserve existing actual HEAD END result");
        const int n=fprintf(actual,"identity\ttoken\tvalue_bits\tposition\tterminal_cycle\n"
            "%llu\t%u\t%08x\t%u\t%ld\n",
            (unsigned long long)plan->identity,head->winner(),head->value(),plan->position,runtime.cycle());
        const int close=fclose(actual);
        if(n<0||close)throw std::runtime_error("actual HEAD END result write failed");
    }
#endif
    const auto path=std::filesystem::path(output)/"native_source_component.tsv";
    FILE* journal=fopen(path.c_str(),"wx");
    if(!journal)throw std::runtime_error("preserve existing native source stage results");
    const int wrote=fprintf(journal,"scope\tstage\trank\tpair\tidentity\ttoken\tinput_start\tinput_end\tinput_words\tterminal_cycle\n"
        "%s\t%d\t%d\t%d\t%llu\t%u\t%ld\t%ld\t%u\t%ld\n",
        head_end?(std::getenv("SIM_ONLY_HEAD_ACTUAL_XN")&&
            std::string(std::getenv("SIM_ONLY_HEAD_ACTUAL_XN"))=="1"
            ?"Lhead.I5.I6.SIM_ONLY_HEAD_ACTUAL_XN.actual-core-END":"Lhead.I5.I6.actual-core-END"):index_component?"L20.I36.I44.native-SIM_ONLY-boundary-inputs":seeded?"L20.seeded-native-component":"L0.I7-component-rows0,1",
        runtime.stage,runtime.rank,runtime.pair,(unsigned long long)plan->identity,
        plan->token,input_start,input_end,index_component?4256u:seeded?20480u:embedding->committed_words(),runtime.cycle());
    const int closed=fclose(journal);
    if(wrote<0||closed)throw std::runtime_error("native source stage result write failed");
    return 0;
}
