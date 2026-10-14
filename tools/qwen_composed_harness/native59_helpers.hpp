#pragma once
// Actual source-bound native59 sequencers plus one persistent collector.
// VM reads are synchronous VRL1; returned words commit only on actual vm_we.
#include "Vot_qwen_native59.h"
#include "native59.h"
#include <array>
#include <functional>
#include <fstream>
#include <memory>
#include <stdexcept>
#include <vector>
#include <dlfcn.h>
class Native59Helpers {
 using Sample=int(*)(void*,const native59_input*,native59_output*);
 using Advance=int(*)(void*);using Destroy=void(*)(void*);
 void* library=nullptr;void* collector=nullptr;Sample sample=nullptr;Advance advance=nullptr;Destroy destroy=nullptr;
 template<class T>T symbol(const char*name){auto ptr=dlsym(library,name);if(!ptr)throw std::runtime_error(std::string("missing persistent collector API ")+name);return reinterpret_cast<T>(ptr);}
 std::array<std::unique_ptr<Vot_qwen_native59>,8> helper;
 std::array<std::vector<uint64_t>,8> descriptors;
 struct Pending {bool desc=false,vm=false;uint64_t descriptor=0;std::array<uint32_t,16> word{};};
 std::array<Pending,8> pending;
 native59_input offered{};native59_output observed{};
 bool sampled=false;uint64_t edges=0;int return_bit=-1;bool mutated=false;
public:
 std::array<uint64_t,8> reads{},writes{},sent{},received{};
 Native59Helpers(VerilatedContext&ctx,const std::string&so){
  library=dlopen(so.c_str(),RTLD_NOW|RTLD_LOCAL);if(!library)throw std::runtime_error(dlerror());
  auto create=symbol<void*(*)()>("native59_create");destroy=symbol<Destroy>("native59_destroy");
  sample=symbol<Sample>("native59_sample");advance=symbol<Advance>("native59_advance");collector=create();if(!collector)throw std::runtime_error("collector create failed");
  for(unsigned r=0;r<8;r++)helper[r]=std::make_unique<Vot_qwen_native59>(&ctx,("rank"+std::to_string(r)+"_native59_helper").c_str());
 }
 ~Native59Helpers(){for(auto&h:helper)h->final();if(collector)destroy(collector);if(library)dlclose(library);}
 void mutate_first_actual_return_tag(unsigned bit){if(bit>=59)throw std::runtime_error("invalid tag mutant bit");return_bit=bit;}
 bool mutation_applied()const{return mutated;}
 void banks(const std::string&program){
  for(unsigned r=0;r<8;r++){
   if(helper[r]->coll_busy)throw std::runtime_error("helper bank transition while collective active");
   auto&d=descriptors[r];d.clear();std::ifstream f(program+"/die"+std::to_string(r)+"/segments.hex");std::string word;
   if(!f)throw std::runtime_error("missing pinned actual segment descriptors");while(f>>word)d.push_back(std::stoull(word,nullptr,16));
   if(d.empty()||d.size()>64)throw std::runtime_error("invalid actual segment descriptor count");
  }
 }
 // Calls must all be in the same low phase, before any helper/collector rise.
 template<class Ranks>void low(Ranks&r,bool reset,bool begin,uint16_t epoch,unsigned stage,unsigned token,unsigned position){
  offered={};offered.rst_n=reset;
  for(unsigned rank=0;rank<8;rank++){
   auto&h=*helper[rank];h.clk=0;h.rst_n=h.rst_nw=reset;h.start=begin;h.tag_epoch=epoch;h.tag_stage=stage;h.token=token;h.pos=position;
   h.core_done=r[rank]->core.done;h.core_fault=r[rank]->core.fault;h.core_next_token=r[rank]->core.next_token;h.core_next_val=r[rank]->core.next_val;
   if(pending[rank].desc)h.desc_q=pending[rank].descriptor;
   if(pending[rank].vm)for(unsigned j=0;j<16;j++)h.vm_rq[j]=pending[rank].word[j];
   h.eval();if(h.fault)throw std::runtime_error("actual native59 helper fault");
   if(h.c_valid){offered.valid|=1u<<rank;offered.tag[rank]=h.c_tag;for(unsigned j=0;j<16;j++)offered.data[rank][j]=h.c_data[j];}
   offered.mode|=unsigned(h.c_mode)<<rank;offered.last|=unsigned(h.c_last)<<rank;
  }
  if(sample(collector,&offered,&observed))throw std::runtime_error("persistent collector low-phase failure");
  if(observed.fault||observed.err)throw std::runtime_error("actual collector fault/poison");
  if(return_bit>=0&&!mutated&&(observed.valid&1)){observed.tag[0]^=uint64_t(1)<<return_bit;mutated=true;}
  for(unsigned rank=0;rank<8;rank++){
   auto&h=*helper[rank];h.c_ready=(observed.credit>>rank)&1;h.r_valid=(observed.valid>>rank)&1;h.r_last=(observed.last>>rank)&1;h.r_err=(observed.err>>rank)&1;h.r_rank=observed.rank[rank];h.r_tag=observed.tag[rank];for(unsigned j=0;j<16;j++)h.r_data[j]=observed.data[rank][j];h.eval();
   // Source CRED32 c_valid is registered-credit dependent, so returned credit
   // cannot alter the offered stream in this low phase.
   if(bool(h.c_valid)!=bool((offered.valid>>rank)&1))throw std::runtime_error("helper offered valid changed after collector sample");
   auto&p=pending[rank];p.desc=h.desc_re;p.vm=h.vm_re;
   if(p.desc){if(h.desc_addr>=descriptors[rank].size())throw std::runtime_error("helper actual descriptor address out of range");p.descriptor=descriptors[rank][h.desc_addr];}
   if(p.vm){unsigned base=16*unsigned(h.vm_raddr);if(base+16>r[rank]->vm.vm.size())throw std::runtime_error("actual helper VM read bounds");for(unsigned j=0;j<16;j++)p.word[j]=r[rank]->vm.vm[base+j];++reads[rank];}
   // vm_we/data are registered faces from the preceding edge, like core writes.
   if(h.vm_we){unsigned base=16*unsigned(h.vm_waddr);for(unsigned j=0;j<16;j++)r[rank]->vm.external_commit(base+j,h.vm_wdata[j],"ACTUAL_NATIVE59_HELPER");++writes[rank];}
   sent[rank]+=bool((offered.valid>>rank)&1);received[rank]+=bool((observed.valid>>rank)&1);
  }
  sampled=true;
 }
 void rise(){if(!sampled)throw std::runtime_error("helper rise without frozen low phase");if(advance(collector))throw std::runtime_error("collector rise failed");for(auto&h:helper){h->clk=1;h->eval();if(h->fault)throw std::runtime_error("actual helper return rejected");}sampled=false;++edges;}
 void fall(){for(auto&h:helper){h->clk=0;h->eval();}}
 bool ready()const{return observed.online==255&&!observed.fault;}
 bool drained()const{return observed.drained==255&&!observed.fault;}
 Vot_qwen_native59&rank(unsigned r){return *helper.at(r);}
 uint64_t cycles()const{return edges;}
};
