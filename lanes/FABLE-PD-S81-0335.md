# FABLE-PD-S81 03:35 PST 11-15 (read-only review; nothing killed, nothing patched)

## A. G1 proof3 (dsdv_slice_c1x_C__t1, epyc10 genbug-impl/proof3), log 3_3_place_gp.tmp.log read at 11:41 UTC

CAUSE: global placement is NOT oscillating. It is the standard routability loop (-routability_driven): each
round runs ~150 Nesterov iterations from the saved snapshot (overflow 0.60, iter 243) down to overflow 0.30,
runs a global-route estimate, inflates cells, and REVERTS to the snapshot (GPL-0087). The overflow samples
0.43/0.31/0.53/0.65/0.47/0.57 are points on that repeated 0.65 -> 0.30 ramp, not divergence.
  round : weighted congestion : overflowed tiles : inflated area
  1 1.6602  4.77%  +9.49%   | 2 1.6718 (worse 1)  4.26%  +8.50% | 3 1.6076  4.28%  +8.53%
  4 1.4731  4.30%  +6.13%   | 5 1.4164  4.40%  +4.75%           | 6 1.3999  4.50%  +4.34%
  7 1.4006 (GPL-0049: higher than minimum, consecutive non-improvement count 1), tiles 4.52%
Each round ~11 min (7 rounds 10:25 -> 11:40 UTC). Timing-driven ran once (iter 240, +102k buffers, wns -565 ps),
before the loop; it is not what repeats.
Not G1: movable utilisation 3.2% (268,354 movable, 161,742 fixed of which 120,838 tap/endcap; FIRM hook cells
~41k: 9,513 face + 532 ft + 11,332 istations + 369 reset + 19,115 cland). 11k FIRM flops in 1.75 mm2 core cannot
block density. The overflowed tile count is flat at 4.3-4.8% over 7 rounds while peak congestion fell
1.80 -> 1.48 (top 0.5%): the residue is structural (pin strips / fixed ring bands), which inflation of movable
cells cannot remove, hence the plateau at 1.40.
NOT MEASURED: the wave-kit baseline GP log for this type was not found on epyc10 or epyc7 (cleaned), so the
"baseline rounds / final congestion" comparison is missing. No FIRM-overlap check was run (no placed DB yet).

CONVERGENCE: yes. Congestion plateaued in round 7 (1.4006 vs 1.3999). The loop ends on consecutive
non-improvement (expected 3 in this OpenROAD: about 2 more rounds, ~12:05 UTC), then reverts to the best
snapshot and finishes Nesterov to final overflow + timing-driven pass 2 (est. done 12:20-12:40 UTC).
Hard bounds if that limit is not 3: revert cap, and iteration 1,300 of the Nesterov cap. CHECK (GENBUG-IMPL):
if round 10 (about 12:15 UTC) still prints GPL-0087, relaunch once with GPL_ROUTABILITY_DRIVEN=0 (place goal
only); do NOT change FIRM to PLACED or shrink the FIRM set: neither is the cause.

INSTALL DECISION: INSTALL G1 NOW, do not wait for GP. Reason: G1 changes only which flops the istations hook
fixes, and FIRM cells do not move in GP/DPL. Their site is final at hook time: touched=11332 missing=0
packed_stage_unmatched=0 (leaf t11 proof already passed placed: last stage 175 -> 13 um, max hop 721 -> 296 um).
The GP result cannot change the last-station position; it can only show routability, which G1 does not worsen by
construction (it removes 2,882 flops that sat q50 442-965 um off site with hops to 2,201 um).
Keep proof3 running as the post-install confirmation: when 3_3_place_gp.odb exists run pq/stq_run.sh
(last stage q90 <= 30 um, hops <= reach) and post; a FAIL there = revert .bak-genbug1 for S81 only.

## B. S81 count-aligned (CA) chain (epyc8 die-grt0-s81/s81/b3x2d_ca, DIE-S81-92)

