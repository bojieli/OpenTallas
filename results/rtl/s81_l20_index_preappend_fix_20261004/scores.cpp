#include "VDsromS81IndexScorer.h"
#include "VDsromS81IndexHbm.h"
#include "svdpi.h"
#include <fstream>
#include <iostream>
#include <array>
#include <bitset>
#include <stdexcept>
static void need(bool v,const char*s){if(!v)throw std::runtime_error(s);}
template<class T> uint32_t bits(const T&v,unsigned a,unsigned n){uint32_t x=0;for(unsigned j=0;j<n;++j)x|=((v[(a+j)/32]>>((a+j)%32))&1u)<<j;return x;}
int main(int argc,char**argv){try{
 need(argc==5,"actual subset image/query/weights plus comparison-only score file");
 std::array<uint32_t,4128> input{};
 std::ifstream query(argv[2],std::ios::binary);query.read((char*)input.data(),4096*4);need(query.gcount()==4096*4&&query.peek()==EOF,"actual I41 query extent");
 std::ifstream weights(argv[3],std::ios::binary);weights.read((char*)(input.data()+4096),32*4);need(weights.gcount()==32*4&&weights.peek()==EOF,"actual I43 weights extent");
 VerilatedContext ctx;ctx.threads(1);VDsromS81IndexHbm m(&ctx,"backend");VDsromS81IndexScorer s(&ctx,"scorer");
 s.clk=m.clk=0;s.rst_n=m.rst_n=0;s.go=0;m.w_v=0;m.w_csec=m.w_ssec=m.w_sslot=m.w_scales=0;m.w_codes={};
 s.cfg_ik_base=0x1000000;s.i_user_base_sec=0;s.i_nout=64;s.i_k=128;s.i_wbase=0x1000000;
 s.i_xbase=98720;s.i_obase=0;s.i_wts=102848;s.i_xks=1;s.i_xjs=128;s.i_xcs=1024;s.i_hg=2;
 s.i_round=s.i_mmode=s.i_oen=s.i_fuse=1;s.x_q={};
 uint64_t cycles=0;std::array<uint32_t,64> actual{};std::bitset<64> seen;
 auto join=[&](){m.r_v=s.h_req_v;m.r_addr=s.h_req_addr;m.r_len=s.h_req_len;m.r_tag=s.h_req_tag;m.r_rsp_rdy=s.h_rsp_rdy;
  m.eval();s.h_req_rdy=m.r_rdy;s.h_rsp_v=m.r_rsp_v;s.h_rsp_tag=m.r_rsp_tag;s.h_rsp_beat=m.r_rsp_beat;s.h_rsp_data=m.r_rsp_data;s.eval();};
 auto low=[&](){s.clk=m.clk=0;s.eval();m.eval();join();join();};
 auto tick=[&](){low();std::array<uint32_t,8> q{};
  for(unsigned p=0;p<8;++p){q[p]=s.x_q[p];if(s.rst_n&&((s.x_re>>p)&1u)){
   auto a=bits(s.x_addr,p*30,30);
   if(a>=98720&&a<98720+4096)q[p]=input[a-98720];
   else if(a>=102848&&a<102848+32)q[p]=input[4096+a-102848];
   else throw std::runtime_error("native query read outside same actual I44 spans");}}
  s.clk=m.clk=1;s.eval();m.eval();for(unsigned p=0;p<8;++p)s.x_q[p]=q[p];++cycles;ctx.timeInc(1);
  need(!s.fault&&!m.fault,"native scorer/backend fault");
  if(s.rst_n)for(unsigned p=0;p<8;++p)if((s.o_we>>p)&1u){auto word=bits(s.o_addr,p*30,30);
   for(unsigned j=0;j<16;++j)if(bits(s.o_mask,p*16+j,1)){auto a=word*16+j;need(a<64&&!seen[a],"native output alias/duplicate");seen[a]=1;actual[a]=s.o_data[p*16+j];}}
  low();};
 tick();tick();auto scope=svGetScopeFromName("backend.DsromS81IndexHbm");need(scope,"scope");svSetScope(scope);
 VDsromS81IndexHbm::s81_index_preload_ring(argv[1]);m.eval();need(m.history_ready,"history not initialized");
 s.rst_n=m.rst_n=1;tick();need(s.ready,"native scorer readiness");s.go=1;tick();s.go=0;
 while(!(seen.all()&&s.idle&&!m.busy))tick();
 // Reference is loaded ONLY AFTER all native outputs exist; it never feeds ports.
 std::ifstream expected(argv[4]);need(bool(expected),"comparison-only cached score file");
 unsigned j,original,count=0,errors=0;uint32_t want;
 while(expected>>j>>original>>want){need(j<64,"comparison index");++count;if(actual[j]!=want){++errors;
  std::cout<<"MISMATCH original_local="<<original<<" actual="<<actual[j]<<" expected="<<want<<'\n';}}
 need(count==64,"comparison coverage");
 std::cout<<(errors?"FAIL":"PASS")<<"_NATIVE_BOUNDARY_SCORE_SUBSET cycles="<<cycles<<" words="<<count<<" errors="<<errors
  <<" affected=48 controls=16 original_I44_query_weights_rounding_tree=1 reduced_key_count_only=64 fullscan_not_rerun=1\n";
 return errors?1:0;
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
