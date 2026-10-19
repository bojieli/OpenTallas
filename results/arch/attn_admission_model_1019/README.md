# ATTN admission structural model: HOLD before source

Read-only analytical successor to exact placed graph **548178937**, source **ac6af21580867b0e1224c7cf7e6476309d5b036cd2ba558ad5014737fbfeddde**, placement43622ef26. No RTL, EDA, placement, clock change, gate or submission. The original TT−569.32ps /1294.07ps arrival remains FAIL. Individual transparent driver→endpoint reach328.171um passes;635 accumulated stage-wire sums are timing diagnostics only.

## Exact useful cuts and the missing cohort

The original critical consumer is `u_attn_root.ctx[10]` (`ahs[33]`), loaded with position+1 only on request_valid&&request_ready. Position+1 already runs in parallel. Its late enable traverses landed record validation, sticky fault and ready/control logic. Removing a reserved-bit/identity check, or replacing an operand with a constant, changes live admission semantics.

`frontiers.json` traces EVERY native data input recursively, stopping only at FF outputs and the stated cut. It does not stop at arbitrary depth or cap the list. The graph has no inferred Boolean constant assumptions. Results:

| Native consumer | Stopped cut | Other real FF operands | Comb cells before stop |
|---|---|---:|---:|
| c2168/Y | none |516 plain FF |672 |
| c2343/Y |c2168/Y |34 resettable+36 plain FF |54 |
| cpo216_ff/D |c2343/Y |60 resettable+65 plain FF |89 |

Consequently a scalar register after c2168 or c2343 is not a complete cut. At the second cut,70 other original-edge operands must be evaluated or carried in the correct cohort. At final capture125 other FF operands remain. They include useful root boot/running/ready, held authority/position, sticky/local/service faults and old context state; the native frontier alone does not establish source-level semantic ownership. Old context is feedback, so blindly delaying every frontier FF would select stale state and can corrupt consecutive admissions. Copies must retain live-state ownership while command-specific operands carry their selected edge. An exact source predicate-to-frontier map and write/hold/reset transition table are mandatory before implementation.

A two-cut partition at c2168/Y then c2343/Y gives critical-path-only surrogate segment arrivals515.38,401.94,578.87ps, adding the original101.06ps CQ to the latter segments. These are useful sizing targets, **not closure estimates**: changed FF load/slew/placement, capture setup, and ALL side-cone arrivals are absent. The third surrogate has only21.13ps to the600ps design-depth target. The original c2343 output already arrives816.26ps, so registering only the complete request/accept there leaves upstream timing unsafe.

## Reviewable alternatives

1. **One admission-bundle stage (217FF): reject as a sufficient repair.** It carries216 metadata bits and valid, costing at least63.36468um², but leaves the measured816.26ps qualification upstream. It also misses Q and public programme alignment.
2. **Two paid predicate/cohort stages: bounded candidate, HOLD source.** First partition record legal/direction/expected-identity/time predicates and all original-edge fault snapshots; second combine those predicates with the selected command, root acceptance conditions and local copied enables. Then update root context/calendar/targets in a third segment. Full70/125 side-frontier semantic maps are prerequisites. Group equality and zero checks remain real; local copies require identical source/clock/reset. No sufficient full-cone candidate has yet been derived, so no claimed total FF/comb/clock or build admission is issued.

For alternative2, a deliberately explicit separate-storage transport model carries two stages of216-bit request metadata+valid, the full518-bit Q bundle `{data[511:0],beat[4:0],valid}`, and the full537-bit exported prg word (535 data bits+2 valids). This costs **2544FF /2544 clock pins /742.53024um² master-box area**, comprising2536 plain and8 resettable-valid FF. It is a **transport floor for this unshared architecture**, not a minimum across all architectures or a full design price. Sharing Q/prg storage may lower it only after exact source-cohort proof. Predicate FFs, hold muxes, clock tree, reset landing/copies, fanout copies and new wire area are extra. No buffer chain counts as a kept FF copy. All-driver fanout<=32 must be recomputed;8 new reset loads do not automatically fit their existing ancestor. Clock/reset capacitance and PG are unpriced and therefore block building. MAC work and external payload widths are unchanged; internal staged Q bandwidth is518bits/edge and prg537bits/edge. The two-entry delays are below the >=3-stage ring/SRAM rule; a longer fallback must model actual ring storage rather than growing chains.

