#pragma once
#include <array>
#include <cstdint>
#include <deque>
#include <functional>
#include <map>
#include <optional>
#include <stdexcept>
#include <vector>
#include "dsrom_vm_tag227.hpp"
namespace dsrom { namespace sun256 {
using Tag=component_tag227::Tag227;
struct ReadRequest {std::uint32_t scalar_base;Tag owner;};
struct ReadAccepted {ReadRequest request;std::uint64_t source_edge;};
struct ReadReply {std::uint32_t scalar_base;Tag owner;std::array<std::uint32_t,64> words;std::uint64_t source_postNBA_edge;};
// Actual same-VM participant: drive held request, report real accepted PRE edge,
// deliver only captured matching checked read reply in logical scalar order.
// It owns rotation/bank expansion/protection and qualified retirement, not this cache.
struct VmReadPort {
 std::function<void(const std::optional<ReadRequest>&)> drive;
 std::function<std::optional<ReadAccepted>()> actual_accept;
 std::function<std::optional<ReadReply>()> checked_reply;
 std::function<bool()> lease_held;
 std::function<bool()> fault;
};
class OperandStage {
 static constexpr std::size_t CAP_WORDS=20480;
 VmReadPort port_;std::vector<std::uint32_t> groups_;
 std::map<std::uint32_t,std::uint32_t> words_;
 std::size_t next_=0;std::optional<ReadRequest> offered_,accepted_;
 std::uint64_t accepted_edge_=0;
 bool active_=false,failed_=false;
 std::function<Tag()> next_tag_;
 static bool same(const ReadRequest&a,const ReadRequest&b){return a.scalar_base==b.scalar_base&&a.owner==b.owner;}
public:
 OperandStage(VmReadPort port,std::function<Tag()> next_tag)
 :port_(std::move(port)),next_tag_(std::move(next_tag)) {
  if(!port_.drive||!port_.actual_accept||!port_.checked_reply||!port_.lease_held||!port_.fault||!next_tag_)
   throw std::invalid_argument("actual VM read/lease/receipt hooks required");
 }
 void begin(const std::vector<std::uint32_t>& groups) {
  if(active_||offered_||accepted_||failed_)throw std::logic_error("operand staging overlap/quarantine");
  if(groups.size()*64>CAP_WORDS)throw std::out_of_range("finite operand staging");
  std::map<std::uint32_t,bool> seen;
  for(auto a:groups){if((a&63)||a>=(1u<<19)||seen.count(a))throw std::invalid_argument("aligned unique VM group19");seen[a]=true;}
  groups_=groups;words_.clear();next_=0;active_=true;
 }
 void prepare() {
  if(failed_||port_.fault()||!port_.lease_held()){failed_=true;throw std::logic_error("actual VM fault/input version lease lost");}
  try {
   if(auto a=port_.actual_accept()){
    if(!offered_||accepted_||!same(a->request,*offered_))throw std::logic_error("wrong/duplicate VM acceptance");
    accepted_=a->request;accepted_edge_=a->source_edge;offered_.reset();
   }
   if(auto r=port_.checked_reply()){
    if(!accepted_||r->scalar_base!=accepted_->scalar_base||r->owner!=accepted_->owner||r->source_postNBA_edge<accepted_edge_||r->source_postNBA_edge-accepted_edge_<4)
     throw std::logic_error("unowned/stale VM response; no synthetic due-time data");
    for(unsigned i=0;i<64;++i)words_.emplace(r->scalar_base+i,r->words[i]);
    accepted_.reset();++next_;
   }
   if(active_&&!offered_&&!accepted_&&next_<groups_.size())offered_=ReadRequest{groups_[next_],next_tag_()};
   port_.drive(offered_);
  }catch(...){failed_=true;throw;}
 }
 bool active()const{return active_;}
 bool ready()const{return active_&&!failed_&&!offered_&&!accepted_&&next_==groups_.size();}
 std::uint32_t read(std::uint32_t addr)const {
  if(!ready()||!port_.lease_held())throw std::logic_error("native fixed-latency read before sealed prefetch");
  auto it=words_.find(addr);if(it==words_.end())throw std::out_of_range("native read outside staged actual extent");return it->second;
 }
 void finish_after_native_drain(){if(!ready())throw std::logic_error("staging debt pending");active_=false;}
 bool fault()const{return failed_||port_.fault();}
};
struct NativeWrite {std::uint32_t address,bits;bool reduction;};
class OutputStage {
 // Worst prefix 5120 vector writes plus bounded reducer results, shared identity.
 static constexpr std::size_t CAP=5376;
 std::deque<NativeWrite> held_;
public:
 void capture(std::uint32_t address,std::uint32_t bits,bool reducer){
  if(address>=(1u<<19)||held_.size()==CAP)throw std::out_of_range("actual native output bound");
  held_.push_back({address,bits,reducer});
 }
 const std::deque<NativeWrite>& held()const{return held_;}
 void qualified_visible(const NativeWrite&w){
  if(held_.empty()||held_.front().address!=w.address||held_.front().bits!=w.bits||held_.front().reduction!=w.reduction)
   throw std::logic_error("wrong/order/duplicate winning VM publication");
  held_.pop_front();
 }
 bool empty()const{return held_.empty();}
};
// Bit helpers for generated 256-lane ports. No FP conversions/arithmetic.
template<class Wide> inline std::uint32_t bits(const Wide& p,unsigned offset,unsigned width){
 std::uint32_t v=0;for(unsigned i=0;i<width;++i)v|=((p[(offset+i)/32]>>((offset+i)%32))&1u)<<i;return v;
}
template<class Model> class FixedOperandShim {
 Model& m_;OperandStage& stage_;
 std::function<std::uint32_t(unsigned,std::uint32_t)> external_;
public:
 FixedOperandShim(Model&m,OperandStage&s,std::function<std::uint32_t(unsigned,std::uint32_t)> native_external)
 :m_(m),stage_(s),external_(std::move(native_external)){}
 // Snapshot actual PRE-edge rd addresses. Evaluate leaf with old rd_q FIRST,
 // then install this sample's data after that edge (one native synchronous RAM
 // register). Published address R -> memory reg R+1 -> lane X capture R+2.
 std::array<std::uint32_t,1024> sample()const {
  std::array<std::uint32_t,1024> q{};
  for(unsigned j=0;j<1024;++j){
   if(!bits(m_.rd_re,j,1)){q[j]=m_.rd_q[j];continue;}
   auto addr=bits(m_.rd_addr,j*30,30);auto src=bits(m_.rd_src,j*2,2);
   if(src==0)q[j]=stage_.read(addr);
   else {if(!external_)throw std::logic_error("actual native constant/weight provider required");q[j]=external_(src,addr);}
  }return q;
 }
 void install_post_edge(const std::array<std::uint32_t,1024>&q){for(unsigned j=0;j<1024;++j)m_.rd_q[j]=q[j];}
 void capture_post_edge(OutputStage& out)const {
  // Source order: vector writer family then reducer family; no arithmetic or
  // magical ACK here. Actual participant must adjudicate simultaneous writers.
  for(unsigned j=0;j<256;++j)if(bits(m_.vm_we,j,1))out.capture(bits(m_.vm_waddr,j*30,30),m_.vm_wdata[j],false);
  for(unsigned j=0;j<32;++j)if(bits(m_.res_we,j,1))out.capture(bits(m_.res_addr,j*30,30),m_.res_data[j],true);
  for(unsigned j=0;j<256;++j)if(bits(m_.kv_we,j,1))throw std::logic_error("prefix unexpected KV write requires real KV participant");
 }
};
}}
