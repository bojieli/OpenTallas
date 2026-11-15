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
