# S81 G4/G8 service geometry feasibility

GEOMETRY ONLY, NOT A DIE RESULT. Coordinator authorized G4 primary and G8 fallback after SVCFIT showed no service fits 122 frames. Parent owner directives prioritize closure and allow frame/die cost. Baseline source is immutable ep6 `/srv/opentallas-scratch/claude/s81-die11/mu7v2c/plan/plan.json` (4ae44d2dd chain).

Reproduce: `python3 tools/s81_dv/service_band_candidate.py --plan BASELINE --groups 4 --out OUT` (then 8).

Actual rectangular child packing: rest1728x1555.2 + 43.2um cell-row separator + attention1296x2160 (G4) /1814.4x2160(G8). All16 regions in one south row. Slots1728/1814.4x3758.4. G4 service103.912mm², G8 109.108mm²; unchanged legal31968.5x25000 outline (799.2125mm²). Real child macro geometry/CTS remains to be built.

Both retain96 frames/880 ROM slots vs122/1130; remove actual colliding frames, move S slices330.08um north, and reserve granted bk_sel907.2x3283.2, seqhost432x777.6, gunit950x1469. Both have zero block overlaps or outline violations (0.05um tolerance for the preexisting facts width rounded0.012um below SerDes edge). No reticle growth. Reader strips still require joint reservation. Exact inventory qualification is owned by token_qualification; no scaled stage or performance claim is made.

Files intentionally omit links rather than claim stale endpoints are routed. Deleted frame links, moved endpoints, corner-reader placement, actual service clocks and <=405um relay channels all need regeneration before trial GRT. Composite boxes do not establish internal relay cell rows. Stage/calendars require exact allocator qualification. No strict-bind/GRT/STA/IR closure claim for these candidates.

Baseline SHA256: 0e1a4250943e5adf78c39e576908dfb9870cdd116d2bbe868e7964ec26f45641

## Split112 successor

The96-frame monolithic candidates FAIL actual allocator dense one-phase capacity:448a_proj rows at4rows/frame require>=112frames; increasing stages cannot fix. Preserve them as failed geometry evidence.

`service_split_candidate.py` generates G4_split112:16 REST-only1728x1555.2 slots across the south band;16 separate attention models950.4x2160 in inter-tier voids. Exact112frames1040slots remain, zero bodyoverlaps/outside, no S-slice movement, unchanged outline. Total service75.844mm². Detailed attention macro model contains32big+38smallSRAMs,4hgrp432; both macro stacks have inserted43.2um cell-row gaps after each8rows. One stdband345.6x1036.8 holds190k assumed cellarea at53.0%. The190k is inherited `mk_attw_lp.py` default input, NOT fresh mapped synthesis. Fresh production NT1 RTL/native/area qualification, static service<->attention links/landing rings/cycle pricing, actual112tensor allocator, index-reader reservation and complete405um relay graph are mandatory before trial GRT. Attention model master is explicitly NOT_RTL.

## Baseline collection

mu7v2c finished22:24:37, GRT0 but STA FAIL. TTsetup-9246.6ps (framexk modeled asdata), FFhold-1617.3ps (ld_hrq_01/rs). Reset stations/fwdENA remaining TT-3725.4/-5642.7ps are real reset reach/startup mechanisms. bk_col geometry fixes improve prior-2.3ns family toTTsetup slicevi-351.9/xtier-222.4ps; residual hold budgets still need planned repair. Native forwarded-clock audit FAIL14/3777 judgedhops postGRT, pairingerrors0. `mu7v2c_classes.txt` preserves complete classes.

`mu7v2c_ir_drop.json`: ROOT14 tool window-model PASS8.85mV rail-to-rail vs35mV on3hotwindows; assumed density1.2W/mm² and735.238Wdiepeak. M8signal0.04% +bothPGstraps19.61%=19.65%. Not final signoff; child-internalPG/package/via-blockage absent. Original immutable route explicitly M2-M8signals/M5-M9clock and M8RC; actual signalguide inspection still needed.

## Clock input replay and reset graph qualification, 22:40 takeover

The immutable GRT replay completed TT and FF with all232 declared clock input bits reached by propagated clocks (`CLOCK_ROLE_PROBE missing=0`). It changed58 stand-in clock-input port models, and actual source Liberty proved16 contributing forwarded clock ports. Native source Liberty and original ODB were untouched. The historical frame-xk setup class(-9246.6ps) disappears. Remaining TTsetup-5642.7ps is gate ENA; FFhold-1617.3ps is landing reset. These are actual obligations, not closure. Replay scripts, manifest and complete classes are preserved here.

`calendar_reset_probe.json` compares the actual baseline graph with retained calendar endpoint paths:4394->4713 reset nodes,1290 additional endpoint consumers, missing local reset sources7->0, zero physical over-reach hops. The original graph was pruned only for block-reset pins and data relay resets; endpoint-serving nodes were discarded. `calendar_reset_endpoints` is an opt-in bind-table flag retaining those paths. It makes cal_tap refuse non-local fallbacks. Eight causal/reset reach tests pass. Full strict source bind is running separately; no full route was launched on an unqualified reset tree.

This reset change addresses physical reach only. Receiving-region two-stage synchronous reset release, native clock roles and actual reset timing remain required. The unrelated645-lane startup proof does not waive arbitrary regional reset crossings.

Actual Claude ATTN1 generator requires1036.8×2160 primary or1123.2×2160 fallback to provide macro-face pin channels. The950.4-wide G4split112 model is not a qualified placement for these real tiles. ATTN1 source qualification is separately pinned on codex/s81-svc-nt-1020@21b79b7e5.

## Reset source bind follow-through

The first full source bind caught16 unread reset outputs after endpoint paths were retained. All other port counters were zero. These were endpoint anchors that the final calendar did not choose. The successor removes only reset relay branches with zero actual consumers, cascading through dead ancestors; it removes their wire declarations, placements and depth entries. It introduces no tie, unread-bit waiver, or timing exception. A causal test proves an unused anchor and parent are removed while a real ICG enable remains connected. Nine reset reach/pruning tests pass. qual2 full source bind is live under ep6 codex-s81-reset-1020; no physical route was started.

Production geometry remains held: RETICLE_MARGIN500 caps width32000. A raw32659.7 expansion would fail this guard and is not an approved margin change. Existing rf3 frame heights3369.6/3672 and actual slice outlines exceed the old capacity vehicle reservations. SVCPLAN owns the legal-frame and static-calendar alternatives; the exact112 inventory remains a capacity/model vehicle, not a manufactured die plan.
