#pragma once
#include "s81_minimum_source_bindings.hpp"
// Additional native writer reservation surface. SU/HE/bootstrap call at actual
// native output strobe BEFORE publication.native_scalar; no acceptance or ACK
// is fabricated. PrefixPublication retains returned immutable MacroWrite.
dsrom_s81_minimum::MacroWrite dsrom_s81_reserve_native_scalar_tag(
 DsromS81MinimumRuntime&,uint64_t identity,unsigned literal_producer,
 uint32_t actual_scalar_address,uint32_t actual_native_bits);
