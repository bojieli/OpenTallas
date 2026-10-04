#pragma once
#include "dsrom_vm_tag227_source_hook.hpp"
#include <optional>
#include <vector>
namespace dsrom { namespace component_tag227 {
// Bounded SOFTWARE planned reservation: 16 scalar records plus one read.
// Not provider credits, not another bank callback, not actual accept counts.
class PlannedTagReservations {
public:
 enum class Kind {ScalarWrite, Read64, ReadElement};
 struct Plan {SourceOffer source;Kind kind;std::uint32_t scalar_address;};
 struct Actual {Tag227 owner;Kind kind;std::uint32_t scalar_address;std::uint64_t edge;};
private:
 struct Seat {Plan plan;Tag227 owner;bool accepted=false,retired=false;};
 std::vector<Seat> seats_;std::vector<Actual> accept_order_;
 std::uint64_t era_,batch_;std::uint16_t next_planned_id_=0;
 static constexpr std::size_t CAP=17;
 Seat& find(const Tag227& owner){
  validate(owner);
  for(auto& s:seats_)if(s.owner==owner)return s;
  throw std::invalid_argument("unreserved/stale COMPONENT_TAG227");
 }
public:
 PlannedTagReservations(std::uint64_t era,std::uint64_t batch):era_(era),batch_(batch){require_width(era,32);require_width(batch,16);}
 // Atomic all-or-none construction. This allocates planned ordinal tags only;
 // actual_accepted_count() remains unchanged. Never repeatedly call offer_tag()
 // from the single-held SourceOfferHook to construct a multi-record batch.
 std::vector<Tag227> reserve(const std::vector<Plan>& plans){
  if(plans.empty()||seats_.size()+plans.size()>CAP||next_planned_id_+plans.size()>1024)
   throw std::out_of_range("bounded COMPONENT_TAG227 planned capacity/ID exhaustion");
  std::vector<Seat> fresh;std::vector<Tag227> tags;
  for(std::size_t i=0;i<plans.size();++i){auto& p=plans[i];
   if((p.kind!=Kind::ScalarWrite&&p.kind!=Kind::Read64&&p.kind!=Kind::ReadElement)||p.scalar_address>=(1u<<19)||(p.kind==Kind::Read64&&(p.scalar_address&63)))
    throw std::out_of_range("planned native VM19 / aligned Read64");
   auto tag=pack({context_from_source_offer(p.source),era_,batch_,next_planned_id_+i});
   fresh.push_back({p,tag,false,false});tags.push_back(tag);
  }
  seats_.insert(seats_.end(),fresh.begin(),fresh.end());next_planned_id_+=plans.size();return tags;
 }
 // Called by Popper's ONE actual PRE-edge accept observer, in actual bank order.
 // Caller passes the installed command metadata, not current unrelated offer.
 void actual_accept(const Actual& a,const SourceOffer& frozen_command,bool actual_rst_n){
  if(!actual_rst_n)throw std::logic_error("planned tag acceptance during reset");
  auto& s=find(a.owner);
  if(s.accepted||s.retired||s.plan.kind!=a.kind||s.plan.scalar_address!=a.scalar_address||
     pack({context_from_source_offer(frozen_command),era_,batch_,unpack(a.owner).request_id})!=s.owner)
   throw std::invalid_argument("changed/duplicate planned actual acceptance");
  if(!accept_order_.empty()&&a.edge<accept_order_.back().edge)
   throw std::invalid_argument("actual observer edges must be monotonic, not lane order");
  accept_order_.push_back(a);s.accepted=true;
 }
 void qualified_retire(const Tag227& owner){
  auto& s=find(owner);
  if(!s.accepted||s.retired)throw std::invalid_argument("unaccepted/duplicate retirement");
  s.retired=true;
 }
 std::size_t actual_accepted_count()const{return accept_order_.size();}
 const std::vector<Actual>& actual_accept_order()const{return accept_order_;}
 std::size_t planned_count()const{return seats_.size();}
 bool batch_retired()const{
  if(seats_.empty())return false;
  for(auto& s:seats_)if(!s.accepted||!s.retired)return false;
  return true;
 }
 void next_batch(){
  if(!batch_retired())throw std::logic_error("planned/accepted command debt remains");
  require_width(batch_+1,16);++batch_;seats_.clear();accept_order_.clear();next_planned_id_=0;
 }
};
}}
