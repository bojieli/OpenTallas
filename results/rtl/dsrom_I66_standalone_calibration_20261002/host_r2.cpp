// Additive simulation-only host, actual module ports; no payload checkpoints.
#include "Vcut.h"
#include "Vpq.h"
#include "Vpb.h"
#include "Vretn.h"
#include "Vroot.h"
#include "Vpq___024root.h"
#include "Vpb___024root.h"
#include "Vretn___024root.h"
#include "Vroot___024root.h"
#include "svdpi.h"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <memory>
#include <vector>
#include <sys/resource.h>
#include <type_traits>
constexpr int CW=25;
static long edge=0;
static int phase=10;
struct PairMem {int pair=0;std::array<uint64_t,25> cfg{};};
static std::vector<PairMem> g_mem;
static PairMem* g_reg=nullptr;
static std::unordered_map<const void*,std::pair<PairMem*,int>> g_romscope;
static std::unordered_map<const void*,PairMem*> g_cfgscope;
static FILE* journal=nullptr;
static uint64_t event_ordinal=0;
static void ev(const char* kind,int a=-1,int b=-1,uint64_t c=0) {
 fprintf(journal,"{\"ordinal\":%llu,\"stage\":0,\"rank\":0,\"phase\":10,\"key_word\":2149580800,\"reset_era\":0,\"edge\":%ld,\"kind\":\"%s\",\"a\":%d,\"b\":%d,\"c\":%llu}\n",(unsigned long long)event_ordinal++,edge,kind,a,b,(unsigned long long)c);
}
extern "C" void v41rt_rom_register(const char* inst) {
 if(!g_reg) exit(3);
 int mb=(inst&&strlen(inst)&&inst[strlen(inst)-1]=='b')?1:0;
 g_romscope[svGetScope()]={g_reg,mb};
}
extern "C" void v41rt_rom_read(int addr,svBitVecVal* q) {
 auto it=g_romscope.find(svGetScope());if(it==g_romscope.end()||addr<0||addr>=8192)exit(3);
 for(int k=0;k<9;k++)q[k]=0;
 for(int nib=0;nib<32;nib++){q[(4*nib)/32]|=2u<<((4*nib)%32);q[(136+4*nib)/32]|=2u<<((136+4*nib)%32);}
 q[4]|=127u; q[8]|=127u<<8; // two E8M0 scales1, all FP4 coefficient codes2 =1.
 ev("macro_read_accept",it->second.first->pair,it->second.second,addr);
}
extern "C" void v41rt_cfg_register() {if(!g_reg)exit(3);g_cfgscope[svGetScope()]=g_reg;}
extern "C" long long v41rt_cfg_read(int addr) {
 auto it=g_cfgscope.find(svGetScope());if(it==g_cfgscope.end())exit(3);
 int k=addr-phase*CW;if(k<0||k>=CW){ev("FAIL_cfg_address",it->second->pair,k,addr);exit(3);}
 ev("cfg_ROM_read_accept",it->second->pair,k,addr);
 return (long long)it->second->cfg[k];
}
// ---- bit helpers over Verilator port types --------------------------------------------------------------
template <class V> static uint64_t getb(const V& v, size_t pos, int n) {
    if constexpr (std::is_integral_v<V>) {
        return (uint64_t(v) >> pos) & (n >= 64 ? ~0ull : ((1ull << n) - 1));
    } else {
        uint64_t r = 0;
        for (int b = 0; b < n; b++) r |= uint64_t((v[(pos + b) / 32] >> ((pos + b) % 32)) & 1) << b;
        return r;
    }
}
template <class V> static void setb(V& v, size_t pos, int n, uint64_t x) {
    if constexpr (std::is_integral_v<V>) {
        uint64_t m = (n >= 64 ? ~0ull : ((1ull << n) - 1)) << pos;
        v = (V)((uint64_t(v) & ~m) | ((x << pos) & m));
    } else {
        for (int b = 0; b < n; b++) {
            uint32_t& w = v[(pos + b) / 32];
            uint32_t bit = 1u << ((pos + b) % 32);
            w = ((x >> b) & 1) ? (w | bit) : (w & ~bit);
        }
    }
}
template <class A, class B> static bool same(const A& a, const B& b) {
    if constexpr (std::is_integral_v<A>) return uint64_t(a) == uint64_t(b);
    else { for (size_t i = 0; i < sizeof(a) / 4; i++) if (a[i] != b[i]) return false; return true; }
}
static std::vector<std::string> split(const std::string& s) {
    std::istringstream is(s); std::vector<std::string> r; std::string t;
    while (is >> t) r.push_back(t);
    return r;
}
struct Node { uint8_t v, e; uint32_t t, d; };
constexpr bool is_bf(int p) {
    for (int i = 0; i < NBF; i++) if ((i * NP) / NBF == p) return true;
    return false;
}
struct Field {
    static constexpr int NL = 2 * NP;
    static constexpr int LR = __builtin_ctz(NR), L = __builtin_ctz(NL), LS = L - LR;
    VerilatedContext& context;
    Vcut& top;
    std::vector<std::unique_ptr<Vpq>> pq;
    std::vector<std::unique_ptr<Vpb>> pb;
    std::vector<int> kind, idx;                                    // per pair: 0 pq / 1 pb, index
    std::vector<std::vector<std::unique_ptr<Vretn>>> nodes;       // [level][position]
    std::vector<std::unique_ptr<Vroot>> roots;
    size_t nmodels() const { return size_t(NP) + nn + roots.size(); }
    size_t nn = 0;
    std::vector<std::pair<int, int>> nlist;                        // flattened (level, position)
    Field(Vcut& t, VerilatedContext& p, const std::string& dir) : context(p), top(t) {
        g_mem.resize(NP);
        for (int g = 0; g < NP; g++) g_mem[g].pair = g;
        for (int g = 0; g < NP; g++) {
            g_reg = &g_mem[g];
            std::string nm = "p" + std::to_string(g);
            if (is_bf(g)) { pb.emplace_back(new Vpb(&context, nm.c_str())); kind.push_back(1); idx.push_back(int(pb.size()) - 1); pb.back()->eval(); }
            else { pq.emplace_back(new Vpq(&context, nm.c_str())); kind.push_back(0); idx.push_back(int(pq.size()) - 1); pq.back()->eval(); }
        }
        g_reg = nullptr;
        nodes.resize(LS);
        for (int l = 0; l < LS; l++)
            for (int g = 0; g < (NL >> (l + 1)); g++) {
                std::string nm = "n" + std::to_string(l) + "_" + std::to_string(g);
                nodes[l].emplace_back(new Vretn(&context, nm.c_str()));
                nlist.push_back({l, g}); nn++;
            }
        for (int g = 0; g < NR; g++) roots.emplace_back(new Vroot(&context, ("r" + std::to_string(g)).c_str()));
    }
    template <class F> void each_pair(int g, F f) { if (kind[g]) f(*pb[idx[g]]); else f(*pq[idx[g]]); }
    void eval_all(uint8_t clk, uint8_t rst) {
        for (size_t ii = 0; ii < nmodels(); ++ii) { auto eval_one = [&](size_t i) {
            if (i < size_t(NP)) { each_pair(int(i), [&](auto& m) { m.clk = clk; m.rst_n = rst; m.eval(); }); return; }
            i -= NP;
            if (i < nn) { auto& n = *nodes[nlist[i].first][nlist[i].second]; n.clk = clk; n.rst_n = rst; n.eval(); return; }
            i -= nn;
            auto& r = *roots[i]; r.clk = clk; r.rst_n = rst; r.eval();
        }; eval_one(ii); }
    }
    // leaf (macro) partial of pair g, macro m
    Node leaf(int g, int m) {
        Node o{};
        each_pair(g, [&](auto& x) {
            o.v = (x.pv >> m) & 1; o.e = (x.perr >> m) & 1;
            o.d = uint32_t(getb(x.pval, 32 * m, 32));
            uint32_t pos = uint32_t(getb(x.ppos, 3 * m, 3)), row = uint32_t(getb(x.prow, 16 * m, 16));
            uint32_t seg = uint32_t(getb(x.pseg, 5 * m, 5)), ns = uint32_t(getb(x.pnseg, 5 * m, 5));
            o.t = (pos << 29) | (row << 13) | (seg << 8) | ns;
        });
        return o;
    }
    Node level_out(int l, int g) {       // output of level l (0 = leaves) position g
        if (l == 0) return leaf(g >> 1, g & 1);
        auto& n = *nodes[l - 1][g];
        return Node{n.o_v, n.o_e, n.o_t, n.o_d};
    }
    // copy broadcast to pairs
    template <class M> void bcast(M& m) {
        m.cfg_go = top.fb_cfg_go; m.cfg_ph = top.fb_cfg_ph; m.cfg_np = top.fb_cfg_np; m.go = top.fb_go;
        m.go_bf = top.fb_go_bf; m.xs_v = top.fb_xs_v; m.xs_p = top.fb_xs_p; m.xs_b = top.fb_xs_b;
        m.xs_sv = top.fb_xs_sv; m.xs_q0 = top.fb_xs_q0; m.xs_e0 = top.fb_xs_e0; m.xs_q1 = top.fb_xs_q1;
        m.xs_e1 = top.fb_xs_e1; m.xs_pos = top.fb_xs_pos; m.xb_pos = top.fb_xb_pos; m.xb_v = top.fb_xb_v;
        m.xb_b = top.fb_xb_b; m.xb_sv = top.fb_xb_sv; m.xb_u = top.fb_xb_u; m.xb_d = top.fb_xb_d;
    }
    void to_pairs(int g) { each_pair(g, [&](auto& m) { bcast(m); }); }
    void to_node(int l, int g) {         // inputs of node (l, g) from level l outputs 2g, 2g+1
        auto& n = *nodes[l][g];
        Node a = level_out(l, 2 * g), b = level_out(l, 2 * g + 1);
        n.a_v = a.v; n.a_t = a.t; n.a_d = a.d; n.a_e = a.e; n.b_v = b.v; n.b_t = b.t; n.b_d = b.d; n.b_e = b.e;
    }
    void to_root(int g) {
        auto& r = *roots[g];
        Node a = level_out(LS, g);
        r.i_v = a.v; r.i_t = a.t; r.i_d = a.d; r.i_e = a.e;
    }
    void to_top() {
        uint64_t f = 0;
        for (int g = 0; g < NR; g++) {
            auto& r = *roots[g];
            setb(top.fr_v, g, 1, r.r_v); setb(top.fr_row, 16 * g, 16, r.r_row); setb(top.fr_pos, 3 * g, 3, r.r_pos);
            setb(top.fr_fp32, 32 * g, 32, r.r_fp32); setb(top.fr_bf16, 16 * g, 16, r.r_bf16); setb(top.fr_e, g, 1, r.r_e);
            f |= r.fault;
        }
        for (int g = 0; g < NP; g++) each_pair(g, [&](auto& m) { f |= m.fault; });
        for (auto& lv : nodes) for (auto& n : lv) f |= n->fault;
        top.fr_fault = f ? 1 : 0;
    }
    void propagate() {
        for(int g=0;g<NP;++g) to_pairs(g);
        for (int l = 0; l < LS; l++) for (int g = 0; g < (NL >> (l + 1)); g++) to_node(l, g);
        for (int g = 0; g < NR; g++) to_root(g);
        to_top();
    }
};


