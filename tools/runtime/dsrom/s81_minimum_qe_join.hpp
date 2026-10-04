#pragma once
#include "s81_minimum_qe.hpp"

// The canonical factory owns the cut, SourceIo, publication and source tags.
// Construct the actors BEFORE shared cold_start. Install this engine at unit3;
// DO NOT arm the old pair0/two-row fixture. SourceFactory already performs the
// one tag retirement, so these callbacks append witnesses, never retire again.
inline DsromS81PrefixNativeEngine dsrom_s81_bind_native_qe_field(
 const std::vector<std::shared_ptr<DsromS81NativeQe>>& phases,
 DsromS81MinimumSourceTags& factory_tags,
 std::function<void(unsigned,const dsrom_s81_minimum::MacroWrite&,
                    const dsrom_s81_minimum::VmReceipt&)>& factory_visibility){
 if(!factory_tags.scalar_accept||!factory_visibility)
  throw std::runtime_error("QE join requires actual existing bank accept/visibility callbacks");
 auto accepted=factory_tags.scalar_accept;
 factory_tags.scalar_accept=[phases,accepted](unsigned b,const auto&c){
  accepted(b,c);
  for(const auto&p:phases)if(p->owns(c))p->scalar_accept(b,c);
 };
 auto visible=factory_visibility;
 factory_visibility=[phases,visible](unsigned b,const auto&c,const auto&v){
  visible(b,c,v);
  for(const auto&p:phases)if(p->owns(c))p->scalar_visible(b,c,v);
 };
 return dsrom_s81_qe_dispatch(phases);
}