(a) WHY 13 get no K. None is unreached (398/398 regions reached). All 13 are "nontree" crossings whose lag
window is wider than the DEPTH-8 ring: limit 7.5 T - aperture = 6,143 ps.
  svc_0 <-> svc_2 (6: idx, unit x2, vid, dfi svc_0->phy_hbm, hbmrd phy_hbm->svc_0): path ambiguity 4 cycles,
     L_hi 6,152-6,479 ps (the two svc_2->svc_0 rows miss by 9 ps)
  bk_sel <-> s_4N_x06 / gunit (6: xtier x2, tl, ca, cb, flt): path ambiguity 7 cycles, L_hi 8,836-8,988 ps
  up_s_4N_L0_2 (s_5N_L3 -> s_4N_L3): path ambiguity 6 cycles, L_hi 7,504 ps
Root cause: the start (reset-release) tree is the DATA min-ambiguity tree, depth 22, with 83 of 397 edges
ambiguous (314 clean). Region pairs far apart in that tree sum every ambiguous edge on the path. Same defect
as QC t6 (START-TREE-1 README).
(b) FIX, two steps.
  Now (no plan change, proven RTL results/die_s81_11_1028/D16.md, COORD 11-13 opt-in): pass
  --depth16-allow <json of the 13 port ids> to count_align_plan.py. DEPTH 16 limit 15.5 T - ap = 12,807 ps,
  worst L_hi 8,988 ps: all 13 fit with >= 3,800 ps. die_chain_ca.sh does not forward planner flags today:
  add a CA_PLAN_ARGS pass-through (copy+mv in the private ca_tools).
  Structural (next delta): --start-tree clock with the clock-variation table (12.16b(iv)); it removes the path
  ambiguity itself and should return the 13 to DEPTH 8 and cut lat 4-7 rows (463 crossings).
(c) B6 CLOCK KIT: split what the types need from what the die ties.
  Type content = ring DEPTH per bus + strap_ca_* pins (strap form, MESO-STRAP-1). Die content = K tie values
  and lane latency. So: run the CA bind in STRAP FORM. Then K from a later clock kit is a parent tie change and
  does not re-key any type; only a DEPTH change (4 <-> 8 <-> 16) re-keys.
  The B3x2d table is good enough to FIX DEPTHS if depth is chosen with guard: worst margin is 104.6 ps against
  a 104.1 ps aperture (zero spare), so promote to the next depth every crossing whose L_hi is within 1 T
  (833 ps) of its depth limit. Count them from count_align_plan.json before launch.
  The K table itself MUST be rebuilt on a B6 clock kit before die STA sign-off (B6 moves leaf seams, serdes
  TX/RX pipes, phy_pg macros: arrivals shift). How: B3x2d chain (run_die.sh + s81_b3x2d.yaml: kit + combo die
  GRT 50 it TT/FF + tap arrivals -> proof_ca) re-pointed at the adopted B6gsh plan, then run_ca.sh. Start it
  now in parallel on epyc8; it does not gate the type release if strap form + guarded depths are used.
(d) ADOPTION: do NOT fold CA into the B6gsh bind in flight (it would restart a bind near its verdict and couple
  a PD plan to a 2,018-row latency change). Adopt B6gsh once it passes; CA = the immediate next delta
  (strap form, 13 on DEPTH 16, guarded depths, LATCHECK on the 2,018 changed latency rows). The 350 types stay
  held until that CA delta bind passes (stop list respected); they do NOT wait for the B6 clock kit, only the
  K ties and die STA do.
  CHECK before the CA delta: 2 crossings have lat_cycles -1 and 27 have 0 (lat_hist): confirm bind.py accepts
  negative/zero lane latency or pad those 29 lanes by +1/+2.

## C. Follow-up 04:45 PST: the 61 crossings with no K at DEPTH 16 (b3x2d_cag2) and --start-tree clock

MEASURED (two planner probes on epyc8, same inputs as ca_g2.sh, outputs in my own dir
/srv/opentallas-scratch2/claude/fable-pd-s81/stc; nothing of DIE-S81-92 touched; 4-5 min each, 1 core):

