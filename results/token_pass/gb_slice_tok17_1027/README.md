# TOK-ALL-17 GB sub-lane: u_s_0S return relay + landing, and the six-frame slice composition (Tue Oct 27 06:42:55 PM PDT 2026)

Branch claude/tok17-gb-1027 (off claude/tok16-gb-1027@8606da96fe). Raw data: intel1 /srv/opentallas-scratch2/claude/tok17-gb.

## 1. Return relay + landing, all six u_s_0S a_proj frames (cone/): POSITIVE FAIL (real landing epoch assertion)

Vehicle (tools/s81_dv/tokfunc/die_ret_cone.py, tb_ret_cone.sv, run_ret_cone.sh):
- Extracted verbatim from die_b178.v (sha a5778b98...): 1,996 instances.
  - 6 hop-0 ICGs; 388 dsfd_dvrlyh half-cycle stations (0L01 39, 0L02 75, 0L03 66, 0R01 48, 0R02 71, 0R03 89).
  - 6 dsfd_dvland_70 at the die K straps (2,1,2,2,1,2).
  - The full die reset wavefront cone: 1,690 dsfd_rly_1 stations back to die rst_n.
- Last-hop flight F comes from the GEN land plan (frame_chain_reset_v2.lane_flight rule): F = 1,0,1,1,0,1 at both tt and ff.
- All root clocks are uniform (one phase).
- Tagged words are injected at each frame ret pin. The bench checks order, content, constant latency, and the landing fault.

Result at the die K straps (CHECKED, sim logs cone/run_tt.rc.txt, run_ff.rc.txt):
- Words arrive at 44/44 per lane, in order, content exact, at one constant latency per lane.
- ret pin -> landed o latencies: 0L01 25, 0L02 42, 0L03 38, 0R01 29, 0R02 40, 0R03 50 cycles.
- BUT the real ot_s81_land epoch assertion fires on 6/6 lanes, right after warm-up (0L01 at edge 100).

Root cause (CHECKED, trace cone/trace_lane0_die_k.txt; depths cone/reset_depths.txt):
- The landing contract has E = K + R0 - G. The K straps were chosen with R0 = G. The bind transport note says so: "E ~ K (R0 = G)".
- In the real die reset cone, the landing rs is 1 or 2 stations SHALLOWER than the hop-0 gate ENA:
  - 0L01 -1, 0L02 -1, 0L03 -2, 0R01 -2, 0R02 -1, 0R03 -1.
  - The die comment says "landing rs 1 edges after the gate".
- So R0 = G - 2..3 edges (0L01: rs released at 96, gate GCLK first edge at 98) and E_eff = K - 2..3, which is 0 or less.
- The reader is ahead of the writer. It reads the slot one ring lap (D = 4) stale, so the data still comes through in order with correct content, but the epoch check fails.
- The latencies above therefore include that lap: they are NOT the contract latencies.

What-if, K strap raised (CHECKED, cone/whatif_k_plus*.rc.txt; a bench edit, not a die change):
- K+1: still faults on 0L03 and 0R01, the lanes whose rs is 2 stations shallower.
- K+2 (K = 4,3,4,4,3,4): PASS on all 6 lanes, land_fault 0. Contract latencies: 0L01 23, 0L02 40, 0L03 36, 0R01 27, 0R02 38, 0R03 48 cycles.
- K+3: PASS, +1 cycle on every lane.
- Fix options for the S81 die owner: K strap +2 on the u_s_0S return lanes (within KW = 3, at most 7), or rs-station padding to R0 = G.
  - Either one needs the die STA window recheck: with K+2 the window is E = 2, D = 4, dL = 1.5T.

Controls:
- OT_DVRLYH_MUT (non-inverting forward) changes every latency to a full cycle per station (45..95): CAUGHT as a latency change.
- OT_S81_LAND_MUT_SEL shifts every latency by -1: CAUGHT as a latency change.
- OT_S81_RLY_RSMUT has no effect at this scope (equivalent).
- These controls ran against the faulting positive. They count only as latency sensitivity, not as qualification.

## 2. Six-frame slice composition (tb_dense_gb_slice.sv, tok17_gb.sh, check_gb_slice.py): RUNNING / not collected

Setup:
- XS4 -> W chain 0L01 (h10_x) -xo-> 0L02 (h9_x) -xo-> 0L03 (h9_nx), and the E chain 0R01 -> 0R02 -> 0R03.
- Each ret -> the die return cone above (at the die K) -> capc5r_e6. +byp=1 feeds ret directly to CAP (the tok16 form).
- Runs: landed, bypass, input mutant, swapped-image control (0L02 <-> 0R02 images).

Run 1 (slice_run1_noimg) INVALID: 0 returns on every frame. Two bench-assembly causes:
- (a) The merged image dir lacked the XS pq_phase0/pq_stream0-3 ROM images, so the XS stream was empty.
- (b) The h9 plan-kit functional copy carried no ROM INSTANCE identities (168 ROM lookups read " _c*" names) and kit-stripped hard params.
  - This is the h10 1450 + tok16 bug class, now on col_h9 too.

Fix (0 cycles; same tools and same rules as h10):
- gb_image_identity.py: 168 identities restored from vg/col_h9_l4_lp.sv.
- Then gb_hard_params.py: 36 calls restored (16 qxpq_w10 elements, 16 cfg7_seq, 4 cfg7_seq_bfp).
- Output: results/token_pass/gb_hard_params_tok17/col_h9_plan_image_bound_hp.sv; new manifest asbuilt_b178_gb_image_candidate_tok17.json.
- Fresh extraction of all 4 masters PASS; the schedules equal tok16 apart from provenance.
- The common files are now asserted identical across the 6 frames, and they include the pq images.

Run 2 LIVE: ot-run unit oth-ubuntu-3552087-1793151637, out /srv/opentallas-scratch2/claude/tok17-gb/slice, build ~30 min.
- Collect: python3 tools/s81_dv/tokfunc/check_gb_slice.py --vec-root <out>/vec --run <out> (it writes check.json).
- Expect land_fault=1 in the landed run (section 1). Judge the data and captures separately.

Bounds:
- One uniform clock phase.
- The x lanes XS->0L01/0R01 and the x relay lanes 0L02->0L03 / 0R02->0R03 are not simulated.
- Native provider not qualified (OT_XS_GB_PROVIDER_UNDER_TEST=1).