## Exact calendar obligations

Let E be the **original root acceptance edge**, and L be the new paid admission latency. This is a static schedule change, with no runtime stall or credit.

| Consumer/observation | Required edge relationship |
|---|---|
| Command identity, position, calendar, capability |All belong to E, accepted at E+L; no later programme value substitution |
| Root request_ready |Original !running&&boot_count==80 at E must be recorded/justified; delayed ready cannot silently change acceptance |
| start_qk/running/age0 and root ctx/ep/layer/cal |Shift together by L |
| Root Q-window |Every original q_valid/beat/data shifts L; window is exact, not a ready handshake |
| Q beat0..31 |Source samples beat0 at E+2; new samples E+L+2 through E+L+33 |
| start_pv/PV consumer/context |Relative calendar and PV_LEAD unchanged; absolute start moves L, all producer/read/write slots follow |
| CAL_PIPE cp_pv/cp_last/cp_cal |Compare against same selected delayed calendar cohort; retain moved-calendar causal failure |
| Results, result_reserved/beat/identity/done |Controller tx_first/end and external result/slot schedule move L; rx_cmd remains tied to original RX arrival |
| RESULT beats0..31, done, STATUS |At controller ages tx_first+L..+L+31, +L+32, +L+33; busy ends old end+L |
| TX launch, prg, ahs/pvst/pvfst/acal/arh outputs |Recompute actual source+existing launch+die relay ages; full prg delay alone is not proof that external consumers align |
| Continuous fault, STATUS, host commit/admission |Retain immediate original fault observation unless an explicit new contract is approved; reprice health cutoff separately |

The original controller faults on request_valid&&!request_ready; delayed request consumption must preserve that original-edge violation. Original root local checks (capability,position,lead range,calendar movement) still execute for the selected command. Delayed valid must not lose a bad-record rejection or allow a newer fault to disappear. Whether a later continuous fault cancels an already selected command is a separate transition/retirement contract: an unconditional sampled-only fault loses live veto, while an unconditional live veto can change faulty trace timing. Resolve this explicitly; do not invent ready-based backpressure or waive the original STATUS/TX/RX timing mutants. Reset must clear every pipeline-valid and preserve the exact existing sampled/asynchronous reset ancestry, with2-stage landing at faces; arbitrary POR/warm transitions and first-use qualification remain necessary.

For a serial dependent token containing N actual ATTN admissions, delta is L*N edges (L*N/1.2ns). Conditional N=32,L=2 gives64edges/53.333ns. Against the existing per-layer-retirement scenario257280edges this is an additional0.024869% rate loss; it is **not a measured token rate or proof of the actual admission count**. Four independent users incur256 added work edges in that scenario; overlap means wall-time/throughput cannot be derived by adding them. The no-overlap service initiation interval grows by L. Actual SU/MU compiler calendars, boot images, lifetimes, occupancy and production-shape throughput remain required. No existing golden,deadline,RT/DQ bound or source schedule is silently edited.

The inherited521 unused inputs and107 constant-output cones remain an exact ABI/source ledger obligation. This model neither registers invented ties nor deletes production ports. Existing native clock matching, slew/recovery/hold, PG pin contacts and source-level alternative proofs remain OPEN. Run `python3 model.py` locally for this small read-only accounting; it rewrites only model.json/frontiers.json from the pinned committed graph. Source creation needs a fresh owner with the full side-predicate/feedback map and explicit model admission.
