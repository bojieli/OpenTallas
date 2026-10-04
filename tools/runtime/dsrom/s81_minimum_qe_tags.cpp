#include <algorithm>
// Compile this TU INSTEAD OF s81_minimum_source_tags_component.cpp. It extends
// the same provider/accepted ledger, not a second reservation namespace.
#include "s81_minimum_source_tags_component.cpp"
std::array<uint32_t,8> dsrom_s81_reserve_qe_root_tag(
 DsromS81MinimumRuntime&r,uint64_t id,unsigned producer,
 const ReturnPhaseBinding&b,const CaptureOwner&c){
 auto p=registered[&r].lock();
 if(!p||id!=p->id||producer>=(1u<<14)||b.identity!=id||c.identity!=id||
    b.stage<0||b.stage>=81||b.rank!=r.rank||b.pair<0||b.pair>=2417||b.phase>=1024||
    c.phase!=b.phase||c.root!=b.root||c.position!=0||c.row>=((b.phrom0>>46)&65535)||
    c.element_address>=(1u<<19)||b.cfg_path.empty()||b.source_matrix_sha256.size()!=64||
    std::find(b.component_rows.begin(),b.component_rows.end(),c.row)==b.component_rows.end())
  throw std::runtime_error("QE root source reservation requires actual selected row/pair");
 if(p->plans.size()>=Provider::MAX_RECORDS||p->planned_ordinal>=(1ull<<26))
  throw std::runtime_error("QE component planned IDs exhausted; no overflow reuse");
 // Explicit COMPONENT_TAG227 experiment, actual physical pair/phase/producer.
 // Existing provider identity is the minimum experiment's identity47, not an
 // invented production full169 owner. Shared ordinal advances at reserve ONLY.
 auto context=T::experiment_context(b.stage,b.rank,b.pair,b.phase,producer);
 auto tag=T::pack({context,1,p->planned_ordinal>>10,p->planned_ordinal&1023});
 if(!p->plans.emplace(tag,Provider::Planned{tag,c.element_address,false,false,{}}).second)
  throw std::runtime_error("QE duplicate planned tag");
 ++p->planned_ordinal;return tag;
}
