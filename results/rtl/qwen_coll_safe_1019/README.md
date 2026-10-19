# SAFE collective structural candidate (2026-10-19)

This is a candidate, with no REVIEW.json or submit authorization. Default SAFE=0 behavior is retained. SAFE=1 replaces delay chains of depth >=3 with exact stationary rings, lands core/link tokens, partitions reset copies, removes unobserved metadata resets, and captures PHY-up. PHY-up fault observation adds one diagnostic edge. No throughput/data calendar stages are added in the recorded phase-0 production test: LU=53, LS=378. The generated physical wrapper adds two startup reset guard edges. A separate real 0.2T core/link phase production test FAILED (phase1/): AR2048/argmax48 mismatches, all8 faulted; SAFE0 comparator completed with identical failure (phase_baseline/); inherited integration phase contract remains a release blocker. Candidate is not mesochronous qualified; the previous duty50 harness ignored phi and has been corrected.

Evidence:

- ring/: sixteen depths (0..378), 4096 edges and repeated reset, golden shift equivalence; early-ring mutant caught.
- r3/: SAFE S1 L378, phase0/1, 240 words per face; six behavioral mutants caught (early RX, CDC, PHY, bank, ring, unlanded).
- phy_up/: normal legacy fault edge28 versus captured SAFE fault edge29, reset/epoch recovery; missing-fault mutant caught.
- hard1_steady/: current source phase0 consecutive2x256 (4096outputs) and2x256+argmax (4160outputs) PASS, exactspans1537/1545, faults0/noP/Roverlap. Independent phase1 blocker remains.
- hard1/: exact fixed five physical wrappers bound into all eight production parents, guarded dv2f18dh2 profile; AR2048+argmax64 outputs PASS phase0, no faults. This proves wrapper binding semantics, not physical closure.
- integration/: eight production parents, all five actual face profiles, six/five gearbox at 50% duty and actual dv2f18dh2 forwarded lanes. AR256=2048 outputs, argmax1=64 outputs, bit exact and fault-free. Source/executable hashes are recorded.
- dv2f18dh2_coll_lane_latency.json: immutable live-run latency fixture. Live die run untouched.

The immutable qfd_static_ch546 child view remains valid under current HANDOFF section2 policy (TT setup+46.88ps, FF hold+9.11ps, both>=0). SS -225.67ps is sensitivity only; no redesign is justified solely by SS.

## Scoped owner placement waiver

ROOT explicitly accepted only the RX MY child origin X129.600 ->129.624um, Y302.4um, as a candidate track legalization. All other origins stay on43.2um lattice. Child RTL and view bytes are verified unchanged against17ac09ab3. LEF SHA256:59a7b6d9f08d212b9b1c5184afb2442f9faed034f8dc6f2d63af40cede3d202a. Transform is MY:(x,y)->(W-x,y), then translate. Nominal origin has3/1115 pins offtrack by24nm and inaccessible2 signal/4 clock shapes. Shifted origin has0 offtrack and all1114 signal,4 clock,86 PG shapes accessible on full-width preferred tracks. See rx_mirror_track_proof.json and reproducible proof script. This proof is geometric; actual pin access/DRC/native clock proof and final visual approval remain pending. No extra relay is added solely for24nm.

## Critical physical checklist before release

1. Calendar: S1 component and phase0 production/steady witnesses PASS; real0.2T production FAIL identically with SAFE0/1. Independent root-phase contract is a release blocker.
2. Input/pin capture: TOK_REG=1 and captured PHY-up (+1 diagnostic edge); actual calibrated pin-to-flop reach and DRC remain open after CTS failure.
3. Storage: N>=3 delay chains become stationary rings with<=16-bit select banks; repeated-reset equivalence and early/unlanded mutants PASS. Physical hold remains open.
4. Reset: local same-depth copies, reset-free metadata, boundary guard+2. Synthesized raw rst_n has1 sink; no extra normal calendar edge. Post-route/native reset reach remains owed.
5. Clock: real FAIL. TT cal_ck38.9ps/cal_lck0.6ps pin spread pass; codec0 spread450.8ps fails80ps. No FF verdict. New TX/RX/control ownership model in regional_model/ awaits ROOT contract choice; no placement/CTS knob retry.
6. Geometry:950.4x561.6um, aspect1.692, six children, full-width std band y475.2..561.6. Floorplan PNG inspected. Fill42%; W1157/E1261 pins over513.6um (92% face span), S76/N2. Scoped RX24nm track waiver is geometric only; actual PG/OBS pin access/DRC still owed.
7. Timing: IO/internal hold0.03ns, no delay masks. CTS failed before calibrated TT setup/FF hold and GRT could complete; no signoff claim.
8. Integration: all five fixed wrapper profiles pass four phase0 production workloads; physical production parent is not built/qualified. S1 gate_result/PNG preserve FAIL. Other four profile specs remain DRAFT. No next S1 gate before ROOT selects and qualifies the crossing contract; no REVIEW.json/submit.

qfd_coll_bank137 view dependency was restored unchanged from commit3dbaaf169 because absent at the adopted branch base. Clock-tool main synchronization is commit7a820e1ee, separable from this RTL candidate.

## Core physical dependency candidates

qfd_io_collective_safe_lattice keeps s4 rawSRAM origins and diagnoses R0 folds at43.2 grid. Its separate gate is a comparison, not the final all-grid candidate. qfd_io_collective_safe_r0 compresses the width to734.4um and expands height to1036.8um, puts all8folds+9rawSRAMs R0 on43.2um origins, and puts rawclock rootpins beside each owning row onW/E. Full-width softband y950.4..1036.8; all macro channels>=20um. core_r0_grid_proof.json checks immutable view hashes, all pin tracks, and nominal raw-clock Manhattan reach<=405um. Actual pin placement, routes, reset census, TT/FF and native spread remain gate obligations. This is not the production physical view: closed five-profile faces and core must still be integrated with the paid relay calendar.

Comparison core gate terminal FAIL: TT clk actual boundary pin-flop spread451.7ps,6628/10196 sinks (>80ps), noFF. Source-bound gate_result/floorplanPNG and core_lattice_gate_failure/cts.log preserved. Floorplan visually inspected; inherited rawSRAM origins remain comparison-only. Distinct full-R0 gate remains active; no knob retry.
