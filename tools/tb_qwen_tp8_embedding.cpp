#include "Vot_qwen_tp8_embedding_core.h"
#include "Vot_qwen_tp8_embedding_core___024root.h"
#include "verilated.h"
#include <array>
#include <vector>
#include <fstream>
#include <string>
#include <stdexcept>
#include <iostream>
#include <filesystem>
#include <iomanip>
template<size_t N> using Word=std::array<uint32_t,N>;
template<size_t N> std::vector<Word<N>> hex(const std::string& path){
 std::ifstream f(path);if(!f)throw std::runtime_error("missing input "+path);std::vector<Word<N>> v;std::string s;
 while(f>>s){Word<N> w{};if(s.size()>N*8)throw std::runtime_error("input width");for(size_t i=0;i<N&&i*8<s.size();++i){size_t e=s.size()-i*8,b=e>8?e-8:0;w[i]=std::stoul(s.substr(b,e-b),nullptr,16);}v.push_back(w);}return v;
}
template<class T> uint32_t bits(const T& p,unsigned o,unsigned n){uint64_t a=p[o/32];if(o%32+n>32)a|=uint64_t(p[o/32+1])<<32;return(a>>(o%32))&((1u<<n)-1);}
template<class T,size_t N> void drive(T& p,const Word<N>& w){for(size_t i=0;i<N;++i)p[i]=w[i];}
int main(int argc,char** argv){try{
 if(argc<5)throw std::runtime_error("program vectors output mutant[none|code|alias|word]");Verilated::commandArgs(argc,argv);
 const std::string root=argv[2],output=argv[3],mutant=argv[4];auto program=hex<32>(argv[1]);if(program.size()!=2)throw std::runtime_error("embedding program2 words required");
 Vot_qwen_tp8_embedding_core m;std::vector<uint32_t> vm(56816,0);Word<32> pq{};Word<16> eq{};uint16_t sq=0;
 Word<64> aq{},bq{},cq{};Word<128> crq{};uint64_t edges=0,total_errors=0;
 m.native_contract_ready=0;m.native_ready=0;m.native_idle=1;m.native_fault=0;m.native_progress=0;
 m.su_descriptor_reserved=1;m.kv_write_drained=1;m.kv_ok=1;m.w_ok=1;m.emb_ok=1;m.me_mem_ok=1;m.start=0;m.pos=0;m.rst_n=0;
 std::vector<Word<16>> codes;uint16_t scale=0;unsigned token=0,issue_count=0,end_count=0,writes=0,reductions=0,requests=0;
 Word<32> observed_next{};bool observed_valid=false;
 auto edge=[&](){m.clk=0;drive(m.prog_q,pq);drive(m.embed_code_q,eq);m.embed_scale_q=sq;drive(m.va_q,aq);drive(m.vb_q,bq);drive(m.vc_q,cq);drive(m.crom_q,crq);m.eval();
  Word<32> np=pq;Word<16> ne=eq;uint16_t ns=sq;auto na=aq,nb=bq,nc=cq;
  if(m.prog_re){np=m.prog_addr<program.size()?program[m.prog_addr]:Word<32>{};if(mutant=="word"&&m.prog_addr==0)np[31]^=0x80000000u;}
  if(m.embed_scale_re){if(m.embed_scale_addr!=token)throw std::runtime_error("truncated18-bit scale address");ns=scale;}
  if(m.embed_code_re){unsigned expected_base=token*64;if(m.embed_code_addr<expected_base||m.embed_code_addr>=expected_base+64)throw std::runtime_error("truncated18-bit code address");unsigned index=m.embed_code_addr-expected_base;ne=codes[index];if(mutant=="code"&&index==0)ne[0]^=1;++requests;}
  std::vector<std::pair<unsigned,uint32_t>> commit;
  for(unsigned lane=0;lane<64;++lane){uint64_t mask=uint64_t(1)<<lane;
   if(m.va_re&mask){unsigned a=bits(m.va_addr,lane*24,24);if(a>=vm.size())throw std::runtime_error("VM A bounds");na[lane]=vm[a];}
   if(m.vb_re&mask){unsigned a=bits(m.vb_addr,lane*24,24);if(a>=vm.size())throw std::runtime_error("VM B bounds");nb[lane]=vm[a];}
   if(m.vc_re&mask){unsigned a=bits(m.vc_addr,lane*24,24);if(a>=vm.size())throw std::runtime_error("VM C bounds");nc[lane]=vm[a];}
   if(m.vw_su_we&mask){unsigned a=bits(m.vw_su_addr,lane*24,24);if(a<4096||a>=8192)throw std::runtime_error("unexpected embedding destination");commit.emplace_back(a,m.vw_su_data[lane]);++writes;}}
  if(m.vw_rd_we){if(m.vw_rd_addr!=14240)throw std::runtime_error("unexpected reduction destination");commit.emplace_back(m.vw_rd_addr,m.vw_rd_data);++reductions;}
  if(m.instruction_issue){if(m.instruction_pc!=0||m.instruction_unit!=2)throw std::runtime_error("nonembedding accepted opcode");if(!observed_valid||observed_next!=program[0])throw std::runtime_error("actual accepted1024-bit instruction differs from pinned source");++issue_count;}
  if(m.end_retired){if(m.end_pc!=1)throw std::runtime_error("END source mismatch");if(!observed_valid||observed_next!=program[1])throw std::runtime_error("actual acceptedEND bits differ from source");++end_count;}
  bool loaded=m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__load;
  Word<32> loaded_word{};if(loaded){auto& actual=m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__fq[m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__fq_rd];for(unsigned i=0;i<32;++i)loaded_word[i]=actual[i];}
  if(m.vw_me_we||m.vw_mx_we||m.kv_we)throw std::runtime_error("unprovided embedding operator");
  if(m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__su_fault||m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__rom_fault||m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__dispatch_fault)
   std::cerr<<"PRE_FAULT edge="<<edges<<" SU="<<unsigned(m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__su_fault)<<" ROM="<<unsigned(m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__rom_fault)<<" DISPATCH="<<unsigned(m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__dispatch_fault)<<"\n";
  m.clk=1;m.eval();for(auto [a,v]:commit)vm[a]=v;pq=np;eq=ne;sq=ns;aq=na;bq=nb;cq=nc;if(loaded){observed_next=loaded_word;observed_valid=true;}++edges;};
 for(unsigned i=0;i<8;++i)edge();m.rst_n=1;for(unsigned i=0;i<8;++i)edge();
 std::filesystem::create_directories(output);
 for(unsigned next:{0u,65536u,151935u}){
  token=next;std::string dir=root+"/token"+std::to_string(token);codes=hex<16>(dir+"/codes.hex");scale=hex<1>(dir+"/scale.hex")[0][0];
  if(mutant=="alias"&&token>=65536){codes=hex<16>(root+"/token0/codes.hex");scale=hex<1>(root+"/token0/scale.hex")[0][0];}
  auto expected=hex<1>(dir+"/expected_X.hex");auto expected_ssx=hex<1>(dir+"/expected_SSX.hex");
  issue_count=end_count=writes=reductions=requests=0;observed_valid=false;m.token=token;m.start=1;uint64_t begin=edges;edge();m.start=0;
  unsigned watchdog=0;while(!m.done&&watchdog++<10000){edge();if(m.fault){std::cerr<<"FAULT_TRACE token="<<token<<" edge="<<edges<<" writes="<<writes<<" req="<<requests<<" su_fault="<<unsigned(m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__su_fault)<<" scale="<<std::hex<<m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__embed_scale_hold<<" embed_sel="<<m.rootp->ot_hdc_core_vector_weight_native_candidate__DOT__embed_sel<<std::dec<<"\n";throw std::runtime_error("actualRTL fault");}}
  if(!m.done||writes!=4096||reductions!=1||issue_count!=1||end_count!=1||requests!=64)throw std::runtime_error("incomplete accepted embedding or commit counts");
  uint64_t errors=0;for(unsigned a=0;a<4096;++a)errors+=vm[4096+a]!=expected[a][0];errors+=vm[14240]!=expected_ssx[0][0];total_errors+=errors;
  std::ofstream x(output+"/token"+std::to_string(token)+"_actual_X.hex");for(unsigned a=4096;a<8192;++a)x<<std::hex<<std::setw(8)<<std::setfill('0')<<vm[a]<<"\n";
  std::ofstream full(output+"/token"+std::to_string(token)+"_actual_VM.hex");for(uint32_t v:vm)full<<std::hex<<std::setw(8)<<std::setfill('0')<<v<<"\n";
  std::cout<<"ACTUAL_EMBED token="<<token<<" cycles="<<edges-begin<<" Xwrites="<<writes<<" REDwrites="<<reductions<<" errors="<<errors<<"\n";
  for(unsigned i=0;i<100;++i)edge();
 }
 std::cout<<"TOTAL_ERRORS "<<total_errors<<"\n";return total_errors?1:0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<"\n";return 2;}}
