# OPUS-FIX-S81-SVC-R8 handoff (started 11-21 10:3x PST; successor of OPUS-FIX-S81-SVC-R7). Nothing signed or exported yet.
Work dir epyc10 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r8 (scripts also in that dir).

## LIVE (re-arm waiters first)
- chainJ7 epyc10 PID 1506228 (chainJ7.sh, log chainJ7.log): bind_j7.sh (elab -> strict bind --all-gaps -> LATCHECK, treeJ7) -> STATE;
  green -> prep_j7.py att + rest kit preps in parallel (kit_att/, kit_rest/; KSTATE_att, KSTATE_rest; config.mk diff gate vs wave_ref).
- H8 proof chains (COORD: keep as type_split-fix proof only): chain10i epyc10 PID 224179 (R7 bind_hi4x), chain_rest8i epyc8 PID 2379962.
- J8 generator trial: epyc10 j8/job_g4.sh (gen16yc4.py = R7 gen16yc3 + keepouts for FT station blocks + landing band rects) on hi rs t1, t3; out j8/out_g4.

## Ruling 1 (hi4 on J7, deadline bind + both preps clean ~19:00 PST, else J8)
- j7pre/plan_pre.json = gen_hi4_j7pre.py on J7 v5 (03c17773): J7 hi4 + (H8 r5b -> preview) 3-way + x_epoch compose (replay reproduces H8 E exactly;
  on J7 only band monitor_0 moves with J7 collector child) + ATTCUT renames + ub tap fix (32/32).
