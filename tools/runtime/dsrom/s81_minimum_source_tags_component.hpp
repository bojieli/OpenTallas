#pragma once
#include "s81_minimum_source_bindings.hpp"
// Additional native writer reservation surface. SU/HE/bootstrap call at actual
// native output strobe BEFORE publication.native_scalar; no acceptance or ACK
// is fabricated. PrefixPublication retains returned immutable MacroWrite.
dsrom_s81_minimum::MacroWrite dsrom_s81_reserve_native_scalar_tag(
 DsromS81MinimumRuntime&,uint64_t identity,unsigned literal_producer,
 uint32_t actual_scalar_address,uint32_t actual_native_bits);

// Call only from existing actual matched old-head receipt / captured checked
// read response path. These release component witness seats, NOT source phase
// credits or production mutable-protection qualification.
void dsrom_s81_retire_source_scalar_tag(DsromS81MinimumRuntime&,unsigned actual_bank,
 const dsrom_s81_minimum::MacroWrite&,const dsrom_s81_minimum::VmReceipt&);
void dsrom_s81_retire_source_read_tag(DsromS81MinimumRuntime&,uint32_t requested_scalar,
 const std::array<uint32_t,8>& actual_captured_owner);
