# HBM die clock/reset inventory rejection

Current v13 is not source-bound native clock/reset feasibility evidence. This read-only audit freezes origin/main `bb9fa3a2766ef179666bb01892f7c0088d3911a1` and exact producer metadata; it performs no new heavy job, source edit, route, or clock/reset delivery qualification.

| Interface | Exact inventory mismatch | Feasibility status |
|---|---|---|
| v13 | 5,773 children/clock sinks; 536 guessed no-LEF centres, comprising512 collapsed SM tiles and24 other centres | Input-only geometry; no taps, insertion, skew or reset driver inventory |
| SM | Each old tile clock becomes OWN_RAW plus12 assigned child RAW clocks and12 real gated outputs | Baseline512 tiles would request6,656 RAW inputs, scoped delta+6,144; static actual TT/SS gating fails. New local-ICG structural variant remains unqualified |
| Native VM/CDC | 128 leaves request256 C/V pins; source graph has16 C labels and1 global V. Owned96 subset uses12 C labels;32 diagnostic leaves add4 | Quarter software connections do not prove per-leaf delivered roots.32 station roots are separately exposed; shared asynchronous reset release remains unbound |
| IDX | 2,160 active owned pins:16 engine+16 meta+16 tail+64 chunk+2,048 hslice.112 glue roots contain566,992 generic FF | Missing native placement/driver/phase/source-slew binding. New-ready leaf adds1 ACK FF each; old CLOSED15,334-sink leaf is a lower bound |
| HC | Historical594declared−12pruned=582; proven source668−12=656. Latest source672−12=660, hardlink proof pending | v13 has4 HC reservations, no placed HC masters. Latest refreshed slot672/660 API and13 source hashes match; legacy594 arithmetic subfield remains historical |
| DMA front/bank |32 lane roots and4 control roots; new bank9 has4 source roots plusVM root per master. Fused main10 actual root15,497 FF | No new physical source/reset/pin grant; quarter/shared legacy roots cannot replace owned interfaces |
| Quant/SFU | Current quant splits payload/finalization clocks; SFU contains16 body roots and16 mapper roots per quarter plus4 proposed control roots | Software cclk ties and pending variants do not establish physical roots or reset delivery |

`receipt.json` retains detailed counts, periods, reset interfaces, corner reference values and evidence limits. `binding.json` binds each frozen source/evidence snapshot by SHA256. `sources/` contains actual producer inventories and source-bound receipts; old v13 inputs are compressed without changes. Counts were checked against actual records:5773 old instances,512 collapsed tiles,128 CDC leaves/256 distinct requests,112 IDX glue roots with566992 FF, and HC668 declared in completed source receipt.

True C periods are833.333 or the actual source-rounded833.33325 ps; V is1111.111 ps. HC kit route770 and signoff833.333 are distinct. Existing historical die policy also declares HBM1024 and link833.333 ps; this audit does not alias them to C/V or grant phase correlation. Functional common-phase or phase-offset benches are not physical driver evidence.

Accepted clock insertion references remain per exact pin, variant and corner. For SM, OWN cut_2 R is TT149.2/FF116.9/SS207 ps; actual child clk values and zero-source-slew context are retained. Actual real-ICG gating receipt `fc7529c51` demonstrates the static negative while retaining nonzero GCLK slew/conditional childR calibration gaps. Quant/SFU and VM published view bindings remain in frozen producer packets; absent SS or source slews remain unknown. Producer-reported DMA ctrl6 maximum197 has unitsps, notns. No zero-R or sibling variant substitution is allowed.

Reset state is separate from ordinary clock delivery: IDX has one global rst_n and local relay outputs/ACK; native CDC uses shared direct asynchronous reset; DMA bank queues/control lack domain-specific release; HC new own logic uses local relay; SM preserves parent reset bit3→cut3. Each needs an actual assertion source, reset-driver/load/slew network, per-domain release owner and timing, recovery/removal checks, and running/stopped-clock drain/lease semantics. No reset false path or unbound driver grant is implied.

The next independent action is to expand admitted native instance and pin bindings into a flattened geometry/load/reach inventory, with every RAW/GCLK/ref/reset connection and source-context provenance, before submitting a die CTS case. There is no new global die root total: native requests overlap hierarchy scopes, and unresolved replacements have not been adopted.

Latest HC update is preserved in `hc_slot_request_latest.json`:13 exact source SHA paths match the current a0 source. Private CTS physical pin demand and six raw TT/FF/SS clock metric packets are included, keeping actual boundary and all-flop metrics distinct. Separate160 window entries are demand, not a total added to collector660. Full native hardlink proof remains pending at the supplied snapshot.
