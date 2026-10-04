#include "s81_minimum_source_bindings.hpp"
#include "../../native/dsrom_vm_tag227_source_hook.hpp"
#include <fstream>
#include <map>
#include <memory>
#include <cstdlib>
#include <sstream>
#include <limits>
using dsrom_s81_minimum::MacroWrite;
using dsrom_s81_minimum::CaptureOwner;
using dsrom_s81_minimum::ReturnPhaseBinding;
namespace {
namespace T=dsrom::component_tag227;
struct Provider {
 DsromS81MinimumRuntime& runtime;std::uint64_t id;int stage,rank,pair;
 struct Planned {T::Tag227 owner;std::uint32_t scalar;bool read,accepted=false;std::optional<std::uint32_t> expected_bits;};
 std::map<T::Tag227,Planned> plans;
 // Planned ordinal and ACTUAL accepted count are distinct; no ACK advances either.
 std::uint64_t planned_ordinal=0,actual_accepted=0;
 std::map<std::tuple<std::uint64_t,std::uint32_t,std::uint32_t>,MacroWrite> held_records;
 std::vector<T::Tag227> actual_order;
 unsigned phase=0,entry=0;
 static constexpr std::size_t MAX_RECORDS=131072;
 Provider(DsromS81MinimumRuntime&r,std::uint64_t identity):runtime(r),id(identity),stage(r.stage),rank(r.rank),pair(r.pair){
  if(id!=(1ull<<31)||r.stage<0||r.stage>80||r.rank<0||r.rank>3||r.pair<0||r.pair>2416||!r.cycle)
   throw std::runtime_error("component source/runtime/identity range");
  // Bind the actual selected source directory; no hardcoded obsolete stage37.
  const char* path=std::getenv("DSROM_S81_MINIMUM_SELECTED_DIR");
  if(!path||!*path)throw std::runtime_error("source-selected PHROM/CFG path required");
  std::ifstream in(std::string(path)+"/spine_phase.hex");std::string s;
  if(!std::getline(in,s))throw std::runtime_error("source PHROM missing");
  std::size_t n=0;auto ph=std::stoull(s,&n,16);
  if(n!=s.size()||ph!=22517998140008448ull)throw std::runtime_error("minimum source PHROM not selected literal");
  std::ifstream cfg(std::string(path)+"/e"+std::to_string(r.pair)+".cfg.hex");
  if(!cfg.good())throw std::runtime_error("actual selected pair CFG missing");
  // Selected factory's literal component phase/key are phase0 / emitted_key0.
  // Enrolled through exact PHROM plus caller ReturnPhaseBinding equality below.
  phase=0;entry=0;
 }
 T::Tag227 reserve(std::uint32_t scalar,bool read,unsigned source_phase,unsigned source_entry){
  if(runtime.stage!=stage||runtime.rank!=rank||runtime.pair!=pair)throw std::runtime_error("changed frozen compiled selection");
  if(scalar>=(1u<<19)||plans.size()==MAX_RECORDS||planned_ordinal>=(1ull<<26))
   throw std::runtime_error("bounded component planned tags exhausted; no wrap");
  auto c=T::experiment_context(runtime.stage,runtime.rank,runtime.pair,source_phase,source_entry);
  auto tag=T::pack({c,1,planned_ordinal>>10,planned_ordinal&1023});
  plans.emplace(tag,Planned{tag,scalar,read,false,{}});++planned_ordinal;return tag;
 }
 MacroWrite scalar(std::uint32_t address,std::uint32_t bits,unsigned source_phase,unsigned source_entry){
  MacroWrite c{};c.source={id,std::uint16_t(source_phase),std::uint16_t(address&65535),0,0,address};
  c.word.address=address>>4;c.word.mask=1u<<(address&15);c.word.data[address&15]=bits;
  c.word.owner=reserve(address,false,source_phase,source_entry);plans.at(c.word.owner).expected_bits=bits;return c;
 }
 MacroWrite record(const S81EmbeddingOutput&out,unsigned lane){
  if(!out.vm_valid||out.fault||out.vm_identity!=id||lane>=16||std::uint64_t(out.vm_address)+lane>=(1u<<19))
   throw std::runtime_error("native held Record lacks source identity/lane/address");
  auto key=std::make_tuple(out.vm_identity,out.vm_address+lane,out.vm_data[lane]);
  auto it=held_records.find(key);if(it!=held_records.end())return it->second;
  auto c=scalar(out.vm_address+lane,out.vm_data[lane],phase,entry);held_records.emplace(key,c);return c;
 }
 void accepted(const T::Tag227& tag,std::uint32_t scalar,bool read){
  auto it=plans.find(tag);
  if(it==plans.end()||it->second.accepted||it->second.scalar!=scalar||it->second.read!=read)
   throw std::runtime_error("unreserved/duplicate/wrong command actual acceptance");
  actual_order.push_back(tag);it->second.accepted=true;++actual_accepted;
 }
};
std::map<DsromS81MinimumRuntime*,std::weak_ptr<Provider>> registered;
}
DsromS81MinimumSourceTags dsrom_s81_bind_minimum_source_tags(DsromS81MinimumRuntime&r,uint64_t id){
 if(auto old=registered[&r].lock())throw std::runtime_error("duplicate component source tag provider");
 auto p=std::make_shared<Provider>(r,id);registered[&r]=p;
 DsromS81MinimumSourceTags tags;
 tags.record=[p](const auto&out,unsigned lane){return p->record(out,lane);};
 tags.read_owner=[p](auto identity,auto address){if(identity!=p->id)throw std::runtime_error("read context");return p->reserve(address,true,p->phase,p->entry);};
 tags.root_owner=[p](const ReturnPhaseBinding&b,const CaptureOwner&c){
  if(b.stage!=p->runtime.stage||b.rank!=p->runtime.rank||b.pair!=p->runtime.pair||b.identity!=p->id||
     b.phase!=p->phase||b.emitted_key!="0"||c.identity!=p->id||c.phase!=b.phase||c.root!=b.root)
   throw std::runtime_error("root source compiled binding mismatch");
  return p->reserve(c.element_address,false,b.phase,0);
 };
 tags.scalar_accept=[p](unsigned bank,const MacroWrite&c){
  auto a=c.source.element_address;
  if(bank>=4||bank!=((a>>4)&3)||c.word.address!=(a>>4)||c.word.mask!=(1u<<(a&15))||
     c.source.identity!=p->id||c.source.phase!=T::unpack(c.word.owner).context.phase10)
   throw std::runtime_error("actual scalar bank/source tuple mismatch");
  auto planned=p->plans.find(c.word.owner);
  if(planned==p->plans.end()||(planned->second.expected_bits&&c.word.data[a&15]!=*planned->second.expected_bits))
   throw std::runtime_error("changed held native scalar bits");
  p->accepted(c.word.owner,a,false);
 };
 // Popper read observer's address is scalar Address19 (not rd_base_word15).
 // This must match the original held read_owner(id,address) source request.
 tags.read_accept=[p](std::uint32_t address,const auto&owner){p->accepted(owner,address,true);};
 return tags;
}
// Native SU/HE/bootstrap writers call this at their actual output strobes before
// publication.native_scalar. Actual accept remains Popper's later callback.
MacroWrite dsrom_s81_reserve_native_scalar_tag(DsromS81MinimumRuntime&r,uint64_t id,
 unsigned producer,uint32_t address,uint32_t bits){
 auto p=registered[&r].lock();if(!p||id!=p->id||producer>8)throw std::runtime_error("native producer tag binding");
 return p->scalar(address,bits,p->phase,producer);
}
