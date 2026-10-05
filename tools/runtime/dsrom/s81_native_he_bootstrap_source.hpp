#pragma once
#include <s81_minimum_prefix_providers.hpp>
#include "s81_native_he_bootstrap_abi.h"
#include <memory>
#include <algorithm>
#include <deque>
#include <cstring>

// All callbacks access the SAME native target/provider as the embedding sink.
// No software arithmetic callback, expected H, XN, or SSX constructor exists.
struct DsromS81NativeHeBootstrapSourcePorts {
 std::function<bool(uint64_t)> H_visible;
 std::function<bool(const DsromS81PrefixOperation&)> inputs_ready;
 std::function<void()> bootstrap_accepted;
 std::function<std::optional<std::array<uint32_t,256>>(uint64_t,uint32_t)> H_read;
 // Actual fixed-latency HE bank/VM read participants populate only he_w_data
 // and he_x_q. Missing enrollment/response must throw, never return defaults.
 std::function<void(uint64_t,const S81NativeHeBootstrapOutput&,S81NativeHeBootstrapInput&)> memory_prepare;
 std::function<bool(uint64_t,uint32_t,uint32_t)> scalar_offer,scalar_visible;
 std::function<bool(uint64_t,uint32_t,uint32_t,const std::array<uint32_t,32>&)> HE_offer,HE_visible;
 std::function<bool()> fault;
};