- treeJ7 = candJ7c hardlink copy (mk_tree_j7.sh, native_bind/out excluded) + overlays: svc_rs att/mem_ar/rs.sv from 9bd318e90366 (R5 tree; J7 svc RTL == H8 HEAD),
  s81_svc_r5_hi4_sources/*.sv, SRAM bb.v, bind/inputs/map_census_r5.json. Manifest treeJ7/asbuilt_r8_hi4_split_j7.json (mk_manifest.py: candJ7c + 3-way hi4 rows).
- Split: spec_j7.json, split_j7.sh (band-test tools with R7 core-tap patch) -> treeJ7/physical/die_plan/s81/split_hi4x (SPLIT_RC 0).
- Trial: PLAN split plan_c BASE v5 onto J7 v6: BUILD_OK.
- Package for R4 after green: PLAN line + manifest ops (asbuilt_vN keys vs candJ7c) + FILE lines (split_hi4x dir, RTL overlays, map, SRAM bb).
## Ruling 2: type_split core-tap fix: FLOW-STRIPBODY-1121 commits (posted 10:5x); if not on main by 15:00 PST, R8 pushes R7 patch
  (epyc10 opus-fix-s81-svc-r7/repo diff, base 197076cf03) via ot-push-main.
## Ruling 3: svc_s1 GEN NOT in J7 v6 steps -> asked R4 to confirm for candJ7d.
## Ruling 4/5 (J8): lo = single types (no split); census of lo real failures still to do (all 8 were STRUCT-STOP cancelled at place 11-21 02:0x).
  hi: keep y cut; t1/t3 fix trial = keepouts (gen16yc4).

## UPDATE 11-21 12:4x PST (newest)
- H8 chains ended: bind/LATCHECK green; both preps pass kit_rtl (core-tap fix proven) and FAIL generate "plan invalid" 6 ports = type_split
  defects A (offset piece N/S bus windows in parent frame) + B (FT cut port windows != slot ends, overlap L* cut ports). Reported to STRIPBODY.
- Lever 8: same spec through STRIPBODY lc splitter == my split (only out-dir relative paths differ). Use their splitter going forward.
- J7: chainJ7 (PID 1506228, pre-fix plan_c, evidence only; its preps will fail generate). chainJ7b PID 263082 = plan_c_fx.json
  (fix_cut.py post-pass: 0 mismatches, 0 cut-line overlaps) -> bind_j7fx.sh (bind_out_fx) -> STATE_FX -> prep_j7fx.py kitfx_att/kitfx_rest
  -> KSTATE_FX_*. On both PREP_OK: python3 -I mk_pkg.py -> pkg/hi4_j7.list (PLAN plan_c_fx BASE v5, mo_svc_hi4_split_j7.json, FILE lines,
  HOOK hook_sidecar.sh 3-way sidecar merge) -> post to R4 before 19:00 PST, else hi4 -> J8.
- J8 hi: all 7 compose. t3: out_g5c (R8_KEEP [[0,1]] R8_BANDBOX attn_i2,attn_i1). t1: out_g6f (gen16yc6, R8_KEEP [[1,1]] R8_FTKEEP ft0,ft1
  R8_DY 260 BANDBOX attn_i2,attn_i1). Others per R7 (gen16yc3). Next: combined run, J8 splits, fix_cut, bind.
- lo: wave attempts only ever failed die-wide kit_rtl (leaf__t12 reset reach) then STRUCT-STOP; J8 single types + struct-release.
- svc_s1 GEN (REACH>405) not seen in J7 v6 steps; asked R4 (no reply yet).

### Codex 14:15–14:45 PST takeover

- ACK waiter IDs 15567adceb7e and 6a8f05a7930b. Epyc10 private `prep_j7fx_rt.py` preserves the existing factory and validates published tool export a9ed808a98d5 plus the four unchanged candJ7c common-flow overlays. No .git retrofit. Both native kit RTL, reset and station phases pass. The next GEN found two shifted envelopes with stale segment coordinates, and the next attempt found collapsed FT grid sites from rounding each half-grid cell independently.
- Corrected port segments and rebuilt both pieces' full 5,630 FT site placements using integer lattice indices at the actual kit row origin. `treeJ7/physical/die_plan/s81/split_hi4x/plan_c_fx_ftgrid.json` is the current private proof geometry. Each payload/epoch site is unique, snap is idempotent, per-bit local max hops below 391 µm. Final preps `kitgrid_att`, `kitgrid_rest` use isolated `.review_venv` for renderer. Old `kitseg_*` preserved.
- Shared `type_split` fix f11e3abd9c3 merged f7c6720324a. Exact replay unit 3017607 emitted 13 cut ports and 15 segments without mismatch or overlap. Stage report `geometry_fix_replay`. Physical plan image reviewed in coord d4ed99f9983. Steps before route include exact kit render, flow config comparison and PG/pin access. Hi4 remains J8.
- Generated four measured renamed xoff clock contracts under `xoff_clock_contracts`. Confirmed candidate candJ7e has all 20 input files byte-identical. Epyc10 R8 private overlay only. Source signoffs and Liberty files unchanged. R4 owns any release-tree adoption.
- J8 all seven horizontal geometry layouts combined on byte-equal v11 base; scoped source manifests `j8/scoped_h8_overlay` select exactly eight hi variants, eight lo stay on released source. Horizontal dry censi all succeed, then real cut allocation fails on bandwidth for three cases and FT reach for rs t6. Exact retained-wire lower bound running under `j8/seam_wire_lower_bound.py`. Shared budget retention candidate d6d37a9b3d preserves inherited ft_track_frac in both pieces.
- Low types: all 86 actual FT groups clear macros. Fixed 18 stale representative coordinate rows of seven slots on three affected types, keeping every actual bit site, worst nominal hop 376.497 µm at zero cycles. `j8/combined_seven_on_v11/lo_nominal_rows.json`. Native bound trace finds 512 wiring paths per low type, 72 connected of 98 hard cores, 12 unresolved instance aliases per type. Low rs t1 private GEN proof `kitlo_t1` underway. No low releases authorized yet.
- R5 arithmetic proofs collected from epyc9: full ATT seeds 1/5 and real cut programmes seeds 1/3 PASS with zero mismatches; arithmetic negative controls caught. Programme q request +1, output streams +2, 160 PV words/20 SM row beats. No J5 service hold changes.

### Codex 14:45–15:23 PST takeover

- E10 exact hi4 both pieces reached native RTL/reset/internal stations, GEN, RTL_LINT and render. Factory PREPARED, outer rc2 only for legacy wave_ref configuration comparison. E10 write freeze observed. Isolated rest pilot retained 13 inherited nongeometry settings, three declared geometry values and current functional latch restoration hooks. No place or route.
- Hi4 Att original generated face guard found 12,652 blocked pins of 19,668. Two independent E2 private replays reproduce the exact original 127 placements, then shift 14 west macros (eight hard, six SRAM) inward 4.32 µm. Final guard zero blocked pins, zero blocked taps, no landing/FT/macro intersections or track regression. E2 units 3164493 and 3294720. Workspace /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r8-north/hi4_kit_readonly/att_access_review. Renderer and incremental physical plan delta run from render_att_delta.py. Full fresh kit and exact placed-kit review are pending before route. Hi4 remains private for J8.
- E10 kitlo_t1 finished 5/5 native RTL/reset/internal stations/GEN/lint with the measured xoff clock contracts. Zero face block. R4 notified. Shared count parser edaae872889 merged 7d19bbd68f0. Actual eight low variants give 576 paths and 76 connected hard cores of 98 versus 512/72 before. Remaining nested hrow is genuinely beneath kept dsdv_svc_sx.
- E7 t5 vertical x371.52 layout keeps all exterior windows and every FT stage. Exact source scan saw 530.393 µm first hop. E7 unit 1745121 repaired 632 bit sites, all four actual maxima at or below 404.749 µm. Input and proof under j8/vertical_t5, with revised plan and native census on E2 j8/alternates_exact/t5. Retry1 stages authoritative core pin table inputs. E2 north t2 actual cut allocator fits, followed by shared strap ties failure omitting an explicitly declared relay without a landed exterior port. Private E2 count_align_bind includes only such relays sourced by an actual landed origin. Exact retry in j8/alternates_exact/north_t2. Before this tool difference, tf plan remained intact.
- E7 north t1 narrowed groups improved early seats, but ft1 still lacks a fixed-cycle legal path. North PV t1 exact allocator charges 11,213 pins with transit duplicates versus 10,388 planned. Vertical alternatives are running. E2 PV t2 has a private 290-macro layout at x466.56 with one −0.743 µm window shift and max landing-band hop 402.378 µm. E2 t3 initial geometry found a west reserve deficit, now packs with a distinct W-side band keepout. E2 t6 initial geometry found early ft1 legal-seat deficits, now tests a narrower FT packet arrangement.
- One canonical OWNER? paragraph records the exact three north feasibility states, t5 unchanged exterior windows and the three candidate vertical shifts. Private source window proposals do not alter release. Matching neighbor construction remains open.