WHY 12-19 cycles. Not station counts. With the one-model STA hull (--sta-proof) every data-crossing interval is
wide (start edges: median 525 ps, max 1,796 ps) and rise-only (rows_without_measured_fall 2330, the proof has no
fall arrivals), so only 10 of 397 data start-tree edges are clean (was 314 on the nominal point, 312 of them by a
fall pick that was never measured). Every tree edge then adds 1 ambiguous cycle, so path ambiguity = tree path
length: eng (depth 11) to svc_14 (depth 12) = 19. Equalising station counts on the start legs does not help;
the start must leave the data crossings.

EXACT ARGUMENTS (count_align_plan.py; STA = the ca_g2.sh set):
  python3 -s count_align_plan.py $I/landed_phase_ocv.json \
    --sta-proof $PR --sta-plan $PLAN --sta-cppr-lca --sta-clock-cell inv2 \
    --start-tree clock --start-retime-up --start-lift --start-retime-max 16 \
    --max-depth 16 --depth-guard-ps 833 --out $O/count_align_plan.json
  (no --sta-clock-ocv needed under the nominal margin policy; --depth16-allow no longer needed; --tree-parent
  must not be given.) die_chain_ca.sh has no planner pass-through: call the planner directly as ca_g2.sh does,
  or add CA_PLAN_ARGS. The probes ran without --depth-guard-ps; add it as in cag2.

RESULT                               crossings no K   depth 4/8/16     max path amb   start edges unclean   lat total vs +3
  data tree (cag2)                   61               824/1208/237     19             387 of 397            +1,061
  --start-tree clock                 0                1968/362/0       3              57 of 762             -438
  + retime-up + lift + retime-max 16 0                2276/54/0        1              6 of 768              -856
All 61 resolve: in the first probe they take depth 4 (42) / 8 (19), worst L_hi 4,020 ps, path ambiguity 0-2.
151 retime flops on clock-tree nodes, 51 lifted, worst margins lo 104.3 / hi 105.2 ps.

OPEN: 6 start edges stay unclean, so the planner exits 1 (12.16b(iv)). They are not wide: width 17-32 ps, but
the capture clock is only 33-108 ps after the launch clock, inside the 104 ps aperture of the rise boundary:
  st:h2000000000000000300010 (below: s_1S_L1 s_2S_C s_1S_C)      d 85.0
  st:h1000..0010 (s_6S_L0 s_5S_L0)                                d 108.3
  st:h5000..0010 (s_2N_L1 s_2N_C s_1N_L1)                         d 71.4
  st:h2000..0010 (fW2_p1_b2 fW2_p1_b1 fW2_p2_b2)                  d 97.7
  svc_8 -> phy_hbm                                                d 80.6
  st:h5000..000 (fW5_p1_b0/b1/b2 fW5_p2_b1/b2)                    d 44.5
  (full node names: regions[].start_from with sync_values 2 in plan_stc2.json)
They do not cost any crossing its K (176 crossings carry 1 ambiguous cycle, all inside depth 4/8).
FIX for the 6, in order:
  1. Falling-edge capture (EDGE_FALL=1): the T/2 boundary is 308-383 ps away. Needs MEASURED fall arrivals:
     add the fall arrival to tap_arrivals_<corner>.json from the existing combo GRT + OpenSTA (arr_TT/FF, no
     re-route), then re-plan. Never rise + T/2.
  2. If fall cannot be dumped today: a planned delay on those 6 start nets (>= d + 104 = 137-212 ps of
     clk-to-D) declared with --start-data-delay {ports:{port:[lo,hi]}}; it must then be measured on the build.
NOT CHECKED: physical reach of the 768 start hops (--start-max-hop-um 405 was not passed; the retime flops need
sites and GEOM), the bind/RTL side of dedicated start ports (count_align_bind.py on plan_stc2.json was not
run), and the B6 clock kit (this is B3x2d).
DECISION: use the third row as the S81 CA plan form. Run count_align_bind (plain + strap) on it now with the 6
edges listed as open; fix them by the fall dump in parallel. No plan re-floor and no station equalisation.

