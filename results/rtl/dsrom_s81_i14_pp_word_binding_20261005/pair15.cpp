#include "Vcut.h"
#include "Vcut___024root.h"
#include "Vpq.h"
#include "Vpq___024root.h"
#include "Vpq_ot_v41_bterm2_w10__T11.h"
#include "svdpi.h"
#include <fstream>
#include <cstdio>
#include <stdexcept>
#include <map>
#include <array>
#include <vector>
#include <cstring>
std::map<const void*,unsigned> scopes;
std::map<std::pair<unsigned,unsigned>,std::array<uint32_t,9>> words;
std::vector<uint64_t> cfg;unsigned cycle=0;
extern "C" void v41rt_rom_register(const char*s){scopes[svGetScope()]=s&&*s&&s[strlen(s)-1]=='b';}
extern "C" void v41rt_cfg_register(){}
extern "C" long long v41rt_cfg_read(int a){return cfg.at(a);}
extern "C" void v41rt_rom_read(int a,svBitVecVal*q){unsigned bank=scopes.at(svGetScope());auto w=words.at({bank,unsigned(a)});for(unsigned j=0;j<9;j++)q[j]=w[j];printf("ROM %u %u %u %08x %08x\n",cycle,bank,a,w[0],w[8]);}
int main(int argc,char**argv){
 VerilatedContext ctx;ctx.commandArgs(argc,argv);Vcut c(&ctx);Vpq p(&ctx);
 std::ifstream w(argv[2]);unsigned bank,a;while(w>>bank>>a){std::array<uint32_t,9> v;for(auto&x:v)w>>x;words[{bank,a}]=v;}
 std::ifstream conf(argv[3]);std::string line;while(conf>>line)cfg.push_back(std::stoull(line,nullptr,16));
 auto tick=[&](){
 c.clk=0;c.eval();p.clk=0;p.eval();
 p.cfg_go=c.fb_cfg_go;p.cfg_ph=c.fb_cfg_ph;p.cfg_np=c.fb_cfg_np;p.go=c.fb_go;p.go_bf=c.fb_go_bf;
 p.xs_v=c.fb_xs_v;p.xs_p=c.fb_xs_p;p.xs_b=c.fb_xs_b;p.xs_sv=c.fb_xs_sv;p.xs_e0=c.fb_xs_e0;p.xs_e1=c.fb_xs_e1;p.xs_pos=c.fb_xs_pos;
 p.xb_v=c.fb_xb_v;p.xb_b=c.fb_xb_b;p.xb_sv=c.fb_xb_sv;p.xb_u=c.fb_xb_u;p.xb_pos=c.fb_xb_pos;
 for(unsigned j=0;j<8;j++){p.xs_q0[j]=c.fb_xs_q0[j];p.xs_q1[j]=c.fb_xs_q1[j];}
 for(unsigned j=0;j<32;j++)p.xb_d[j]=c.fb_xb_d[j];p.rst_n=c.rst_n;
 auto* pr=p.rootp;
 auto* term=pr->__PVT__ot_v41_pair_w17w10__DOT__u_e__DOT__g_mac__BRA__0__KET____DOT__g_l2__DOT__u_l0;
 if(term->__PVT__p0_v){printf("TERM %u %x %u %u X",cycle,unsigned(term->__PVT__u_tag__DOT__g_line__DOT__line[0])&0x1ffff,unsigned(term->__PVT__p0_xe),unsigned(term->__PVT__p0_we));
  for(unsigned j=0;j<8;j++)printf(" %08x",term->__PVT__p0_xq[j]);printf(" W");for(unsigned j=0;j<8;j++)printf(" %08x",term->__PVT__p0_wq[j]);puts("");}
 if(term->__PVT__p8_v)printf("DOT %u %x %08x\n",cycle,unsigned(term->__PVT__u_tag__DOT__g_line__DOT__line[5]>>10)&0x1ffff,unsigned(term->__PVT__p8_y));
 if(pr->ot_v41_pair_w17w10__DOT__u_e__DOT__g_mac__BRA__0__KET____DOT__pr_vp & 128){
  auto& bits=pr->ot_v41_pair_w17w10__DOT__u_e__DOT__g_mac__BRA__0__KET____DOT__u_pt__DOT__g_line__DOT__line;
  printf("CHUNK8 %u %03x %08x\n",cycle,unsigned(bits[2]>>6)&1023,pr->ot_v41_pair_w17w10__DOT__u_e__DOT__g_mac__BRA__0__KET____DOT__q_val);
 }
 for(unsigned j=0;j<2;j++)if(p.pv&(1u<<j))printf("PARTIAL %u %u %u %u %u %08x\n",cycle,j,(p.prow>>(16*j))&65535,(p.pseg>>(5*j))&31,(p.pnseg>>(5*j))&31,uint32_t(p.pval>>(32*j)));
 p.clk=1;p.eval();c.clk=1;c.eval();p.clk=0;p.eval();c.clk=0;c.eval();++cycle;
 };
 c.rst_n=0;c.go=0;for(unsigned j=0;j<4;j++){c.fr_v[j]=0;c.fr_e[j]=0;}c.fr_fault=0;
 for(unsigned i=0;i<4;i++)tick();
 std::ifstream f(argv[1],std::ios::binary);unsigned qr[1280];f.read((char*)qr,sizeof qr);if(f.gcount()!=sizeof qr)throw std::runtime_error("QR extent");
 for(unsigned k=0;k<1280;k++)c.rootp->dsrom_source_cut__DOT__dut__DOT__vm[52928+k]=qr[k];
 c.rst_n=1;c.i_ph=20;c.i_np=0;c.i_xbase=52928;c.i_xps=0;c.i_obase=32768;c.i_ops=4608;
 tick();c.go=1;tick();c.go=0;
 for(unsigned i=0;i<1000;i++)tick();
 printf("END have=%u cutfault=%u pairfault=%u\n",unsigned(c.obs_have),unsigned(c.fault),unsigned(p.fault));
}
