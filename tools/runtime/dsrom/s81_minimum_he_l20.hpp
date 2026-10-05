#pragma once
#include "s81_minimum_source_bindings.hpp"

// Existing HHW8 source layout: (native he_w_addr[bank]*8+bank) selects one
// eight-F32 word. false selects released layers.20.hc_attn_fn; true selects
// layers.20.hc_ffn_fn. Each is F32[24,20480], 61440 words. Caller enrolls the
// checkpoint-bound byte reader; missing source must throw, never zero-fill.
using DsromS81MinimumL20HeWordRead=
    std::function<std::array<uint32_t,8>(bool ffn,uint64_t line)>;

// actual_ops[0/1] are the caller's source-mapped L20.I1/I78 operations,
// including unique publication indices and exact 2048-bit instructions.
// Reuses the existing s81_native_he_bootstrap C ABI/library, HE arithmetic
// only: no bootstrap arm/reduction or PF/SSX writes. The returned engine's
// participant is its SOLE clock owner; nest in Prefix, do not also register.
DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_he_l20(
    DsromS81MinimumRuntime&,uint64_t identity,
    dsrom_s81_minimum::PrefixPublication&,const DsromS81MinimumSourceIo&,
    const DsromS81MinimumSourceTags&,std::function<bool()> actual_entry_complete,
    const std::array<DsromS81PrefixOperation,2>& actual_ops,
    DsromS81MinimumL20HeWordRead released_words);
