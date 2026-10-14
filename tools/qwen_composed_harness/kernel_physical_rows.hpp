#pragma once
// Actual compiled-controller/DRAM transport. Expected/golden rows are absent.
#include "row_backend.hpp"
#include <array>
#include <deque>
#include <map>
#include <stdexcept>
#include <type_traits>
namespace qwen_native_services {
template<class V>unsigned get_bits(const V&v,unsigned off,unsigned n){
 if constexpr(std::is_integral_v<V>)return (uint64_t(v)>>off)&(n==32?0xffffffffULL:((1ULL<<n)-1));
 else return qwen_actual_phy::bits(v.data(),off,n);
}
template<class V>void set_bits(V&v,unsigned off,unsigned n,unsigned value){
 if constexpr(std::is_integral_v<V>){uint64_t mask=(n==32?0xffffffffULL:((1ULL<<n)-1))<<off;v=V((uint64_t(v)&~mask)|((uint64_t(value)<<off)&mask));}
 else qwen_actual_phy::put(v.data(),off,n,value);
}

class KernelRows {
 struct Owner {bool value;unsigned channel,t,slot; qwen_actual_phy::RowIdentity identity;};
 struct Reply {Owner owner;qwen_actual_phy::RowBytes data;};
 qwen_actual_phy::RowBackend& backend;
 std::map<uint64_t,Owner> owners;
 std::array<std::deque<Reply>,32> kr;
 std::array<std::deque<Reply>,4> vr;
 std::array<unsigned,32> k_owned{};std::array<unsigned,4> v_owned{};
 public:
 uint64_t k_requests=0,v_requests=0,k_returns=0,v_returns=0;
 explicit KernelRows(qwen_actual_phy::RowBackend& b):backend(b){}
 void collect(){qwen_actual_phy::RowReturn r;
  while(backend.pop_row(r)){auto it=owners.find(r.ticket);if(it==owners.end())throw std::runtime_error("unowned physical row return");auto o=it->second;
   if(r.identity.epoch!=o.identity.epoch||r.identity.layer!=o.identity.layer||r.identity.pos!=o.t||r.identity.kind!=o.identity.kind)
    throw std::runtime_error("physical row response identity mismatch");
   if(o.value)vr[o.channel].push_back({o,r.data});else kr[o.channel].push_back({o,r.data});owners.erase(it);
  }
 }
 template<class K>void drive(K& k){using namespace qwen_actual_phy;collect();
  k.k_req_ready=0;k.v_req_ready=0;k.k_rsp_valid=0;k.v_rsp_valid=0;
  for(unsigned c=0;c<32;c++){
   if(k_owned[c]<8)k.k_req_ready|=uint32_t(1)<<c;
   if(!kr[c].empty()){auto&r=kr[c].front();k.k_rsp_valid|=uint32_t(1)<<c;
    set_bits(k.k_rsp_t,13*c,13,r.owner.t);set_bits(k.k_rsp_epoch,16*c,16,r.owner.identity.epoch);set_bits(k.k_rsp_layer,6*c,6,r.owner.identity.layer);
    for(unsigned j=0;j<32;j++)k.k_rsp_data[32*c+j]=r.data[j];
   }
  }
  for(unsigned c=0;c<4;c++){
   if(v_owned[c]<8)k.v_req_ready|=1u<<c;
   if(!vr[c].empty()){auto&r=vr[c].front();k.v_rsp_valid|=1u<<c;
    set_bits(k.v_rsp_t,14*c,14,r.owner.t);set_bits(k.v_rsp_slot,3*c,3,r.owner.slot);
    set_bits(k.v_rsp_epoch,16*c,16,r.owner.identity.epoch);set_bits(k.v_rsp_layer,6*c,6,r.owner.identity.layer);
    for(unsigned j=0;j<32;j++)k.v_rsp_data[32*c+j]=r.data[j];
   }
  }
 }
 template<class K>void sample(K& k){using namespace qwen_actual_phy;
  for(unsigned c=0;c<32;c++){
   if(k.k_rsp_valid&(uint32_t(1)<<c)){if(kr[c].empty()||!k_owned[c])throw std::runtime_error("unowned K retirement");kr[c].pop_front();--k_owned[c];++k_returns;}
   if((k.k_req_valid&k.k_req_ready)&(uint32_t(1)<<c)){
    unsigned t=get_bits(k.k_req_t,13*c,13);RowIdentity id{unsigned(k.active_epoch),unsigned(k.active_layer),t,0};
    auto ticket=backend.request_row(id);owners.emplace(ticket,Owner{false,c,t,0,id});++k_owned[c];++k_requests;
   }
  }
  for(unsigned c=0;c<4;c++){
   if((k.v_rsp_valid&k.v_rsp_ready)&(1u<<c)){if(vr[c].empty()||!v_owned[c])throw std::runtime_error("unowned V retirement");vr[c].pop_front();--v_owned[c];++v_returns;}
   if((k.v_req_valid&k.v_req_ready)&(1u<<c)){
    unsigned t=get_bits(k.v_req_t,14*c,14),slot=get_bits(k.v_req_slot,3*c,3);if(((t>>7)&3)!=c)throw std::runtime_error("V request stack map mismatch");
    RowIdentity id{unsigned(k.active_epoch),unsigned(k.active_layer),t,1};auto ticket=backend.request_row(id);
    owners.emplace(ticket,Owner{true,c,t,slot,id});++v_owned[c];++v_requests;
   }
  }
 }
 bool drained()const{for(auto n:k_owned)if(n)return false;for(auto n:v_owned)if(n)return false;return owners.empty();}
};
class SectorWrites {
 qwen_actual_phy::RowBackend& backend;
 std::map<uint64_t,qwen_actual_phy::QuarterIdentity> owners;
 std::deque<qwen_actual_phy::WriteAck> acks;
 public:
 uint64_t issued=0,committed=0;
 explicit SectorWrites(qwen_actual_phy::RowBackend& b):backend(b){}
 template<class Sector,class Front>static void connect(Sector&s,Front&f){
  s.row_v=f.row_v;s.row_kind=f.row_kind;s.row_epoch=f.row_epoch;s.row_layer=f.row_layer;s.row_pos=f.row_pos;
  for(unsigned j=0;j<32;j++)s.row_data[j]=f.row_data[j];f.row_ready=s.row_ready;
 }
 // Consume completions ONCE per core edge; keep these ACK inputs stable during
 // every low-phase fixed-point evaluation. connect() alone is repeatable.
 template<class Sector,class Front>void prepare_acks(Sector&s,Front&f){using namespace qwen_actual_phy;
  WriteAck ack;while(backend.pop_write_ack(ack)){auto it=owners.find(ack.ticket);if(it==owners.end())throw std::runtime_error("unowned physical write completion");acks.push_back(ack);owners.erase(it);}
  s.ack_v=0;f.store_ack_v=0;s.ack_kind=0;f.store_ack_kind=0;
  unsigned mask=0;
  while(!acks.empty()&&!(mask&(1u<<acks.front().identity.q))){auto a=acks.front();acks.pop_front();auto id=a.identity;unsigned q=id.q;mask|=1u<<q;
   s.ack_v|=1u<<q;f.store_ack_v|=1u<<q;s.ack_kind|=id.row.kind<<q;f.store_ack_kind|=id.row.kind<<q;
   set_bits(s.ack_epoch,16*q,16,id.row.epoch);set_bits(f.store_ack_epoch,16*q,16,id.row.epoch);
   set_bits(s.ack_layer,6*q,6,id.row.layer);set_bits(f.store_ack_layer,6*q,6,id.row.layer);
   set_bits(s.ack_pos,18*q,18,id.row.pos);set_bits(f.store_ack_pos,18*q,18,id.row.pos);++committed;
  }
 }
 template<class Sector>void sample(Sector&s){using namespace qwen_actual_phy;
  for(unsigned stack=0;stack<4;stack++)if(bits(s.commands.data(),291*stack,1)){
   unsigned off=291*stack,pc=bits(s.commands.data(),off+1,5),q=pc>>3;
   QuarterIdentity id{{unsigned(s.command_epoch),unsigned(s.command_layer),unsigned(s.command_pos),unsigned(s.command_kind)},q};
   Physical p{stack,pc,bits(s.commands.data(),off+6,5),bits(s.commands.data(),off+11,5),bits(s.commands.data(),off+16,19)};
   Quarter data{};for(unsigned j=0;j<8;j++)data[j]=bits(s.commands.data(),off+35+32*j,32);
   auto t=backend.enqueue_mapped_quarter(id,data,p);owners.emplace(t,id);++issued;
  }
 }
 bool drained()const{return owners.empty()&&acks.empty()&&issued==committed;}
};
}