int main(int argc,char**argv) {
 if(argc!=3){fprintf(stderr,"usage: gate IMG JOURNAL\n");return 2;}
 std::string dir=argv[1],plus="+OT_ROM_DIR="+dir;
 journal=fopen(argv[2],"wx");if(!journal)return 3;
 const char*av[]={"gate",plus.c_str()};
 constexpr uint64_t object_est=(uint64_t(NP-NBF)*(sizeof(Vpq)+sizeof(Vpq___024root))+uint64_t(NBF)*(sizeof(Vpb)+sizeof(Vpb___024root))+uint64_t(2*NP-NR)*(sizeof(Vretn)+sizeof(Vretn___024root))+uint64_t(NR)*(sizeof(Vroot)+sizeof(Vroot___024root)))*14/10+128*1024*1024;
 printf("CAPACITY NP=%d NBF=%d R=%d estimate_bytes=%llu pq=%zu pb=%zu node=%zu root=%zu\n",NP,NBF,NR,(unsigned long long)object_est,sizeof(Vpq___024root),sizeof(Vpb___024root),sizeof(Vretn___024root),sizeof(Vroot___024root));
 if(object_est>6ull*1024*1024*1024){printf("FAIL_preallocation_capacity\n");return 4;}
 VerilatedContext ctx;ctx.threads(1);ctx.randReset(0);ctx.commandArgs(2,av);
 VerilatedContext topctx;topctx.threads(1);topctx.randReset(0);topctx.commandArgs(2,av);
 Vcut cut(&topctx,"cut");cut.eval();
 Field fld(cut,ctx,dir);
 {std::ifstream f(dir+"/config.txt");int g,k;std::string v;while(f>>g>>k>>v){if(g<0||g>=NP||k<0||k>=25)return 3;g_mem[g].cfg[k]=std::stoull(v,nullptr,16);}}
 long writes=0,roots=0,ce=0,captures=0,consumers=0,cfgwrites=0;bool seenrun=false,done=false,spinedone=false,phaseaccepted=false,spinebusy=false;int stable=0;
 std::array<bool,576> wrseen{};std::array<bool,576> rtseen{};
 std::vector<std::vector<std::pair<long,int>>> debts(NP);
 for(edge=0;edge<4096;++edge) {
  bool rst=edge>=6;cut.rst_n=rst;cut.go=edge==10;cut.i_ph=phase;cut.i_np=0;cut.i_xbase=46464;cut.i_xps=5120;cut.i_obase=398720;cut.i_ops=576;
  // All events sampled on the input side BEFORE the rising edge. Every
  // model samples old producer registers, then ports propagate together.
  if(rst) {
   if(cut.go&&cut.ready)ev("op_accept",phase);
   if(cut.obs_VI_re)ev("EID_VM_read_accept",cut.obs_VI_addr);
   if(cut.obs_phase_accept){phaseaccepted=true;ev("phase_accept",cut.obs_phase,-1,cut.obs_key);}
   if(phaseaccepted&&!cut.obs_spine_idle)spinebusy=true;
   if(cut.obs_VM_re)ev("VM_read_accept",cut.obs_VM_addr,64);
   if(cut.obs_AQ_in)ev("AQ_input_accept",cut.obs_AQ_k);
   if(cut.obs_AQ_out)ev("AQ_output_capture",cut.obs_have);
   if(cut.obs_sm_adv)ev("stream_ROM_advance",cut.obs_sm_i,-1,cut.obs_sm_word);
   if(cut.obs_sm_wait)ev("stream_have_stall",cut.obs_sm_i,cut.obs_sm_have,cut.obs_sm_need);
   if(cut.fb_cfg_go)ev("field_cfg_accept",cut.fb_cfg_ph);
   if(cut.fb_go)ev("field_go_accept");
   if(cut.fb_xs_v)ev("activation_field_accept",cut.fb_xs_p,cut.fb_xs_b,cut.fb_xs_sv);
   bool allquiet=true;
   for(int g=0;g<NP;++g)fld.each_pair(g,[&](auto&m){
    if(m.obs_cfg_write){++cfgwrites;ev("cfg_element_write_accept",g,m.obs_cfg_word,m.obs_cfg_data);if(m.obs_cfg_data!=g_mem[g].cfg[m.obs_cfg_word]){ev("FAIL_cfg_payload",g,m.obs_cfg_word);exit(5);}}
    if(m.obs_go_e)ev("active_pair_go_accept",g);
    if(m.obs_issue){++ce;ev("main_CE_accept",g,-1,m.obs_addr);debts[g].push_back({edge,m.obs_addr});}
    if(m.obs_capture){++captures;ev("bank_capture",g,m.obs_cap_bank);}
    if(m.obs_consume){++consumers;ev("lane_consumer_sample",g);}
    if(m.fault){ev("FAIL_pair_fault",g);exit(6);}
    allquiet=allquiet&&m.quiet;
   });
   for(int g=0;g<NP;++g)for(int mb=0;mb<2;++mb){Node n=fld.leaf(g,mb);if(n.v)ev("pair_partial",g,mb,n.t);}
   for(auto&lv:fld.nodes)for(auto&n:lv){if(n->fault){ev("FAIL_node_fault");exit(7);}allquiet=allquiet&&n->quiet;}
   for(int g=0;g<NR;++g){auto&r=*fld.roots[g];allquiet=allquiet&&!r.i_v&&!r.r_v&&!r.obs_qc&&!r.obs_held&&!r.obs_add&&!r.obs_sv;if(r.fault){ev("FAIL_root_fault",g);exit(8);}
    if(r.r_v){++roots;ev("root_row_accept",g,r.r_row,r.r_fp32);if(r.r_row>=576||rtseen[r.r_row]||r.r_e){ev("FAIL_root_identity",g,r.r_row);exit(9);}rtseen[r.r_row]=true;}
   }
   bool any_writer=false;for(int g=0;g<NR;++g)if(getb(cut.o_we,g,1)){any_writer=true;int ad=getb(cut.o_addr,VAW*g,VAW);uint32_t data=getb(cut.o_data,32*g,32);++writes;ev("VM_write_accept",g,ad,data);if(ad<398720||ad>=398720+576||wrseen[ad-398720]||data!=0x45a00000u){ev("FAIL_write_identity",g,ad,data);exit(10);}wrseen[ad-398720]=true;}
   if(cut.fault){ev("FAIL_spine_fault");return 11;}
   if(!cut.idle)seenrun=true;
   if(phaseaccepted&&spinebusy&&cut.obs_spine_idle&&!spinedone){spinedone=true;ev("spine_idle",cut.phase_cycles,writes);}
   if(seenrun&&cut.idle&&!done){done=true;ev("phase_retire",cut.phase_cycles,writes);}
   if(done&&allquiet&&!cut.obs_ld_run&&!cut.obs_sm_run&&!any_writer&&roots==576&&writes==576)++stable;else stable=0;
   if(stable==16){ev("all_source_root_writer_drained",cfgwrites,roots,writes);break;}
  }
  std::vector<std::pair<int,uint32_t>> accepted_writes;
  if(rst)for(int port=0;port<NR;++port)if(getb(cut.o_we,port,1))accepted_writes.push_back({int(getb(cut.o_addr,VAW*port,VAW)),uint32_t(getb(cut.o_data,32*port,32))});
  cut.clk=1;cut.eval();fld.eval_all(1,rst);fld.propagate();
  for(auto [ad,data]:accepted_writes){cut.obs_probe_addr=ad;cut.eval();ev("final_destination_visible",ad,-1,cut.obs_probe_data);if(cut.obs_probe_data!=data){ev("FAIL_final_destination",ad,-1,cut.obs_probe_data);return 12;}}
  cut.clk=0;cut.eval();fld.eval_all(0,rst);
  topctx.timeInc(1);ctx.timeInc(1);
 }
 fflush(journal);fclose(journal);
 struct rusage ru;getrusage(RUSAGE_SELF,&ru);
 bool ok=done&&stable==16&&cfgwrites==NP*25&&roots==576&&writes==576&&ce==23040&&captures==ce&&consumers==ce;
 printf("%s edges=%ld phase_cycles=%u cfgwrites=%ld CE=%ld captures=%ld consumers=%ld roots=%ld writes=%ld maxrss_KiB=%ld\n",ok?"FUNCTIONAL_PASS":"FUNCTIONAL_FAIL",edge,cut.phase_cycles,cfgwrites,ce,captures,consumers,roots,writes,ru.ru_maxrss);
 return ok?0:1;
}
