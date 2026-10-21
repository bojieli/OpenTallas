# Typed staged finalization: design for ROOT review (NOT IMPLEMENTED)

This proposes ONE source-owned cooperation path for the observed protected-spine/LRT conflict. No source helper changes, EDA, retry, policy/SDC/target change or API promotion occur in this packet. Existing engine aab59f9 remains canonical; any future approved phase addition would have a new explicit source hash and publisher-owned qualification.

## Existing typed facilities and missing phase

`ot_sp_buf(name,x,y,innet,master)` already accepts a concrete buffer master, uses that master's width, places on the builder's free legal row sites, updates occupancy and appends created buffers to the builder ledger. `ot_sp_checkpoint/ot_sp_restore` already preserve created instances/count/pad state/occupied sites. `ot_sp_bind_pg` is a typed PG phase. None is a supported record-tap finalization phase, and none authorizes arbitrary callbacks. We propose a fixed, narrow record-tap phase before final protection, reusing these allocator/bookkeeping facilities and the existing LRT measurement/target algorithm.

## Exact current tap/record ownership

The supported initial record kind is `hybrid_raw` only. Actual fixture plan is `record_tap_plan.json`: one instance u_hr, exact master ot_qfd_tt_ctlm_static_hr, owner ck_hr, raw ck_pm0/ck_pm1, reference ck_head. All three actual Liberty clock contacts were admitted from that same declared HR root before CTS. Counts remain core11940/HR5188.

Targets are NOT new knobs. Derive with existing `clock_entry_constraints.landed_tap_targets` from the child's CLOSED record and insertion measurements, preserving its rounding:

| Raw pin | Reference | TT ps | FF ps | SS ps |
|---|---|---:|---:|---:|
| ck_pm0 | ck_head | 287.9 | 232.0 | 379.8 |
| ck_pm1 | ck_head | 288.5 | 232.5 | 380.4 |

Source view: physical/ref_tile/qfd_tt_head_static_h16c/views/ot_qfd_tt_ctlm_static_hr. Signed record: results/rtl/ref_tile/qfd_tt_head_static_h16c/qfd_tt_head_static_h16c-h16c-ae6b0c59a/signoff.sdc SHA366b2b1bcadd6412d85f2f948833026d29bfcb43d5efde5b1e0fb0946d47d530; verdict results/closure_loop/qfd_tt_head_static_h16c-h16c-ae6b0c59a/verdict.json; insertion SHAffe8b84a9d59ae588ddd62a1f04c5158facfd90a455fcc77a85fe38f670a4277. Full verdict/hash set is in the JSON. These are the legacy fixture's exact records, **not H16ZA targets**. H16ZA's49-port/one-clock source must never inherit ck_pm0/ck_pm1 or this old child identity.

## Narrow data interface

Generation of an opted-in domain-spine case with existing hybrid raw targets emits one internal typed plan `ot_sp_record_taps_v1`: version, exact instance/master/raw/ref, same-declared-root ownership requirement, immutable record/verdict/insertion/view hashes and targets for all corners. No Tcl script, procedure name, arbitrary callback, file override, free target or timing relationship is accepted. Existing source-manifest closure includes all plan input bytes and the fixed worker helper. No user hook is added.

The plan is derived from the existing source contract, not reconstructed from Liberty absence. Runtime admission binds every raw/ref terminal to its actual pre-CTS root; freezes that owner ledger before tree mutation; refuses different owners, duplicate targets, nonclock contacts, master/instance/record mismatch or unrepresented targets. Current fixture's owner is exactly ck_hr. Other models/cross-root tap relationships remain unsupported and fail closed until separately source-owned; no inference of related phase.

## Staged execution and final ownership