## D. Leaf kit generation failures on the adopted B6gsh (S81-LEAF-PLAN cp27 control), 06:15 PST

All three reproduce from the B6gsh tree and plan alone; none is the leaf delta, none is the kit env flags.
The release wave WOULD hit all three if it is repointed to run/b/B6gsh/src + ev/B6gsh.json as is.

D1. sdc_lint core tap window (t14, t54 x2). KIT SETUP (stale lint in the bound tree), not plan, not generator.
  B6 is the first S81 plan with clock.tap_offset rows (R-CLOCK-7): 395 of 395 types have rows, 334 of them on
  core taps (clk_cN), tol 0 everywhere; the wave plan B3x2b has 0 rows. gen_phys writes the offset form
  (-early o-u / -late o+u). The lint that accepts this form is main 1ab1a16c27f; the wave tree B3x2b/src has
  it (sdc_lint sha1 5d78ad92, installed 11-15 06:20 UTC), but overlay ovl_b6h ships the older sdc_lint b38eb379
  (11-14 02:39) and B6gsh/src and LT2/src carry that copy. Same drift on gen_phys.py (B3x2b 210e9b8f 11:43 vs
  B6gsh 2a22a996 09:59) and bind.py.
  Hits: 334 types certain (core-tap rows), expected all 395 (every type has offset rows; the old lint also
  rejects grid-port offsets); t17/t72/t62 only fail earlier on D2/D3.
  Fix (KIT-OPS-5 with DIE-S81-92): wave src for the release = B6gsh/src + the wave overlay set, with
  tools/die_plan/sdc_lint.py = main (5d78ad92 or newer); remove sdc_lint.py from ovl_b6h; run
  hook_manifest.py check on the tree before the tick. NOT RUN: I did not regenerate t14 with the new lint.
  Advisory: tol 0 on all rows means every tap is timed at an exact offset; R-CLOCK-7 intends a tolerance u.

D2. Reset collectors differ from the bound RTL (t17, t72). PLAN (stale collector publish), 9 types.
  Scan of all 395 types with the same comparison the generator makes (epyc7 fable-pd-s81/collscan.py B6gsh):
  326 match, 60 inactive, 9 MISMATCH: leaf t8 t12 t17 t33 t52 t59 t68 t72 and kv_leaf t3.
  Not a stale sidecar: sidecar_new.json, the bind output bind_clock_landings.json and the plan
  collector_tree / collector_local_sources all agree with each other and all disagree with the emitted RTL.
  t17: the plan publishes landing source ft1_i on reset tap 46 and ft2_i on tap 47; the bound RTL collects
  ft1_i at rst_n_t20 and ft2_i at rst_n_t18 (bands moved in B6, the contract tap of the source did not).
  Fix (DIE-S81-92): collector_reattach.py + stage_sidecar_collector_sync.py on those 9 types in the next
  delta, regenerate sidecar_new.json, re-run collscan.py until 0. The bound RTL already has the right taps,
  so the RTL should not change; confirm by the delta bind. If reattach reproduces taps 46/47, it is the bind
  emitter (GENBUG-IMPL), not the plan: say so at once. NOT CLOSED: I did not run reattach.

D3. t62 ORIENT-OFF-TRACK. PLAN (introduced in B6), 13 types.
  ot_dsrom_su_hcpost_lane_pr in an x-mirrored orient has no on-track origin (M3 and M5 pin phases;
  LEAF-DRT73-1). B6gsh holds 8 R180 + 5 MY lanes, one each in 13 types: leaf t4 t7 t25__cl431c660f t33 t37
  t45 t46 t53__clb66fa5cb t58 t62 t67 t73 and kv_leaf t3. Wave plan B3x2b: 0. B6gsl (LT2): the same 13.
  Fix (S81-LEAF-PLAN): orient_realize.py --types on those 13 (R180 -> MX, MY -> R0), re-derive taps and lane
  ends on swapped faces, hand the type rows to DIE-S81-92 for the same delta as D2; add the orient check to
  core_place so a move cannot bring it back. NOT CONFIRMED BY TOOL: the whole-plan dry run did not finish in
  560 s; the count is a plan scan of this master only (the 5 MY by the rule in the tool header), other
  masters unscanned.

