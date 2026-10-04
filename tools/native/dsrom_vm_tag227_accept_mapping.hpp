#pragma once
#include "dsrom_vm_tag227_planned.hpp"
#include <map>
namespace dsrom { namespace component_tag227 {
// Generic adapter to Popper ActualVmAcceptObservers.scalar(bank,MacroWrite)
// and read(requested_scalar_address,Owner227). No bank loop/clock/model eval is owned here.
class PlannedAcceptMapping {
 PlannedTagReservations ledger_;
 std::map<Tag227,PlannedTagReservations::Plan> plans_;
 const PlannedTagReservations::Plan& lookup(const Tag227& tag)const {
  auto it=plans_.find(tag);if(it==plans_.end())throw std::invalid_argument("unplanned actual VM owner");return it->second;
 }
public:
 PlannedAcceptMapping(std::uint64_t era,std::uint64_t batch):ledger_(era,batch){}
 std::vector<Tag227> reserve(const std::vector<PlannedTagReservations::Plan>& plans){
  auto tags=ledger_.reserve(plans);
  for(std::size_t i=0;i<tags.size();++i)plans_.emplace(tags[i],plans[i]);
  return tags;
 }
 template<class MacroWrite>void scalar(unsigned bank,const MacroWrite& command,std::uint64_t actual_edge){
  Tag227 owner=command.word.owner;const auto& p=lookup(owner);
  if(p.kind!=PlannedTagReservations::Kind::ScalarWrite||bank>=4||
     command.word.address!=(p.scalar_address>>4)||bank!=((p.scalar_address>>4)&3)||
     command.word.mask!=(1u<<(p.scalar_address&15))||
     command.source.element_address!=p.scalar_address||command.source.identity!=p.source.identity47||
     command.source.phase!=p.source.accepted_phase)
   throw std::invalid_argument("actual MacroWrite mismatches sealed scalar plan");
  ledger_.actual_accept({owner,p.kind,p.scalar_address,actual_edge},p.source,true);
 }
 // Popper/Cicero callback is requested ELEMENT address19. The backend
 // internally aligns a native Read64; this observer does not shift twice.
 void read(std::uint32_t scalar_address,const Tag227& owner,std::uint64_t actual_edge){
  const auto& p=lookup(owner);
  if((p.kind!=PlannedTagReservations::Kind::Read64&&p.kind!=PlannedTagReservations::Kind::ReadElement)||
     scalar_address>=(1u<<19)||scalar_address!=p.scalar_address)
   throw std::invalid_argument("actual requested scalar read owner/address mismatch");
  ledger_.actual_accept({owner,p.kind,p.scalar_address,actual_edge},p.source,true);
 }
 void qualified_retire(const Tag227& owner){ledger_.qualified_retire(owner);}
 const std::vector<PlannedTagReservations::Actual>& accepted_order()const{return ledger_.actual_accept_order();}
 std::size_t actual_accepted_count()const{return ledger_.actual_accepted_count();}
};
}}
