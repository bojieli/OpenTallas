**Superseded reset comparison:** the original comparison below reused a Plan with a cached reset graph. Use `../s81_reset_cache_correction_0405/` for the corrected independent-Plan results and proof. The original source/logs remain historical evidence.

# SOURCE-only slice_station__t18 tap correction

Reviewed actual native census from frozen source39f754dda07e9746c4850ea0814d48d134a6cf2a and the private dead-proof-refreshed + clk_t28 plan. Original FAIL remains in FLOW bind_clk28 and census results.

Move only clk_t16 from (196.6712,294.8172) to M7/M6 track-snapped (197.088,294.112), 1.122um L1. Existing radius150 and capacity1500 are unchanged. Actual419 assigned sinks have feasible u=x+y interval[377.607,623.337], v=x-y interval[-97.053,-25.203], minimum radius114.075. Exact native taps.assign over all13449 sinks gives tap16 radius149.971/load419, all41 taps pass, zero sink membership changes. Type is macrofree (contents[], no canonical placement obstacles); nominal maximum BUFx24 body is clear. Existing frequency, names, edges, all other taps remain unchanged.

The exact frozen reset_tree.for_type was recomputed on original and changed private plans, without a bound_native_contract override. Both have153 native relay/FFs and43 named output taps; every relay coordinate/edge and reset_tree.rtl_lines are byte-identical. Both release in8 clocks. No reset/source RTL, clockload, resetload, boot or mission-cycle delta. The saved old/new JSONs preserve that native comparison; no custom frozen-tree replacement is applied.

Personally viewed actual_native_tap_repair.png: all actual assigned sink endpoints fit the unchanged green150um envelope; the failed red envelope shows the original far endpoint. PASS for this minimal SOURCE-clock coordinate proposal. This is not physical plan qualification: canonical reset physical halo HOLD remains, and the full census terminal result must be collected before the one next coherent BIND-only event. Existing fresh ELAB may be reused because frontend RTL is unchanged. No P&R/STA/new ELAB is authorized by this packet.