Union D2 + D3: 20 distinct leaf types need a plan row change (t33 and kv_leaf t3 are in both).

## E. CA delta compose (phy_hbm 8 landings, 5.6M flops), 06:15 PST

(a) 5.6M is a formula total, not a net add and not a bug. requirements.json: 2,330 crossings, 1,120,119 bits,
  and 5 flops per bit (clock_landing_plan.py: live storage = 5 x (width + epoch), depth-blind; the same line
  prices HEAD and KV, so the per-bit cost is identical there; their totals were not measured).
  The +3 form of today already has 993 crossings, 447,111 bits = 2.24M storage flops.
(b) The real problem is the REGION MAP, not the CA form. The compose used the identity map (398 regions = one
  per partition). The adopted plan has 98 clock regions; partitions in one region are plain synchronous
  neighbours with no landing. Split of the 2,330 (depths from ca_g3f plan_nohop.json):
    cross-region, landed today:    508 at depth 4 (232,742 bits) + 485 at depth 8 (214,369 bits)
    same region, no landing today: 869 at depth 4 (388,373 bits) + 468 at depth 8 (284,635 bits)
  The 1,337 same-region crossings (673,008 bits, 3.4M flops at 5/bit, 4.5M at depth + 1) are pure cost:
  the fixed +3 does not exist there either, and die STA times them directly.
  RULE: CA applies only where a landing exists today, the 993 cross-region crossings. Depth-4 rings replace
  the +3 rings one for one (0 added flops); the 485 depth-8 crossings add 4 flops/bit = 857,476 flops.
  Re-plan them with --depth-guard-ps 208 instead of 833 (the table is now on the B6 kit, the large guard is
  no longer needed); NOT MEASURED how many drop back to depth 4.
(c) phy_hbm: neither multi-landing nor a dfi merge. All 17 phy_hbm crossings (dfi_i0..7, hbmrd, flt) are
  inside region hard_phy_hbm, shared with eng and svc_2/4/6/8/10/12. On the 98-region map phy_hbm has 0
  landings, as in the adopted plan, and the compose restriction never triggers.
MINIMAL PATH (DIE-S81-92):
  1. Region table = the 98 tags of B6gsh sidecar_new.json regions[] (tag -> parts), in place of
     regions_part.json; rebuild regions_ca_strap.json on ca_g3f (fall arrivals, strap form).
  2. Re-plan (same args as section C, guard 208); expect 993 crossings. Check 0 no-K and 0 unclean start
     edges again: the start tree changes with the region set.
  3. ca_compose.sh -> run_bind_ca.sh -> LATCHECK; fold D2 + D3 rows into the same delta.
  4. Release the 350 on that bind with the D1 tree fix.
NOT CHECKED: that count_align_plan / ca_region_table accept the 98-tag table unchanged (ca_merge.sh and
ca_merge2.sh exist in die-clk-s81-b6, not read), and the compose result itself.

## F. CA compose failures on the 98-region table, and the release question, 07:10 PST

MEASURED FIRST (ca_e_g417 plan.json, B6gsh clock kit with fall arrivals, the 993 landed crossings):
the fixed +3 ring is not a valid die form on this clock. 930 of 993 crossings fail the +3 ring margin, 722
do not have a cycle-fixed latency, 599 have a region-to-region arrival difference above one period
(max 3,419 ps, worst +3 margin -3,361 ps). LATCHECK 873/873 on +3 is an ideal-clock result. So CA is a
correctness item, not a latency gain (it costs +13 cycles in total), and it cannot be dropped, only sequenced.

