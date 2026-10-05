#include "VDsromAttention.h"
#include "s81_minimum_l20_bank.hpp"
#include "s81_minimum_su256_ports.hpp"
#include "s81_minimum_attention_cut.hpp"
#include "s81_sim_only_attention_endpoint.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
#include <deque>
#include <map>
#include "literals.hpp"
#include "adapter_config.hpp"

constexpr uint64_t ID=2147483648ull;
void require(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
template<class B> unsigned bits(const B& b,unsigned off,unsigned n){
 unsigned v=0;for(unsigned j=0;j<n;j++){
  if constexpr(std::is_integral<B>::value)v|=((uint64_t(b)>>(off+j))&1u)<<j;
  else v|=((b[(off+j)/32]>>((off+j)%32))&1u)<<j;
 }return v;
}
std::vector<uint32_t> load(const std::string& path,unsigned n){
 std::ifstream f(path,std::ios::binary);std::vector<uint32_t> v(n);
 f.read(reinterpret_cast<char*>(v.data()),n*4);require(bool(f)&&f.peek()==EOF,"source extent");return v;
}
template<class B> void write(std::ofstream& f,const B& b,unsigned n){
 for(unsigned i=0;i<n;i++){uint32_t v=b[i];unsigned char x[4]={uint8_t(v),uint8_t(v>>8),uint8_t(v>>16),uint8_t(v>>24)};
  f.write(reinterpret_cast<char*>(x),4);}require(bool(f),"capture write");
}
int main(int argc,char** argv){try{
 require(argc==3,"capture INPUT OUTPUT");std::string input=argv[1],output=argv[2];
 require(std::filesystem::create_directory(output),"fresh output required");
 auto packed=load(input+"/source_kv_beats.u32",160*530);
 auto query=load(input+"/I55.Q_rank0.u32",8192);
 auto h=load(input+"/H.u32",20480);
 VerilatedContext ctx;long cycle=0;DsromS81MinimumRuntime runtime{};
 runtime.stage=37;runtime.rank=0;runtime.pair=11;runtime.bf16=true;runtime.context=&ctx;runtime.cycle=[&](){return cycle;};
 auto vm=std::make_shared<Vnative_vm>(&ctx,"minimum_rank0_VM");
 DsromS81MinimumL20Bank bank(runtime,ID,vm,dsrom_s81_bind_minimum_source_tags(runtime,ID));
 auto bankp=bank.bank_participant();auto& pub=bank.publication();auto& io=bank.io();
 pub.enroll_literal(2525,{{55744,8192}});pub.enroll_literal(2526,{{63936,10240}});
 pub.enroll_literal(2532,{{63936,10240},{74176,16}});
 pub.enroll_literal(2533,{{63936,10240},{74208,16}});pub.enroll_literal(2534,{{74272,8192}});
 DsromS81NativeSuPorts hooks;hooks.actual_dynamic=[](unsigned d)->std::optional<uint32_t>{
  if(d==0)return 0;if(d==34)return 640;throw std::runtime_error("unbound SU dynamic");};
 auto su=dsrom_s81_bind_minimum_su256(runtime,ID,pub,io,bank.tags(),hooks);
 VDsromAttention a(&ctx,"minimum_QK_PV_adapter");DsromS81SimOnlyAttentionEndpoint endpoint(&ctx,"frozen_integer_endpoint");
 auto cut=std::make_shared<DsromS81MinimumAttentionCut<VDsromAttention,DsromS81SimOnlyAttentionEndpoint>>(runtime,a,endpoint);
 auto ep=cut->participant();a.clk=0;a.rst_n=0;a.go=0;a.packed_kv_v=0;a.packed_kv_fault=0;
 for(unsigned j=0;j<4;j++)a.x_q[j]=0;
 bool att_active=false,att_admitted=false;unsigned att_kind=0,nkv=0,np=0,nq=0,nscore=0,npv=0;
 std::map<unsigned,uint32_t> operand;std::deque<S81EmbeddingOutput> writes;bool offered=false;
 std::ofstream events(output+"/events.tsv");events<<"cycle\tstage\tevent\tordinal\n";
 std::ofstream pfile,kfile,qfile,scorefile,pvfile;
 auto tick=[&](bool released){
  if(!writes.empty()){
   if(!offered)offered=io.offer(writes.front(),1);
   if(offered&&io.visible(writes.front(),1)){writes.pop_front();offered=false;}
  }
  bankp.prepare({});su.participant.prepare({});
  a.rst_n=released;a.go=att_active&&!att_admitted&&a.ready;
  a.packed_kv_v=att_active&&nkv<160;a.packed_kv_m=15;
  if(att_active&&nkv<160)for(unsigned j=0;j<530;j++)a.packed_kv_w[j]=packed[nkv*530+j];
  a.clk=0;cut->join();ep.prepare({});
  const bool acc=released&&a.go&&a.ready;
  std::array<uint32_t,4> next{};for(unsigned j=0;j<4;j++){
   next[j]=a.x_q[j];if(released&&((a.x_re>>j)&1)){
    unsigned addr=bits(a.x_addr,j*30,30);auto it=operand.find(addr);require(it!=operand.end(),"unstaged adapter read");next[j]=it->second;
   }
  }
  auto event=[&](const char* name,unsigned ordinal){events<<cycle<<'\t'<<(att_kind?"PV":"QK")<<'\t'<<name<<'\t'<<ordinal<<'\n';};
  if(released&&att_active){
   if(endpoint.job_v&&endpoint.job_ready)event("JOB",0);
   if(endpoint.p_v&&endpoint.p_ready){write(pfile,endpoint.p_w,16);event("P",np++);}
   if(endpoint.kv_v&&endpoint.kv_ready){write(kfile,endpoint.kv_w,530);event("KV",nkv++);}
   if(endpoint.q_v&&endpoint.q_ready){write(qfile,endpoint.q_w,256);event("Q",nq++);}
   if(endpoint.sc_v){write(scorefile,endpoint.sc_y,64);event("SCORE",nscore++);}
   if(endpoint.pv_v){write(pvfile,endpoint.pv_y,1024);event("PV",npv++);}
  }
  // All prepares and accepted OLD bus captures precede every rising callback.
  bankp.rising(released);su.participant.rising(released);a.clk=1;a.eval();ep.rising(released);
  for(unsigned j=0;j<4;j++)a.x_q[j]=next[j];
  if(acc)att_admitted=true;
  if(released&&att_active)for(unsigned port=0;port<4;port++)if((a.o_we>>port)&1){
   unsigned base=bits(a.o_addr,port*30,30)*16;
   for(unsigned lane=0;lane<16;lane++)if((a.o_mask>>(port*16+lane))&1){
    S81EmbeddingOutput o{};o.vm_valid=1;o.vm_identity=ID;o.vm_address=base+lane;o.vm_data[0]=a.o_data[port*16+lane];
    dsrom_s81_capture_minimum_prefix_scalar(runtime,pub,ops[att_kind?3:0].index,o,0,true);writes.push_back(o);
   }
  }
  bankp.falling(released);su.participant.falling(released);a.clk=0;a.eval();ep.falling(released);++cycle;
  require(!bankp.fault()&&!su.participant.fault()&&!a.fault&&!ep.fault(),"native participant fault");
 };
 for(unsigned i=0;i<3;i++)tick(false);runtime.identity=ID;
 // Actual seeded H word0 services native SU's unused default VM operands.
 S81EmbeddingOutput ho{};ho.vm_valid=1;ho.vm_identity=ID;ho.vm_address=0;std::copy_n(h.begin(),16,ho.vm_data);
 while(!bank.embedding_sink().offer(ho))tick(true);
 while(!bank.embedding_sink().visible(ho))tick(true);
 pub.begin(ID,2525);
 for(unsigned off=0;off<8192;off+=16){
  S81EmbeddingOutput o{};o.vm_valid=1;o.vm_identity=ID;o.vm_address=55744+off;
  for(unsigned j=0;j<16;j++){o.vm_data[j]=query[off+j];dsrom_s81_capture_minimum_prefix_scalar(runtime,pub,2525,o,j,true);}
  while(!io.offer(o,16))tick(true);while(!io.visible(o,16))tick(true);
 }
 require(pub.complete(ID,2525),"query lacks actual matched publication");
 auto capture_span=[&](const char* name,unsigned base,unsigned count){
  require(io.span_lease(ID,base,count),"boundary missing source lease");
  std::ofstream f(output+"/"+name+".u32",std::ios::binary);std::vector<uint32_t> v;
  for(unsigned i=0;i<count;i++){std::optional<uint32_t> x;while(!(x=io.read_word(ID,base+i)))tick(true);v.push_back(*x);}write(f,v,count);
  events<<cycle<<"\tBOUNDARY\t"<<name<<"\t"<<count<<'\n';std::cerr<<"BOUNDARY "<<name<<" cycle="<<cycle<<'\n';
 };
 auto attention=[&](bool pv){
  att_kind=pv;operand.clear();unsigned base=pv?63936:55744,count=pv?10240:8192;
  require(io.span_lease(ID,base,count),"attention source lease missing");
  for(unsigned i=0;i<count;i++){std::optional<uint32_t> x;while(!(x=io.read_word(ID,base+i)))tick(true);operand.emplace(base+i,*x);}
  configure(a,pv);att_admitted=false;nkv=np=nq=nscore=npv=0;
  std::string stage=pv?"PV":"QK";
  pfile.open(output+"/"+stage+"_accepted_p.u32",std::ios::binary);kfile.open(output+"/"+stage+"_accepted_kv.u32",std::ios::binary);
  qfile.open(output+"/"+stage+"_accepted_q.u32",std::ios::binary);scorefile.open(output+"/"+stage+"_old_score.u32",std::ios::binary);
  pvfile.open(output+"/"+stage+"_old_pv.u32",std::ios::binary);
  pub.begin(ID,ops[pv?3:0].index);att_active=true;
  do{tick(true);}while(!att_admitted||!a.idle||!writes.empty());
  require(nkv==160&&np==320&&nq==16&&nscore==160&&npv==8,"accepted attention extent");
  require(pub.complete(ID,ops[pv?3:0].index),"attention native write ACK incomplete");
  att_active=false;pfile.close();kfile.close();qfile.close();scorefile.close();pvfile.close();
 };
 attention(false);capture_span("QK",63936,10240);
 for(unsigned i=1;i<=2;i++){
  while(!su.inputs_ready(ops[i])||!su.ready())tick(true);
  pub.begin(ID,ops[i].index);su.drive(ops[i],true);tick(true);su.drive(ops[i],false);
  while(!su.idle())tick(true);require(pub.complete(ID,ops[i].index),"SU native write ACK incomplete");
  capture_span(i==1?"Sscaled":"EXP",63936,10240);
  capture_span(i==1?"MAX":"SUM",i==1?74176:74208,16);
 }
 attention(true);capture_span("PV",74272,8192);
 std::cout<<"CONNECTED_QK_I61_I62_PV cycle="<<cycle<<" real_macro_ACK=1 SIM_ONLY_endpoint=1 scope=minimum_controlled_source_rank0\n";
 return 0;
}catch(const std::exception& e){std::cerr<<"CONNECTED_ERROR "<<e.what()<<'\n';return 1;}}
