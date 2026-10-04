#pragma once
#include "s81_minimum_runtime.hpp"
#include "s81_minimum_pair_stage.hpp"
#include "Vcut.h"
#include "Vcut___024root.h"
#include "verilated.h"
#include <memory>
#include <stdexcept>

namespace dsrom_s81_minimum {
// Head uses the retained source cut solely for real BF input load/broadcast.
// All K5120 source words are held BEFORE logit writes may overlap XN.
// Runtime owns every eval edge. This participant never clocks a private loop.
class NativeBfHeadInput {
    DsromS81MinimumRuntime& rt;
    Vcut& cut;
    std::function<std::optional<uint32_t>(uint64_t,uint32_t)> read;
    std::function<bool(uint64_t,uint32_t,unsigned)> lease;
    uint64_t identity=0;
    unsigned loaded=0;
    bool cold=false,armed=false,issued=false,saw_go=false;
    DsromS81PairDrive drive() const {
        DsromS81PairDrive p{};
        p.cfg_go=cut.fb_cfg_go;p.cfg_ph=cut.fb_cfg_ph;p.cfg_np=cut.fb_cfg_np;
        p.go=cut.fb_go;p.go_bf=cut.fb_go_bf;
        p.xs_v=cut.fb_xs_v;p.xs_p=cut.fb_xs_p;p.xs_b=cut.fb_xs_b;p.xs_sv=cut.fb_xs_sv;
        p.xs_e0=cut.fb_xs_e0;p.xs_e1=cut.fb_xs_e1;p.xs_pos=cut.fb_xs_pos;
        for(unsigned i=0;i<8;i++){p.xs_q0[i]=cut.fb_xs_q0[i];p.xs_q1[i]=cut.fb_xs_q1[i];}
        p.xb_pos=cut.fb_xb_pos;p.xb_v=cut.fb_xb_v;p.xb_b=cut.fb_xb_b;
        p.xb_sv=cut.fb_xb_sv;p.xb_u=cut.fb_xb_u;
        for(unsigned i=0;i<32;i++)p.xb_d[i]=cut.fb_xb_d[i];
        return p;
    }
    void prepare(const DsromS81PairResult&) {
        cut.go=0;
        if(armed) {
            if(!rt.identity || *rt.identity!=identity)throw std::runtime_error("head XN identity changed");
            if(loaded<5120 && lease(identity,46464,5120)) {
                auto w=read(identity,46464+loaded);
                if(w){
                    // Source head m_round0: normalized XN must already be
                    // BF16-widened. Native cut RNE is then the identity, not
                    // an extra rounding point hidden in a BF input wrapper.
                    if(*w&65535u)throw std::runtime_error("unrounded head XN is not BF16-widened");
                    cut.rootp->dsrom_source_cut__DOT__dut__DOT__vm[46464+loaded]=*w;loaded++;
                }
            }
            if(!issued && loaded==5120 && cut.ready)cut.go=1;
        }
        rt.drive(drive());
    }
    void rising(bool released) {
        bool accepted=released&&cut.go&&cut.ready;
        if(released&&cut.fb_go) {
            if(!armed||!issued||!cut.fb_go_bf)throw std::runtime_error("actual head BF GO missing admission");
            saw_go=true;
        }
        cut.clk=1;cut.rst_n=released;cut.eval();
        if(!released)cold=true;
        if(accepted)issued=true;
    }
public:
    NativeBfHeadInput(DsromS81MinimumRuntime& r,Vcut& c,
        std::function<std::optional<uint32_t>(uint64_t,uint32_t)> actual_read,
        std::function<bool(uint64_t,uint32_t,unsigned)> actual_lease)
        :rt(r),cut(c),read(std::move(actual_read)),lease(std::move(actual_lease)) {
        if(!rt.context||cut.contextp()!=rt.context||!rt.bf16||!rt.drive||!read||!lease)
            throw std::runtime_error("head retained cut/PB/source IO required");
        // Borrowed cut pins belong to the existing cold owner. Inactive
        // HEAD must not drive GO, clocks, or reset even in its constructor.
    }
    void arm(uint64_t id,unsigned phase,const std::array<uint64_t,2>& ph,
             const std::vector<uint64_t>& stream) {
        if(!cold||id>=(1ull<<47)||!rt.identity||*rt.identity!=id||phase>1 ||
           (armed&&(!finished()||!cut.idle||!rt.result().quiet)))
            throw std::runtime_error("head phase arm before native previous return/input drain");
        if(armed&&identity!=id)throw std::runtime_error("head XN snapshot owner cannot be rebound");
        unsigned k=(ph[0]>>1)&8191,beats=(ph[0]>>14)&65535,base=(ph[0]>>30)&65535;
        if(!(ph[0]&1)||k!=5120||((ph[0]>>46)&65535)!=2||((ph[0]>>62)&3)!=3||ph[1] ||
            !beats||beats!=stream.size()||base+beats>16384)
            throw std::runtime_error("head BF K5120 FP32 two-row PHROM required");
        identity=id;
        auto* root=cut.rootp;
        root->dsrom_source_cut__DOT__dut__DOT__u_sp__DOT__phrom[phase*2]=ph[0];
        root->dsrom_source_cut__DOT__dut__DOT__u_sp__DOT__phrom[phase*2+1]=ph[1];
        for(unsigned i=0;i<beats;i++) {
            if(stream[i]>>48)throw std::runtime_error("head BF stream width");
            root->dsrom_source_cut__DOT__dut__DOT__u_sp__DOT__strom[base+i]=stream[i];
        }
        // Explicit private input-only alias 0..1. Actual head logits route
        // 30428+local_row through carried output, NEVER these cut VM writes.
        cut.i_ph=phase;cut.i_np=0;cut.i_xbase=46464;cut.i_xps=0;cut.i_obase=0;cut.i_ops=2;
        armed=true;issued=false;saw_go=false;
    }
    void observe_shared_cold_reset() {
        if(rt.identity||!rt.cycle||rt.cycle()!=0||cut.rst_n)
            throw std::runtime_error("head shared cold reset not actually observed");
        cold=true; // no eval: caller's ONE selected cut participant owns edge
    }
    DsromS81MinimumParticipant participant() {
        return {"native_bf_head_input",[this](const auto& p){prepare(p);},
          [this](bool r){rising(r);},[this](bool r){cut.clk=0;cut.rst_n=r;cut.eval();},
          [this](){return bool(cut.fault);}};
    }
    void release_snapshot() {
        if(!armed||!finished()||!cut.idle||!rt.result().quiet)
            throw std::runtime_error("head XN snapshot release before actual input/return drain");
        loaded=0;armed=false;issued=false;saw_go=false;
    }
    bool finished()const{return issued&&saw_go&&!cut.obs_ld_run&&!cut.obs_sm_run&&!cut.fault;}
    bool snapshot_ready()const{return loaded==5120;}
    Vcut& native_cut(){return cut;}
};

// Exact released raw BF274 read routing. Two local native banks map to
// actual adjacent head rows; physical source homes are supplied by the
// ReleasedHeadByteProvider callback, NOT a field pair allocation fallback.
class NativeBfHeadRom {
public:
    using Word=std::array<uint32_t,9>;
    using Read=std::function<Word(unsigned,unsigned,unsigned,unsigned)>;
private:
    Read read;
    unsigned rank=0,rowpair=0,grain=0;
    bool held=false;
public:
    explicit NativeBfHeadRom(Read released):read(std::move(released)) {
        if(!read)throw std::runtime_error("released head native BF byte provider required");
    }
    void bind(unsigned r,unsigned pair,unsigned g,bool native_quiet,bool prior_roots_taken) {
        if(r>=4||pair>=16160||g>1||!native_quiet||!prior_roots_taken)
            throw std::runtime_error("head native ROM rebind before subtree return closure");
        rank=r;rowpair=pair;grain=g;held=true;
    }
    Word word(unsigned bank,unsigned address)const {
        if(!held||bank>1||address>=(grain?64u:256u))throw std::runtime_error("unowned head ROM read");
        unsigned q=address/64,b=(address%64)/8,j=address%8;
        auto w=read(rank,2*rowpair+bank,(grain?32:0)+8*q+j,b);
        if(w[8]>>18)throw std::runtime_error("head native provider exceeds raw274 container");
        return w;
    }
};

// Only transports actual pair partials through retained branch/root models.
// One segment per local row: native return performs no cross-grain add.
// The receiver owns A/B roots until actual carried in_ready acceptance.
template<class Branch,class Root> class NativeBfHeadReturn {
    DsromS81MinimumRuntime& rt;
    Branch branch;
    Root root;
    Vcut& cut;
    bool bound=false,stopped=false;
    unsigned grain=0,seen=0,seen_mask=0;
    std::array<std::optional<uint32_t>,2> values;
    bool sampled_valid=false,sampled_error=false;
    unsigned sampled_row=0,sampled_pos=0;
    uint32_t sampled_value=0;
    static uint32_t tag(const Partial& p) {
        if(p.row>1||p.segment||p.segments!=1||p.position)
            throw std::runtime_error("head partial outside accepted local two-row subtree");
        return (uint32_t(p.row)<<13)|1;
    }
    template<class Packed> static void pin(Packed& packed,unsigned offset,unsigned width,uint32_t value) {
        for(unsigned i=0;i<width;i++) {
            auto mask=uint32_t(1)<<((offset+i)%32);
            packed[(offset+i)/32]=(packed[(offset+i)/32]&~mask)|(((value>>i)&1)?mask:0);
        }
    }
    void prepare(const DsromS81PairResult& result) {
        sampled_valid=root.r_v;sampled_error=root.r_e;sampled_row=root.r_row;
        sampled_pos=root.r_pos;sampled_value=root.r_fp32;
        root.i_v=branch.o_v;root.i_t=branch.o_t;root.i_d=branch.o_d;root.i_e=branch.o_e;
        auto a=partial(result,0),b=partial(result,1);
        if((a.valid||b.valid)&&!bound)throw std::runtime_error("head partial without held grain");
        branch.a_v=a.valid;branch.a_e=a.error;branch.a_d=a.fp32_bits;branch.a_t=a.valid?tag(a):0;
        branch.b_v=b.valid;branch.b_e=b.error;branch.b_d=b.fp32_bits;branch.b_t=b.valid?tag(b):0;
        // Actual observed root0 only; no peer completion injection. Two-row
        // private PHROM quota is root0=2, all other quotas are naturally zero.
        pin(cut.fr_v,0,1,root.r_v);pin(cut.fr_e,0,1,root.r_e);
        pin(cut.fr_row,0,16,root.r_row);pin(cut.fr_pos,0,3,root.r_pos);
        pin(cut.fr_fp32,0,32,root.r_fp32);pin(cut.fr_bf16,0,16,root.r_bf16);
        cut.fr_fault=bool(cut.fr_fault)||bool(branch.fault)||bool(root.fault);
    }
public:
    NativeBfHeadReturn(DsromS81MinimumRuntime& r,Vcut& c):rt(r),
        branch(r.context,"native_head_retained_branch"),root(r.context,"native_head_retained_root"),cut(c) {
        branch.clk=0;branch.rst_n=0;branch.a_v=0;branch.b_v=0;
        branch.a_t=0;branch.b_t=0;branch.a_d=0;branch.b_d=0;branch.a_e=0;branch.b_e=0;
        root.clk=0;root.rst_n=0;root.i_v=0;root.i_t=0;root.i_d=0;root.i_e=0;
        branch.eval();root.eval();
    }
    void bind(unsigned g) {
        if(g>1||stopped||(bound&&(seen!=2||values[0]||values[1])))
            throw std::runtime_error("head subtree return still owned");
        grain=g;seen=0;seen_mask=0;values={};bound=true;
    }
    std::optional<uint32_t> take(unsigned row) {
        if(row>1)throw std::runtime_error("head local row");
        auto v=values[row];values[row].reset();return v;
    }
    bool roots_taken()const{return !bound||(seen==2&&!values[0]&&!values[1]&&branch.quiet&&!branch.o_v&&!root.r_v&&!root.obs_qc&&!root.obs_held);}
    DsromS81MinimumParticipant participant() {
        return {"native_bf_head_return",[this](const auto& p){prepare(p);},
          [this](bool r){
            if(!r&&bound)throw std::runtime_error("reset cannot clear accepted head roots");
            branch.clk=1;branch.rst_n=r;root.clk=1;root.rst_n=r;branch.eval();root.eval();
            if(r&&sampled_valid) {
                if(!bound||sampled_error||sampled_pos||sampled_row>1||seen>=2||(seen_mask&(1u<<sampled_row)))
                    throw std::runtime_error("head native root error/identity/duplicate");
                values[sampled_row]=sampled_value;seen_mask|=1u<<sampled_row;seen++;
            }
          },[this](bool r){branch.clk=0;branch.rst_n=r;root.clk=0;root.rst_n=r;branch.eval();root.eval();},
          [this](){return stopped||bool(branch.fault)||bool(root.fault);}};
    }
};
} // namespace dsrom_s81_minimum