RULINGS for a composable delta
1. Relay stages over 405 um (134 errors): remove the relays, do not re-place them. The relay is a star from
   the region origin partition to every other partition of the region (2 registers, up to 7 partitions per
   region, 75 regions, 135 relay partitions), so its wire spans the region (up to 4.1 mm).
   Use one start origin per partition: add --start-native-clocks --start-partition-origins to the section-C
   arguments. PROBED on the same inputs (epyc7 fable-pd-s81/po, guard 417): 993 crossings, 0 no-K, depth
   4/8 = 833/160, latency total +13 (unchanged), start tree 378/378 clean (min sync distance 105.4 ps),
   0 relay partitions, plain count_align_bind rc 0 with 0 window violations (lo 108.7 / hi 522.5 ps).
   NOT RUN: the strap-form bind on this plan (needs the part table) and the compose.
2. cland_rstart_out used 2-5 times (29 errors): one pin and one launch flop per consumer, no branch on a die
   wire (point-to-point pins, as every other lane); an absent child leaves its output open. With partition
   origins all 378 start ports launch from 146 clock-tree retime nodes, fan-out 1 to 9 (43 nodes with 1,
   52 with 2, 51 with 3 or more), so compose needs this form in any case.
3. Depth-8 bands that do not fit (17 buses, 11 types): do not resize first. Only 52 of the 160 depth-8
   crossings need depth 8 on their own window (L_hi above the depth-4 limit 2,811 ps); 108 are guard
   promotions. Rule: a bus whose band does not fit stays depth 4 if every copy has L_hi <= 2,811 ps
   (per-bus exception list in place of the global guard, then re-run the strap sim on the whole table);
   a bus that truly needs 8 gets a notched multi-rect band (leaf_rules bands --densify --max-depth form).
   My per-type match of the 17 was partial (23 depth-8 crossings found on svc_lo_rs t7, svc_rs t2/t5,
   pvso_entry t2: 14 guard-only, 9 need 8); DIE-S81-92 must redo it on the compose placement list.
OPEN RISK, not checked by anyone: physical reach of the 378 start hops (the earlier identity-map run had
66 start hops over 405 um with --start-max-hop-um). Run the partition-origin plan once with
--start-max-hop-um 405 and post the count before the compose.

