# S81 t13 corridor candidate — owner PASS-COND

This private replay widens the upper west M7-free corridor by moving four
existing macros and keeping all 27 macro instances. Two north input storage
bands move above the VE columns. Four existing FT stage footprints move.
The RTL, pins, outline, internal station counts, reset edges/depths and cycles
remain unchanged.

The actual image t13_form.png was viewed by types and the S81 plan owner before
route. Owner adopted a bounded private canary, preserving the inherited intel1
t13 pilot. This is NOT a routed or SIGNED result.

- Full FT per-bit footprints are macro-free, unique; matching bit-stage maximum
  Manhattan hop402.57um; whole input-window/ring/output-window corners also
  remain under402.84um.
- 88 existing internal core-to-core station rows retain counts; endpoints follow
  actual macro translations, with no macro conflict or hop over402.84um.
- Existing reset stages keep names/drivers/Q/depth/tap/kind; maximum hop398.52um.
  Eleven existing physical reset sites move, plus endpoint aliases.
- Actual native grid retains16 tap names; three sites relocate by the original
  macro-aware grid function. All53 grid+explicit tap sites pass their native
  outline/halo/spacing check. clk_t34 was adjusted2.108um to the exact canonical
  track-offset halo boundary; clk_t50 moved13um from the first draft to retain
  native tap spacing. clk_t44 was subsequently recentered to [345.6,1170.72] to satisfy its unchanged200um clockload radius; reset aliases follow; no reset age changes.

The replay checks fixed geometry, counts and hops and emits an isolated plan.
Native kit export on released ad-s81/faecd passed (62 source files, zero unbound buses), including unchanged native clockload limits. Physical generation, CTS/STA, GRT overflow and final
hold/DRV remain owed. Start with util0.40/M7 and bounded resources, and diagnose
the canary before any family release. No held item was cleared by this event.
