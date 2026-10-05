#pragma once
#include "s81_embedding_abi.h"
#include <array>
#include <functional>
#include <stdexcept>

// Cicero ABI: the raw provider services addresses emitted by the native reader.
// Native VM writes use the existing C8 identity/quiet checked write function.
// This adapter grants neither input visibility nor context-restored authority.
// Caller must clock its actual runtime and retain all source/target leases.
class DsromS81EmbeddingParent {
public:
 using RawRead=std::function<std::array<uint32_t,8>(uint64_t,uint32_t,uint32_t)>;
private:
 void* reader;
 S81EmbeddingInput in{};
 S81EmbeddingOutput out{};
 RawRead raw;
 unsigned response_wait=0, written=0;
 bool pending=false, started=false, complete=false;
 uint32_t held_address=0;
 std::array<uint32_t,16> held_data{};
public:
 DsromS81EmbeddingParent(uint32_t token,uint64_t identity,uint32_t vm_base,RawRead read)
 :reader(nullptr),raw(std::move(read)) {
   if(!raw || token>=129280 || identity>=(1ull<<47) || vm_base>503808)
     throw std::runtime_error("cold embedding source/context bounds");
   // The small connected wrapper covers the first cold H region only. It is
   // not a general VM19 implementation; retain this explicit admission bound.
   if(vm_base>32768-20480)throw std::runtime_error("small embedding ABI VM extent");
   reader=s81_embedding_create();
   in.token=token;in.identity=identity;in.vm_base=vm_base;in.req_ready=1;
   s81_embedding_edge(reader,&in,&out);in.reset_n=1;
 }
 ~DsromS81EmbeddingParent(){s81_embedding_destroy(reader);}
 DsromS81EmbeddingParent(const DsromS81EmbeddingParent&)=delete;
 DsromS81EmbeddingParent& operator=(const DsromS81EmbeddingParent&)=delete;
 template<class NativeDie> bool edge(NativeDie& target) {
   if(complete)return true;
   uint64_t identity;uint32_t token;uint16_t entry;
   if(!target.c8_context(identity,token,entry) || identity!=in.identity || token!=in.token)
     throw std::runtime_error("cold embedding lacks actual matching target context");
   if(target.fault())throw std::runtime_error("cold embedding native target fault");
   in.start=!started;in.commit_ready=0;in.rsp_valid=pending && response_wait==0;
   s81_embedding_eval(reader,&in,&out);
   if(out.fault)throw std::runtime_error("native embedding reader fault");
   bool received=in.rsp_valid && out.rsp_ready;
   if(out.req_valid && in.req_ready) {
     if(pending || out.req_identity!=in.identity)throw std::runtime_error("embedding request identity/outstanding");
     auto words=raw(out.req_identity,out.req_macro,out.req_row);
     for(unsigned n=0;n<8;n++)in.rsp_data[n]=words[n];
     in.rsp_macro=out.req_macro;in.rsp_row=out.req_row;in.rsp_identity=out.req_identity;
     pending=true;response_wait=8;
   }
   if(out.vm_valid) {
     if(out.vm_identity!=in.identity)throw std::runtime_error("embedding VM identity");
     if(written==0) {
       held_address=out.vm_address;
       for(unsigned n=0;n<16;n++)held_data[n]=out.vm_data[n];
     } else {
       if(held_address!=out.vm_address)throw std::runtime_error("stalled embedding address changed");
       for(unsigned n=0;n<16;n++)if(held_data[n]!=out.vm_data[n])throw std::runtime_error("stalled embedding data changed");
     }
     while(written<16) {
       if(!target.c8_workspace_write(in.identity,held_address+written,held_data[written]))break;
       ++written;
     }
     in.commit_ready=written==16;
   }
   s81_embedding_edge(reader,&in,&out);started=true;
   if(in.commit_ready)written=0;
   if(received)pending=false;
   else if(pending && response_wait) --response_wait;
   if(out.fault)throw std::runtime_error("native embedding reader fault");
   if(out.done) {
     if(pending || written || out.committed_words!=20480)throw std::runtime_error("cold embedding commit debt");
     complete=true;
   }
   return complete;
 }
 bool committed() const {return complete;}
 // Caller still owes native SSX generation, PF source constant setup, required
 // +DIR files and actual input/remote/all-copy visibility before restored.
};