namespace dsrom_s81_minimum {
struct NativeBfHeadPhase {
    std::array<uint64_t,25> cfg{};
    std::array<uint64_t,2> phrom{};
    std::vector<uint64_t> stream;
};
inline NativeBfHeadPhase native_bf_head_phase(unsigned grain) {
    if(grain>1)throw std::runtime_error("head grain ordinal");
    unsigned u0=grain?32:0,nu=grain?8:32;
    NativeBfHeadPhase p{};
    p.cfg[0]=(1ull<<21)|(1ull<<42);
    p.cfg[8]=1|(uint64_t(u0)<<1)|(uint64_t(nu)<<9)|(1ull<<22);
    p.cfg[16]=nu/8-1;p.cfg[17]=1;
    for(unsigned q=0;q<nu/8;q++)for(unsigned b=0;b<8;b++) {
        std::array<uint64_t,8> slots{};
        for(unsigned group=0;group<2;group++) {
            uint64_t word=1|(b<<1);
            for(unsigned lane=0;lane<4;lane++)word|=(1ull<<(4+lane))|
                (uint64_t(u0+q*8+group*4+lane)<<(8+8*lane));
            slots[group*3]=word;
        }
        p.stream.insert(p.stream.end(),slots.begin(),slots.end());
    }
    p.phrom={1ull|(5120ull<<1)|(uint64_t(p.stream.size())<<14)|(2ull<<46)|(3ull<<62),0};
    return p;
}
struct NativeBfHeadRoots {
    uint64_t identity,request_sequence;
    unsigned rank,local_row;
    uint32_t root4096,root1024;
};
// Actual producer orchestration, not an arithmetic interpreter. The native
// sink must drive Boole's real in_valid/in_ready; false keeps both roots owned.
// It may not replace an offered root by an expected/golden value.
template<class Branch,class Root> class NativeBfHeadProducer {
    DsromS81MinimumRuntime& rt;
    Vcut& cut;
    NativeBfHeadInput input;
    NativeBfHeadReturn<Branch,Root> returned;
    NativeBfHeadRom rom;
    std::function<bool(const NativeBfHeadRoots&)> sink;
    std::array<NativeBfHeadPhase,2> phases{native_bf_head_phase(0),native_bf_head_phase(1)};
    std::array<std::array<std::optional<uint32_t>,2>,2> roots{};
    uint64_t identity=0,sequence=0;
    unsigned rank=0,rowpair=0,grain=0,offered=0;
    bool started=false,done=false;unsigned rank_seen=0;
    void arm() {
        rom.bind(rank,rowpair,grain,rt.result().quiet,returned.roots_taken());
        returned.bind(grain);
        input.arm(identity,grain,phases[grain].phrom,phases[grain].stream);
    }
public:
    NativeBfHeadProducer(DsromS81MinimumRuntime& r,Vcut& actual_shared_cut,
        std::function<std::optional<uint32_t>(uint64_t,uint32_t)> read,
        std::function<bool(uint64_t,uint32_t,unsigned)> lease,
        NativeBfHeadRom::Read raw_head,std::function<bool(const NativeBfHeadRoots&)> native_sink,
        bool register_standalone_participants=false)
        :rt(r),cut(actual_shared_cut),input(r,cut,std::move(read),std::move(lease)),
         returned(r,cut),rom(std::move(raw_head)),sink(std::move(native_sink)) {
        if(!sink)throw std::runtime_error("actual carried head root consumer required");
        if(register_standalone_participants) {
            rt.participants.push_back(input.participant());
            rt.participants.push_back(returned.participant());
        }
    }
    DsromS81MinimumParticipant input_participant(){return input.participant();}
    DsromS81MinimumParticipant return_participant(){return returned.participant();}
    void observe_shared_cold_reset(){input.observe_shared_cold_reset();}
    void start(uint64_t owner,uint64_t request_sequence,unsigned actual_rank) {
        if(actual_rank>=4||owner>=(1ull<<47)||!rt.identity||*rt.identity!=owner||
           (rank_seen&(1u<<actual_rank)) || (started&&(!done||identity!=owner||sequence!=request_sequence)))
            throw std::runtime_error("actual head producer start owner/rank/previous accepted roots");
        if(started) {
            if(!returned.roots_taken())throw std::runtime_error("previous head return still owned");
            input.release_snapshot();
        }
        identity=owner;sequence=request_sequence;rank=actual_rank;
        rowpair=0;grain=0;offered=0;roots={};done=false;started=true;
        rank_seen|=1u<<actual_rank;arm();
    }
    // Call only from caller's between-edge control loop. No eval or tick here.
    void advance() {
        if(!started||done)return;
        for(unsigned row=0;row<2;row++)if(!roots[grain][row])roots[grain][row]=returned.take(row);
        if(!roots[grain][0]||!roots[grain][1]||!returned.roots_taken()||
           !input.finished()||!cut.idle||!rt.result().quiet)return;
        if(grain==0){grain=1;arm();return;}
        while(offered<2) {
            NativeBfHeadRoots command{identity,sequence,rank,2*rowpair+offered,
                                     *roots[0][offered],*roots[1][offered]};
            // A real consumer acceptance can occur at most once per host
            // advance invocation. Do not synthesize two grouped accepts.
            if(!sink(command))return;
            offered++;return;
        }
        rowpair++;offered=0;roots={};grain=0;
        if(rowpair==16160){done=true;return;}
        arm();
    }
    bool active()const{return started&&!done;}
    bool all_roots_accepted()const{return done;}
    bool snapshot_ready()const{return input.snapshot_ready();}
    Vcut& native_cut(){return cut;}
    NativeBfHeadRom::Word raw_word(unsigned bank,unsigned address)const {
        if(!active())throw std::runtime_error("native head ROM request outside active producer");
        return rom.word(bank,address);
    }
    uint64_t cfg_word(unsigned address)const {
        if(!active()||address>=50)throw std::runtime_error("native head CFG request outside active producer");
        return phases[address/25].cfg[address%25];
    }
};
} // namespace dsrom_s81_minimum
