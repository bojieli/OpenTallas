#pragma once
#include "s81_minimum_source_bindings.hpp"
#include "VDsromQeQuant.h"
// Native ot_hdc_v41_qe only. No reconstructed codes from dequantized w_data.
// Noether samples native() OLD ports in its prepare before ANY rising eval:
// mode1: kvb_* -> WINDOW. mode3 && w_we[0]: w_addr/w_data -> CKV nw_*.
struct DsromS81NativeQeQuantizerPorts {
 std::function<const VDsromQeQuant&()> native;
 std::function<DsromS81PrefixOperation()> held_operation;
 std::function<unsigned()> held_mode;
 std::function<bool()> accepts_on_current_shared_edge;
 std::function<std::optional<uint32_t>(unsigned)> actual_dynamic;
 // Positive actual CKV code AND scale backend visibility for the held op;
 // never request ready/accept/native QE idle. Mandatory for mode3 retirement.
 std::function<bool(const DsromS81PrefixOperation&)> ckv_writes_visible;
};
DsromS81PrefixNativeEngine dsrom_s81_bind_minimum_qe_quantizer(
 DsromS81MinimumRuntime&,uint64_t,dsrom_s81_minimum::PrefixPublication&,
 const DsromS81MinimumSourceIo&,DsromS81NativeQeQuantizerPorts& borrowed_ports);
// Compose ONE unit3 engine with existing full matrix field actor. No duplication
// of cut clock, native math, bank participant, or source tag reservation ledger.
DsromS81PrefixNativeEngine dsrom_s81_bind_qe_modes(
 DsromS81PrefixNativeEngine field,DsromS81PrefixNativeEngine quantizer);