1. Production root/Liberty/clock-entry admission runs unchanged. Register all exact target/ref terminals before tree construction and preserve their source owner ledger. Reject malformed/missing/wrong-owner plans before mutation.
2. For each existing root, execute the **unchanged canonical balancing algorithm** and choose its best checkpoint exactly as today. Complete its actual parasitic estimation and balance iterations first. Do not measure or tune the record taps against a pre-balance reference. All participants of a tap must belong to this completed root; other domains are untouched.
3. Immediately before the current per-root final-protection phase, invoke a FIXED typed record-tap worker for this root's registered plan. The root's cells/nets are still builder-owned and not protected yet, so no protected object is unlocked. Earlier completed domains keep their protection. There is no general phase callback.
4. Reuse existing LRT propagated-clock scene/corner discovery, raw-minus-ref measurement, target values, BUFx4 default, limit64, minimum added-delay check and nearest-target overshoot rule. Insert one buffer at a time and re-estimate after actual placement. Use `ot_sp_buf` with the concrete approved LRT buffer master to allocate a free legal row footprint and claim it in the SAME builder occupancy ledger; do not stack tap buffers at the macro pin. Validate the master has the expected single clock-buffer input/output and positive footprint. This typed path changes placement ownership only; it does not add a register/cycle or change target/measurement definitions.
5. For overshoot backout, save a typed leaf checkpoint containing the raw terminal's previous net plus the existing allocator checkpoint. Restore the raw endpoint first, then use the existing checkpoint removal/bookkeeping path to remove the last tap cell/net and reclaim occupancy. Preserve other terminal connectivity, canonical pad state and buffer-master bookkeeping. No canonical balance pass runs after taps (it would erase the required record offset).
6. Existing PG binding applies to every new tap cell before it is protected/measured where PG-strict requires it. Adopt all tap-created buffers/nets into the builder's final ownership list. Apply the usual final do-not-touch protection to the complete topology, including tap cells/nets, then existing placement legality/checks. No global or temporary unprotect is used.
7. The outer LRT wrapper must verify a **consumed completion receipt**, one per declared source target, and remeasure using the existing function after full CTS. It must refuse missing/duplicate/wrong-instance/wrong-owner completion or altered topology/protection. This is evidence that LRT ran in the typed builder phase, not an LRT skip. It must not insert the same chain twice. With no staged plan, the old LRT wrapper executes byte-for-byte as before.
8. Existing boundary clock_entry.sdc reapplication, RAW_PIN residual/clock-entry checks, reach/spread/STA/PG/final-write policies and physical admission remain unchanged. A source/helper failure leaves the case failed; it does not fall back to ideal clocks, target changes, another root or legacy unprotected rewiring.

## Default identity and focused refusal review matrix

These are REQUIRED proposed checks, not claimed results; implementation and ROOT approval must precede execution.

* No domain-spine plan: old generated hooks/SDC/dependency closure and LRT execution path unchanged. Canonical tree/pad/placement traces, inserted cells/nets and measured balance arrivals must match old engine on the same default fixture. Do not relabel source-file hash identity as behavior identity after adding a phase.
* Domain spine without raw targets: same current balancing, per-root protection order and output topology. No record worker/protocol activation.
* Exact current hybrid_raw fixture: target values/hash inputs unchanged; all actual source contacts retain root ownership; actual post-tap targets checked, every final cell/net protected, all original physical checks pass before any promotion.
* Wrong raw owner, wrong ref owner, cross-root raw/ref, duplicate target, nonclock target or unknown root: refuse before constructing any tree/tap mutation.
* Changed signoff/insertion/verdict/LEF/master/instance/target or missing source bytes: refuse generation/admission. Unknown plan version/model/callback-shaped field: refuse.
* Premature tap before balancing, attempt on already protected net, attempt after finalized root, endpoint not in current root ledger, second consumption or missing completion: refuse, no unprotect/fallback.
* Allocation/backout failure, no propagated arrival, unsupported corner, no positive delay growth, limit exhaustion, unresolved illegal placement or PG binding failure: preserve failure and protections; no threshold relaxation or retry.
* Tamper any other spine leaf connection, raw ref connection, final protection or completion receipt: existing post-check plus strict typed ledger must refuse.

## Remaining review decisions

ROOT must accept the fixed phase placement and exact data contract before implementation. The source changes would be limited to the engine's typed finalization call, typed LRT worker/consumption checks and generated source-bound plan/dependencies; no FRAME timing-basis file, balancing equations, wrappers' semantic order or generic pre_cts_extra policy changes. No EDA launch is requested in this design packet.