RELEASE DECISION (recommendation; the stop list is COORD's to lift)
Release now, on B6gsl with the 13 orient rows if it passes, else B6gsh, fixed +3, with the D1 lint tree fix:
  - the types with no active landing (60 of 395 types): final, the CA delta does not touch them;
  - the landed types (335 of 395): build to sign-off now as PRE-CA. Their core logic, congestion and timing
    results carry over; the CA delta changes ring read logic, strap and start pins, and 160 bands at most.
    At CA adoption they re-key and re-run. Label their records pre-CA and do not report them to the owner
    as final: the die is not functional on +3.
  - exclude the 9 D2 types until GENBUG-IMPL fixes the emitter.
Reason: the CA delta still needs three tool changes (partition-origin strap table, per-consumer start pins
in compose, band exception list), a reach check and a 2-hour bind; no one can promise it today, the fleet
is idle on these types, and finding the problem types is the slow part. Cost: one extra build wave for up
to 335 types and a signed count that drops at the re-key. If COORD prefers no superseded records, release
only the 60 unlanded types now and hold the rest for CA.

## G. Start-hop reach and the strap depth cut, 08:05 PST

(1) START HOPS OVER 405 um: real, but the failure is timing, not routing.
  What they are: 1-bit die-level nets between start-stage flops that sit beside clock-tree node cells
  (start_stage_emit.py) and the partition start pins. The die router can repeater them. The planner judges
  each start edge on the clock phase only (data delay 0) unless --start-data-delay is given.
  Measured on the form now in bind (ca_f, uncapped, node and tap coordinates of proof_fall):
    378 start edges; 340 are over 405 um (337 over 453.6); median 1,767 um, 90th percentile 3,951, max 7,556.
    Room before the sampling boundary on those 340: median 168 ps, minimum 1 ps.
    At 0.1 / 0.2 / 0.3 ps per um plus 40 ps clock-to-Q the wire delay exceeds that room on 234 / 301 / 315
    of the 340 (delay figures ASSUMED, not extracted).
  Consequence: the start bit is sampled a cycle later than planned or inside the aperture, the partition count
  origin is off by a cycle, and the lane latency is wrong at the die. The RTL LATCHECK cannot see it.
  The compose check (max hop 379 um) covers partition-to-partition edges only, not these die-level nets.

  RULING: take the capped form (--start-max-hop-um 405) as the start tree of record.
    capped, no delay model (ca_f_hop):   2,854 edges, 2,425 retime stages, depth 4/8 = 827/166, 0 no-K,
                                          latency +23 vs +3 (uncapped +13), max path ambiguity 1.
    capped + delay model (my probe, epyc7 fable-pd-s81/dd, model lo 25 + 0.06/um, hi 70 + 0.22/um, ASSUMED):
                                          all 2,811 hops at or under 405 um stay CLEAN with their wire delay.
    So the cap makes 2,811 of 2,859 start hops safe against wire delay. Only the long ones are left.
  THE 48-49 LONG HOPS (435 to 5,812 um; 33 node-to-node, 16 node-to-partition): gaps where no intermediate
  clock-tree node gives a clean stage. Origin moves do not help the 33 node-to-node ones. With the delay
  model they are ambiguous and cost depth downstream: 201 crossings on 52 receiver types change depth
  (164 from 4 to 8, 37 from 8 to 16), latency +307. List: fable-pd-s81/dd/types_depth_open.json.
  Fix, in order (DIE-S81-92 with the start_stage_emit owner):
    a. give each of the 48 its own measured delay: route the start nets in the die clock kit, read launch
       CLK to capture D at TT and FF, pass them as ports in --start-data-delay. A fixed, measured delay of any
       length is fine; only an unknown one is ambiguous.
    b. where the measured window is still unclean, add a start stage on a tap of its own (a leaf buffer off
       the nearest tree node, placed mid-gap) and re-plan. This is the "relay station" form; it needs the
       tap in the clock kit, so it is not a same-hour change.
  WHAT GOES INTO THIS DELTA: the CA bind in flight (uncapped) decides type content only through ring depth
  and start pins. Capped vs uncapped changes depth on 6 crossings, 3 types (col_h9_r0_p1__t1__pv697f40c9,
  col_h9_r0_p5__t1__pv8995e794, serdes__t13). So: do not restart the bind. Adopt it for the type release,
  and make the capped start tree the next die-level delta (start stages, strap ties, those 3 types).
  Release rule for the 335: release all except the 9 D2 types and those 3; the 52 types in
  types_depth_open.json are released as AT RISK of one depth re-key (4 to 8) if fix a/b fails for their edge.
  CHECK BEFORE RELEASE (not done): diff the start pin sets per type (start_pins type_pins) between the
  uncapped and the capped compose; any type whose pins differ joins the 3.

(2) STRAP-SAFE DEPTH CUT: guard 417 stays; it is not a margin, it is the strap form itself.
  Every strap margin equals the plain margin shifted by exactly T/2 = 416.5 ps:
    guard 417:   plain lo 108.7 / hi 522.5   strap lo 525.2 / hi 106.0
    exemptions:  plain hi 180.7              strap hi -235.8
  The strap ring reads half a cycle later than the plain ring. The strap-safe depth-4 cut is therefore
  L_hi <= 2,811 - 416.5 = 2,394.5 ps, which is what guard 417 already applies. No exemption list can pass
  in this RTL form; drop --depth-guard-exempt for S81.
  Real lever, next delta, not measured: make the planner strap-aware (pick K against the strap window, which
  has 416 ps unused on the low side). The 108 promoted buses whose window is narrower than 2,291 ps should
  then return to depth 4.
  Band failures: 13 of the 17 are depth-4 buses, so depth is not their cause. The compose re-places bands
  that the +3 plan already holds at the same 5 flops per bit; keep the existing band rectangles for depth-4
  buses. The 2 true depth-8 buses (svc_hi_rs t2 attnh_i0, svc_lo_rs t7 hbmrd_i0) need a notched band.