class DsromS81NativeHeBootstrapSource {
 void* leaf=nullptr;
 uint64_t identity;
 DsromS81NativeHeBootstrapSourcePorts ports;
 S81NativeHeBootstrapInput input{};
 S81NativeHeBootstrapOutput output{};
 unsigned vector=0,scalar=0;
 bool reset_seen=false,armed=false,started=false,ssx_seen=false,scalar_offered=false;
 bool stopped=false;
 uint32_t ssx=0;
 struct Pending {uint32_t address,mask;std::array<uint32_t,32> data;bool offered=false;};
 std::deque<Pending> he_pending;
 static void require(bool ok,const char* reason){if(!ok)throw std::runtime_error(reason);}
 static uint32_t field(const DsromS81PrefixOperation& op,unsigned offset,unsigned width) {
  uint32_t result=0;
  for(unsigned b=0;b<width;b++)result|=((op.instruction[(offset+b)/32]>>((offset+b)%32))&1u)<<b;
  return result;
 }
 void prepare(const DsromS81PairResult&) {
  try {
   require(!fault(),"native HE/bootstrap fault: accepted source and VM debt retained");
   input.ssx_valid=0;input.ssx_last=0;
   if(armed&&reset_seen&&!started&&ports.H_visible(identity))started=true;
   if(output.ssx_we) {
    require(started&&vector==80&&!ssx_seen&&output.ssx_addr==40960,
            "SSX output lacks full native H reduction ownership");
    ssx_seen=true;ssx=output.ssx_data;
   }
   if(started&&vector<80) {
    auto data=ports.H_read(identity,vector*256);
    if(data){std::copy(data->begin(),data->end(),input.ssx_x);input.ssx_valid=1;input.ssx_last=vector==79;}
   }
   if(ssx_seen&&scalar<5) {
    uint32_t address=scalar?41151+scalar:40960,bits=scalar?(scalar==1?0x3f800000u:0u):ssx;
    if(!scalar_offered)scalar_offered=ports.scalar_offer(identity,address,bits);
    if(scalar_offered&&ports.scalar_visible(identity,address,bits)){++scalar;scalar_offered=false;}
   }
   if(output.he_o_we) {
    require(he_pending.size()<32,"HE reserved 32-word publication queue overflow");
    Pending p{output.he_o_addr,output.he_o_mask,{}};
    std::copy(std::begin(output.he_o_data),std::end(output.he_o_data),p.data.begin());
    he_pending.push_back(p);
   }
   if(!he_pending.empty()) {
    auto& p=he_pending.front();
    if(!p.offered)p.offered=ports.HE_offer(identity,p.address,p.mask,p.data);
    if(p.offered&&ports.HE_visible(identity,p.address,p.mask,p.data))he_pending.pop_front();
   }
   auto before=input;
   ports.memory_prepare(identity,output,input);
   std::copy_n(input.he_w_data,64,before.he_w_data);std::copy_n(input.he_x_q,8,before.he_x_q);
   require(!std::memcmp(&before,&input,sizeof input),"HE memory participant changed native control or SSX input");
   // Prepare only stages ports. The sole participant evaluates once per rising/falling edge.
  }catch(...){stopped=true;throw;}
 }
public:
 DsromS81NativeHeBootstrapSource(uint64_t id,DsromS81NativeHeBootstrapSourcePorts p):identity(id),ports(std::move(p)) {
  require(id<(1ull<<47)&&ports.H_visible&&ports.H_read&&ports.inputs_ready&&ports.bootstrap_accepted&&ports.memory_prepare&&
          ports.scalar_offer&&ports.scalar_visible&&ports.HE_offer&&ports.HE_visible&&ports.fault,
          "actual native VM, fixed-latency HE banks and matched visibility required");
  leaf=s81_native_he_bootstrap_create();
 }
 ~DsromS81NativeHeBootstrapSource(){s81_native_he_bootstrap_destroy(leaf);}
 DsromS81NativeHeBootstrapSource(const DsromS81NativeHeBootstrapSource&)=delete;
 DsromS81NativeHeBootstrapSource& operator=(const DsromS81NativeHeBootstrapSource&)=delete;
 bool fault()const{return stopped||output.he_fault||output.ssx_fault||ports.fault();}
 bool cold_visible()const{return scalar==5&&!output.ssx_busy&&!fault();}
 DsromS81MinimumParticipant participant() {
  return {"native-HE-and-cold-SSX-PF",
   [this](const auto&r){prepare(r);},
   [this](bool released){
    try {
     if(!released){require(!started&&!input.he_go&&he_pending.empty(),"reset would erase native bootstrap/HE owner");reset_seen=true;}
     input.reset_n=released;
     if(released&&input.ssx_valid){if(vector==0)ports.bootstrap_accepted();++vector;}
     s81_native_he_bootstrap_rise(leaf,&input,&output);
    }catch(...){stopped=true;throw;}
   },
   [this](bool released){input.reset_n=released;s81_native_he_bootstrap_fall(leaf,&input,&output);},
   [this](){return fault();}};
 }
 void arm(){require(reset_seen&&!armed&&!started&&!fault(),"explicit bootstrap arm requires shared reset and unique admission");armed=true;}
 DsromS81PrefixNativeEngine engine() {
  DsromS81PrefixNativeEngine e;
  e.participant={"native-HE-control-only",[](const auto&){},[](bool){},[](bool){},[this](){return fault();}};
  e.inputs_ready=ports.inputs_ready;
  e.ready=[this](){return cold_visible()&&he_pending.empty()&&output.he_ready;};
  e.idle=[this](){return he_pending.empty()&&output.he_idle;};
  e.drive=[this](const DsromS81PrefixOperation& op,bool go){
   input.he_go=go;
   if(!go)return;
   require(op.unit==5&&cold_visible()&&he_pending.empty()&&ports.inputs_ready(op),"HE GO lacks native operand/cold publication");
   // Exact full2048 ISA offsets generated by hdc_isa_v41.layout_for.
   input.he_nout=field(op,1563,21); input.he_k=field(op,1584,21);
   input.he_wbase=field(op,1605,30); input.he_xbase=field(op,1635,30);
   input.he_obase=field(op,1665,30); input.he_m=field(op,1723,3);
   input.he_xps=field(op,1726,30); input.he_ops=field(op,1756,30);
   require(input.he_k&&input.he_k<=2560&&input.he_nout&&input.he_nout<=32&&input.he_m<=1,
           "HE literal exceeds enrolled fullshape engine");
  };
  return e;
 }
};
