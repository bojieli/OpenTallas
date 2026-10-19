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

1. Calendar exactness: RTL witnesses above; extra phase production test pending.
2. Input/pin capture: TOK_REG=1, PHY-up captured; actual pin-to-flop reach must pass gate.
3. Storage: long chains replaced with <=16-bit bank stationary rings; physical feedback/hold must pass gate.
4. Reset: kept same-depth copies, reset-free unobserved metadata, generated two-edge boundary guard; synthesized census pending.
5. Clock: scalar regional roots and explicit core/link landings; native TT/FF spread/insertion pending.
6. Geometry:950.4x561.6um, six children, full-width standard-cell band y475.2..561.6; actual density/pins/reach/layout pending. Narrow RX waiver above.
7. Timing: hold constraints0.03ns for IO/internal, no delay masks; TT setup and FF hold must be>=0.
8. Integration: production RTL passes; source-bound production physical parent rekit and final visual acceptance remain open. Only S1 kit is gate-ready. Other profile specs are explicitly DRAFT with no independent wrapper bench.

qfd_coll_bank137 view dependency was restored unchanged from commit3dbaaf169 because absent at the adopted branch base. Clock-tool main synchronization is commit7a820e1ee, separable from this RTL candidate.

## Core physical dependency candidates

qfd_io_collective_safe_lattice keeps s4 rawSRAM origins and diagnoses R0 folds at43.2 grid. Its separate gate is a comparison, not the final all-grid candidate. qfd_io_collective_safe_r0 compresses the width to734.4um and expands height to1036.8um, puts all8folds+9rawSRAMs R0 on43.2um origins, and puts rawclock rootpins beside each owning row onW/E. Full-width softband y950.4..1036.8; all macro channels>=20um. core_r0_grid_proof.json checks immutable view hashes, all pin tracks, and nominal raw-clock Manhattan reach<=405um. Actual pin placement, routes, reset census, TT/FF and native spread remain gate obligations. This is not the production physical view: closed five-profile faces and core must still be integrated with the paid relay calendar.
