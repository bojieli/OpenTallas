#pragma once
#include "actual_phy.hpp"
#include "verilated.h"
#include <memory>
#include <string>
#include <tuple>
#include <set>
namespace qwen_actual_phy {
struct RowIdentity {uint32_t epoch,layer,pos,kind;};
struct QuarterIdentity {RowIdentity row;unsigned q;};
struct Physical {unsigned stack,pc,bank,col,row;unsigned index()const{return 32*stack+pc;}uint64_t address()const{return key(row,bank,col);}};
inline Physical native_map(const QuarterIdentity& id){
 auto r=id.row;if(r.epoch>65535||r.layer>=36||r.pos>=8192||r.kind>1||id.q>=4)throw std::runtime_error("native KV identity out of bounds");
 unsigned sec=(r.layer<<11)|(r.kind<<10)|(((r.pos>>6)&1)<<8)|((r.pos>>9)<<3)|((r.pos>>3)&7);
 unsigned j=((sec>>8)&7)<<7|(sec&127);
 return {(r.pos>>7)&3,id.q*8+(r.pos&7),((j>>7)<<2)|(j&3),(j>>2)&31,64+r.layer};
}
using Quarter=std::array<uint32_t,8>;
using RowBytes=std::array<uint32_t,32>;
struct WriteAck {uint64_t ticket;QuarterIdentity identity;uint64_t core_edge,hbm_edge;};
struct RowReturn {uint64_t ticket;RowIdentity identity;RowBytes data;uint64_t core_edge,hbm_edge;};
// One compiled controller class instantiated 128 times, not 128 RTL elaborations.
// Each physical PC has its own actual controller clocks, SRAM/ECC/CDC state,
// PHY backing, four host credits and four landing credits.
class RowBackend {
 struct Write {uint64_t ticket;QuarterIdentity id;Quarter data;};
 struct Read {uint64_t ticket;QuarterIdentity id;};
 struct Assemble {RowIdentity id;RowBytes data{};unsigned mask=0;};
 struct Channel {
  std::unique_ptr<Vqwen_native_hbm_pc_provider> model;Backing phy;
  std::deque<Write> writes,issued_writes;
  std::deque<Read> reads,issued_reads;
  unsigned host_credits=4,land_credits=4;
  uint64_t ack_index=0;
 };
 std::array<Channel,128> channels;
 std::map<uint64_t,Assemble> assembling;
 std::deque<WriteAck> completed_writes;
 std::deque<RowReturn> completed_rows;
 using IdentityKey=std::tuple<uint32_t,uint32_t,uint32_t,uint32_t,unsigned>;
 std::set<IdentityKey> acknowledged,pending_writes,declared_image;
 VerilatedContext& ctx;
 unsigned current_position;
 uint64_t ticket_next=1,core_next=553667,hbm_next=512000;
 bool core_high=false,hbm_high=false;
 static IdentityKey ik(const QuarterIdentity& x){return {x.row.epoch,x.row.layer,x.row.pos,x.row.kind,x.q};}
 void observe_core(){
  for(auto&c:channels){auto&m=*c.model;
   if(!m.rst_n)continue;
   if(m.host_cr){if(++c.host_credits>4)throw std::runtime_error("host credit overflow");}
   if(bits(m.land_er.data(),259,1)){if(++c.land_credits>4)throw std::runtime_error("landing credit overflow");}
   if(m.host_ack){
    if(c.issued_writes.empty())throw std::runtime_error("host ACK without issued quarter");
    auto w=c.issued_writes.front();auto address=native_map(w.id).address();
    if(c.ack_index>=c.phy.written_keys.size()||c.phy.written_keys[c.ack_index]!=address)throw std::runtime_error("ACK physical quarter identity mismatch");
    if(hbm_edges<c.phy.written_at[c.ack_index]+12)throw std::runtime_error("host ACK before actual WDONE17");
    ++c.ack_index;c.issued_writes.pop_front();acknowledged.insert(ik(w.id));pending_writes.erase(ik(w.id));
    completed_writes.push_back({w.ticket,w.id,core_edges,hbm_edges});++write_acks;
   }
   if(bits(m.land_er.data(),0,1)){
    if(c.issued_reads.empty())throw std::runtime_error("landing return without requested quarter");
    if(bits(m.land_er.data(),258,1))throw std::runtime_error("landing uncorrectable ECC");
    auto r=c.issued_reads.front();c.issued_reads.pop_front();auto&a=assembling.at(r.ticket);
    if(a.mask&(1u<<r.id.q))throw std::runtime_error("duplicate row quarter return");
    for(unsigned j=0;j<8;j++)a.data[8*r.id.q+j]=bits(m.land_er.data(),1+32*j,32);
    a.mask|=1u<<r.id.q;++read_quarters;
    if(a.mask==15){completed_rows.push_back({r.ticket,a.id,a.data,core_edges,hbm_edges});assembling.erase(r.ticket);++row_returns;}
   }
   if(m.fo||m.static_fault||m.completion_fault||bits(m.land_er.data(),260,1))throw std::runtime_error("actual PC controller fault");
  }
 }
 void drive_core_falling(){
  for(auto&c:channels){auto&m=*c.model;
   for(unsigned j=0;j<9;j++){m.host_es[j]=0;m.land_es[j]=0;}
   if(hbm_edges<160)continue;
   if(c.host_credits&&!c.writes.empty()){
    auto w=c.writes.front();c.writes.pop_front();c.issued_writes.push_back(w);--c.host_credits;auto p=native_map(w.id);
    put(m.host_es.data(),0,1,1);put(m.host_es.data(),286,2,3);put(m.host_es.data(),281,5,p.bank);put(m.host_es.data(),276,5,p.col);put(m.host_es.data(),257,19,p.row);
    for(unsigned j=0;j<8;j++)put(m.host_es.data(),1+32*j,32,w.data[j]);++write_issues;
   }
   if(c.land_credits&&!c.reads.empty()){
    auto r=c.reads.front();c.reads.pop_front();c.issued_reads.push_back(r);--c.land_credits;auto p=native_map(r.id);
    put(m.land_es.data(),0,1,1);put(m.land_es.data(),281,5,p.bank);put(m.land_es.data(),276,5,p.col);put(m.land_es.data(),257,19,p.row);++read_issues;
   }
  }
 }
 public:
 uint64_t core_edges=0,hbm_edges=0,write_issues=0,write_acks=0,read_issues=0,read_quarters=0,row_returns=0,declared_preloads=0;
 explicit RowBackend(VerilatedContext& context,unsigned token_position):ctx(context),current_position(token_position){
  if(token_position>=8192)throw std::runtime_error("current token out of bounds");
  for(unsigned i=0;i<128;i++){
   auto&c=channels[i];auto name="actual_pc_"+std::to_string(i);c.model=std::make_unique<Vqwen_native_hbm_pc_provider>(&ctx,name.c_str());auto&m=*c.model;
   m.pc=i%32;m.ck=0;m.pll_hbm=0;m.rst_n=0;m.hrst=0;m.fi=0;m.ki=0;
   for(unsigned j=0;j<10;j++){m.ci[j]=0;m.pi[j]=0;}for(unsigned j=0;j<9;j++){m.host_es[j]=0;m.land_es[j]=0;}m.eval();
  }
 }
 uint64_t enqueue_mapped_quarter(const QuarterIdentity&id,const Quarter&data,const Physical&observed){
  auto p=native_map(id);if(observed.stack>=4||observed.pc>=32||observed.bank>=32||observed.col>=32||observed.row>=524288)throw std::runtime_error("sector adapter physical field out of bounds");
  if(p.index()!=observed.index()||p.address()!=observed.address())throw std::runtime_error("sector adapter physical mapping mismatch");
  return enqueue_quarter(id,data);
 }
 uint64_t enqueue_quarter(const QuarterIdentity& id,const Quarter& data){
  if(id.row.pos!=current_position)throw std::runtime_error("current-token writer position mismatch");return enqueue_controller_quarter(id,data);
 }
 uint64_t enqueue_prior_quarter_via_actual_controller(const QuarterIdentity&id,const Quarter&data){
  if(id.row.pos>=current_position)throw std::runtime_error("prior actual writer includes current/future token");return enqueue_controller_quarter(id,data);
 }
 private:
 uint64_t enqueue_controller_quarter(const QuarterIdentity& id,const Quarter& data){
  auto p=native_map(id);if(id.row.pos>current_position)throw std::runtime_error("writer future position mismatch");
  if(!pending_writes.insert(ik(id)).second)throw std::runtime_error("duplicate in-flight quarter identity");
  acknowledged.erase(ik(id));declared_image.erase(ik(id));uint64_t t=ticket_next++;channels[p.index()].writes.push_back({t,id,data});return t;
 }
 public:
 // Prior-cache preload is an explicit harness operation. Caller supplies a
 // declared ECC288 DRAM image; no current-token preload is accepted.
 void declare_prior_quarter(const QuarterIdentity&id,const Codeword&code){
  auto p=native_map(id);if(id.row.pos>=current_position)throw std::runtime_error("prior preload includes current/future token");
  if(pending_writes.count(ik(id)))throw std::runtime_error("preload overlaps pending actual writer");
  channels[p.index()].phy.memory[p.address()]=code;declared_image.insert(ik(id));++declared_preloads;
 }
 bool row_is_committed(const RowIdentity&id)const{
  bool all_ack=true,all_declared=true;
  for(unsigned q=0;q<4;q++){all_ack&=acknowledged.count(ik({id,q}))!=0;all_declared&=declared_image.count(ik({id,q}))!=0;}
  return all_ack||(id.pos<current_position&&all_declared);
 }
 uint64_t request_row(const RowIdentity&id){
  if(id.pos>current_position||!row_is_committed(id))throw std::runtime_error("row request before actual current-token ACKs");
  uint64_t t=ticket_next++;assembling.emplace(t,Assemble{id});
  for(unsigned q=0;q<4;q++){QuarterIdentity qi{id,q};auto p=native_map(qi);channels[p.index()].reads.push_back({t,qi});}return t;
 }
 bool pop_write_ack(WriteAck&out){if(completed_writes.empty())return false;out=completed_writes.front();completed_writes.pop_front();return true;}
 bool pop_row(RowReturn&out){if(completed_rows.empty())return false;out=completed_rows.front();completed_rows.pop_front();return true;}
 Backing& physical_backing(unsigned index){return channels.at(index).phy;}
 const Backing& physical_backing(unsigned index)const{return channels.at(index).phy;}
 // Independent edge hooks let a parent join other compiled RTL models. Calls
 // must preserve rising/falling sequence and monotonic context time.
 void core_edge(bool high){
  if(high==core_high)throw std::runtime_error("duplicate core edge hook");
  if(high){++core_edges;observe_core();}
  for(auto&c:channels){c.model->ck=high;c.model->eval();}
  if(!high){drive_core_falling();for(auto&c:channels)c.model->eval();}
  core_high=high;
 }
 void hbm_edge(bool high){
  if(high==hbm_high)throw std::runtime_error("duplicate HBM edge hook");
  if(high){++hbm_edges;
   for(auto&c:channels){auto pi=c.phy.sample_hbm(*c.model);c.model->pll_hbm=1;c.model->eval();for(unsigned j=0;j<10;j++)c.model->pi[j]=pi[j];c.model->eval();}
   if(hbm_edges==8)for(auto&c:channels){c.model->rst_n=1;c.model->hrst=1;c.model->eval();}
  }else for(auto&c:channels){c.model->pll_hbm=0;c.model->eval();}
  hbm_high=high;
 }
 void begin_token(unsigned position){
  if(position>=8192||position<=current_position||!pending_writes.empty()||!assembling.empty())throw std::runtime_error("token advance before drain or invalid position");
  current_position=position;
 }
 uint64_t next_event_fs()const{return std::min(core_next,hbm_next);}
 void advance_one_event(){auto t=next_event_fs();ctx.time(t);if(core_next<=hbm_next){core_next+=416667;core_edge(!core_high);}else{hbm_next+=512000;hbm_edge(!hbm_high);}}
};
}
