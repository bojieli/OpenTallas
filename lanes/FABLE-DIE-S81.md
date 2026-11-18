# FABLE-DIE-S81 2026-11-16 08:3x PST: S81 whole-die verdict on B6gF2s2 (v2 tree), and the die event

Owner of S81 die-level PD quality. MEASURED = my runs or files I read. INFERENCE is marked.
Run: epyc9 `/srv/opentallas-scratch2/claude/fable-die-s81/s81/F2s2` (plan B6gF2s2 a623deec2d38, tools v2 tree
src_s81_pin_eb1e73448bd0, chain `run_base.sh`: r98 spt feed + region DME clock kit -> combo die GRT TT/FF 50 it -> tap
arrivals -> die_sta_related; 21 min). Render: intel2 `~/fable-die-s81/die_F2s2.png` (floorplan / clock arrival / GRT
density). Census: `s81/F2s2/dieana.json` (script `dieana.py`). Earlier kit read for comparison: B6gsh (epyc7 die-clk-s81-b6).

## 0. Verdict

The die routes (GRT 0 overflow) and related-pair setup passes (+390 intra, +312 seam). The die is NOT closed on four
structures: the clock cells sit unreserved inside types and on landing bands, the feed is 11.7 ns deep with the K
table still from the B6gsh kit, seam skew is 310 ps against a 40 ps seam contract, and reset fan-out crosses whole col
types in one cycle.

## 1. Numbers (MEASURED, F2s2)

| item | value |
|---|---|
| die | 32.24 x 25.98 mm, 398 partitions / 395 types, 0 overlaps, partition area 798.1 of 837.7 mm2 |
| die GRT TT/FF | overflow 0 / 0 / 0; usage M4 2.6 %, M5 4.1 %, M6 4.4 %, M7 2.2 %, M8 0.9 %, M9 0.8 %; 18.7 GB |
| die STA TT setup | intra +390.05 (0 of 1,333,766 pairs), plain seam +312.48 (0 of 2,040,620) |
| related-pair skew | intra 253.6, seam 310.3 (FF 244.1 / 290.2) |
| hold | NOT measured on real views (0 signed views fed). Kit contract: intra need 208.4, seam need 290.2 against 40 |
| landed pairs | region-to-region damage 3,639 ps TT (3,264 FF) against 416.5: single-cycle FAIL, as expected; covered only by count-aligned rings with a K table from THIS clock |
| clock tree | 93,530 cells, 21,687 taps, 7.67 m wire, 22..188 stages; tap arrival 1,314..11,682 ps TT; late-early up to 1,359 ps |
| clock legs | 559 over 260 um, 21 over 405 um, max 995 um (kit runs without a reach cap) |
| clock cells vs types | 93,522 inside partitions, 0 in hard cores, 54 in the 2.16 um core halo; 2,586 inside landing band rects (223 types; svc_hi t6 attnh_i0 50, svc_lo_w t1 hbmrd_i0 31); about 4,003 on ft station columns (my 6 um test); 0 of 395 types carry clock.reserved_sites_um |
| glue tap spread per partition | median 64 ps; 24 partitions over 100; 1 over 180: s_7N_x13 slice_station__t51 253.6 |
| region spread | median 140; hard_phy_hbm 748, std_bg_70_0 (bk_sel) 405, std_bg_80_0 360, std_bg_64_0 348 |
| channels | 98 ports (57,930 bits) cross a die-route gap; 56 ports (34,292 bits) cross 414.7..527.0 um, over the 405 reach, with no station (svc band gaps grown by +77.76 and +51.84) |
| lanes | 873 lanes, 14,007 cycles; longest idx svc_14 -> bk_sel 25.3 mm / 17 hops / 102 cycles, xtier seqhost <-> bk_sel 23.4 mm / 108; x_E3_out 16.98 mm against 14.12 for x_W3_out (2.9 mm detour, 1,104 bits) |

Visual: the feed radiates from the centre root (16.1, 12.2 mm); arrival grows smoothly to 11.6 ns in the four corners, so
neighbours stay close but every corner region carries about 10 ns of unshared path against the centre. GRT density is
concentrated in the slice_station rings (x 9-10.5 and 22-23 mm, y 11.5, 19 and 24.5 mm); no bin is near capacity.

## 2. Bad structures and root causes

1. Clock cells over types, unreserved. Every type kit is built without the 93,530 die cells; 2,586 land in ring bands
   that the ring-ff form now fills. Root cause: the kit's site rule knows cores and PHY only, and no type reserves.
2. Feed depth. 188 inverter stages and 11.7 ns to the corners. Count-aligned rings absorb the mean, not the variation:
   the CA strap margin was 105.5 against 100 on the B6gsh kit. The K table of record is from B6gsh; taps moved
   (22,895 -> 21,687), so it is stale.
3. Seam and intra skew 310 / 254 ps. Setup has room; hold does not: a 40 ps seam contract needs 290.
4. 21 clock legs over 405 um (max 995).
5. Channel hops 414..527 um on 34,292 bits without a station.
6. Reset fan-out (col): one flop to 103-155 copies across a 1,443 x 1,227 um type in one cycle (-100..-151 routed on
   r2); on 48 r0 types the driver regex missed, so one flop drives 138-145 loads unreplicated.
7. Start tree: 48 long start hops (435..5,812 um) have no measured delay; 1 stage unplaced (S81-START-CAP).

## 3. Die event (delta rows to DIE-S81-92)

| row set | state |
|---|---|
| R1 col reset-copy chains, 216 types (reset_replicate copy_depth 3, per-instance regions, cf_rs regex) | DELIVERED for F2s3: epyc10 fable-die-s81/rst/rows_col_reset_F2s3.json 7ef9db83e4f5 + overlay; tool claude/fable-die-s81-1116 @f222855b650. Checked on real bound RTL of all 216 types, 0 errors; schema 0 errors on F2s3 preview. Routed timing NOT measured |
| R2 clock site reservation, 395 types | DRAFT only: epyc9 fable-die-s81/ev/rows_clksite_F2s2.json (clksite_reserve.py --tree, 54,417 rects). Not for adoption: it would reserve the 2,586 band sites. Needs R3 first |
| R3 clock kit of record: type keep-outs (bands, ft stations, tap rows) in the site rule, reach cap 405 on legs, then freeze | NOT done |
| R4 K table + strap ties + common latency from the R3 kit (count_align_plan --strap-window, capped start tree) | NOT done; ties only, no type re-key unless a depth changes |
| R5 stations in the 56 channel hops over 405 um (+1 cycle each lane, pre-approved) | NOT done; die STA seam setup on them is positive today, so advisory |
| R6 seam hold: per-port windows from this kit (die_sta_related --kit-window-out, s81/F2s2/kitwin.json) | file exists; rows not cut |

## 4. Not checked

Hold on signed views; PG (psm kit not run); the landed K margins on this kit; start-hop delays; whether die_trial
type keep-outs already cover bands when enabled (test_die_trial_type_keepouts exists, yaml does not set it).

## CODEX R3 takeover 2026-11-16 10:4x PST
- Existing epyc2 F2s2ke completed GRT TT/FF EXIT0 (~18.7GB RSS each); taps21687/21687 present. TT intra+396.61 / seam+308.05. FF raw seam-353.23 and landed-phase margins-3255.33TT/-2871.11FF use stale K/phase; measured boundary-hold views0, so no full hold signoff claim.
- R3 failure diagnosed on minimum18-leg vehicle:16 missing placement regions are already-declared svc/jumper channels with between[] but no rect_um. Explicit exact gap rectangles (28 channels) at reach_codex/plan_gap_rects.json + gap_rect_rows.json resolve16/18 without area/cycles. Use current-plan channel_rect derivation when rebasing to F2s3/F2s4; never transplant stale coordinates after re-floor.
- Two in-part paths: SerDes__t2 wide PHY wall needs existing adaptive site-legal helper; node19 cap/xr clock path needs parity/minimum-count stages on legal sides of an unsplittable macro overflight. Shared tools pushed on existing claude/fable-die-s81-1116: cda5a7251117e78fdf815f49563fe707c69b52ff (adaptive helper fallback, normal gate51/51 GREEN) then4aa3ebbc21fe6585bea681511bfc8b3fdcba6159 (largest SPLITTABLE span for extra stages, targeted12/12 PASS; normal gate owned MERGE-QUEUE).
- Whole-body census: original ke point sites93528/93528 legal, but native1.62x0.27um bodies overlap3083 core halos,506 band exclusions,245 outside,7 PHY keepouts. Existing body_sites option was absent. New template s81_tpl_reach1_codex.yaml enables body_sites:true +detour:adaptive, with existing reach405/type_keepouts.
- Body-aware component evidence:17/18 PASS with cda; node19 PASS after4aa (7repeaters,max343.43um,+13.2um wire). Combined18 mechanisms at reach_codex/replay_body_composed.json, max343.43um. No new RTL cycles. Earlier failed logs preserved. A sparse-corner prototype was unnecessary once the padding bug was identified; retained as corner_uncommitted_codex.patch in epyc9 lane dir, never adopted.
- Fresh pinned candidate source epyc2 src_reach3_codex = real tools copy with cda+4aa +inherited private band patch; physical symlink points to same immutable src_v2/physical inputs. No report-all exception catch: it fails closed. Do not edit candidate after launch.
- Visual body-path review LOOKED/PASS-COND at reach_codex/results/geom_review/reach18_body_{paths.png,review.txt}. Launcher run_reach3_codex.sh -> F2s2kr3 is prepared, not yet launched pending4aa normal GREEN. Follow fulltree body/band/reach census, then R2 site rows +R4 K/strap regeneration. Inherited private band patch still needs source/test integration before release; no R2 adoption or R3 PASS yet.

---

# FABLE-DIE-S81 2026-11-17 22:5x PST: D8d (plan_d8f e291d6a8) whole-die review + first die STA read on D7w

V = file or run I read myself. I = inference. Work dir: epyc10 `/srv/opentallas-scratch2/claude/fable-die-s81-1117/d7w_r2`
(my CA rerun, unit oth-ubuntu-1788849-1794983541). Sources: epyc2 `s81-die-r3-proto/s81/d7w_r2` (R3 proto), epyc8
`s81-die-r3-e8/d8/{plan_d7w,plan_d8d,plan_d8d_nudge,plan_d8e,plan_d8f}.json`, `g0_d8e/`, epyc10 `fable-die-s81/s81/F2s4currentECOv3`.

## Verdict

- **D8d may go on to bind/G0 as built** (plan in the build is plan_d8f e291d6a8, not be8d565e). No die-level reason to stop it.
- **Die route: no blocker.** D7w GRT (V, combo_TT.log): overflow 0 on M4-M9, 550,358 nets, usage M4 2.73 / M5 4.04 / M6 4.42 / M7 2.15 %.
  Caveat (V): M4-M6 run at 25 % capacity (ADJ 0.75) but M7 at 100 % (ADJ7=0). At 0.6 of M7 the die-wide M7 use is 3.6 %, and
  the s_4N_L1 window 17.2 % becomes 29 %: still no blocker. The cut moves are optional; keeping only 9 of them is right.
- **Die STA with the real clock: NOT measured yet.** The proto does not time the S81 clock of record (blocker B1).

## What D8f is (V, full JSON diff against D7w: 35 entries)

9 rigid y moves (t3 x3, t43 x4, t14, t32, t52; every dy a multiple of 8.64), 3 flips (t3 u_vsw MX->R0, t3 u_rxsf MY->R0,
t43 u_vs MX->R180), `die.hold_ff_margin_ps` 25, and the 4 serdes defines on all 11 serdes types. No outline, w/h or tap change.
Standalone G0 on d8e (same geometry; V): 2 ERRORs, both cuts already in the D7w baseline (s_0S_L0@10500 0.67, s_6S_L0@10750 0.63);
geometry ERRORs 0 (D8c had 8); R-REACH-5 not judged there (needs the bind).

Not in D8f, against what was announced:
1. **TAP-GROUP-CAP-1 is dropped** (serdes clock blocks = D7w). This removes the D8c reset-name break. serdes__t13 keeps one
   6,502-flop u_enc group on clk_t42. FABLE-FIX-S81-SERDES2 decides from the H17 routed timing whether the split returns.
2. **The t53/t7 station site snap is dropped** (V). plan_d8f still has t7 ft3 at [82.9376, 176.8544] and t53 ft0 at
   [9.3393, 1032.3389], off the 0.054 x 0.27 site grid. These are the two "explicit FT site is not on a row/site" place stops.

## Blockers and fix rows

| # | blocker (numbers) | fix |
|---|---|---|
| B1 | **The proto clock is not the die clock.** proto_die.sh builds a generic H-tree (12 levels, 18,870 cells; V tree.json meta). The clock of record is the ECOv3 cohort feed tree (43 levels, 93,626 cells, reach 405). On the H-tree: tap spread inside one partition is over 250 ps on 115 of 398 partitions (worst fE0_p4_b2 1,006 ps); related-pair TT setup -1,066.8 intra / -1,164.7 seam (legacy droop form). On ECOv3 (819 plan, V): intra +340.6 / seam +270.1, 0 negative; 7 partitions over 250 ps (eng 612, bk_sel 389). So the H-tree numbers are an artefact of the vehicle, not a design failure. | Rerun the die STA on the ECOv3 kit: `KITSRC=<ECOv3>/tree/kit proto_die.sh s81 plan_d7w.json d7w_eco` after refreshing 9 taps. D7w differs from the ECOv3 tree in 9 of 21,687 taps (V): 8 `t_gunit__*` and `t_s_3S_L3__clk_c4` (43.2 um). ECO those 9 legs, do not rebuild the tree. |
| B2 | **Count-align fails on proto defaults: 66 of 2,330 crossings have no K/DEPTH** (V ca_plan.log, ca_bind.log BindError). All 66 are neighbour pairs with d of 11 to 102 ps (s_3S..s_7S L1<->C 54, s_2N/s_3N 9, s_7S_x19<->LP 3). Cause: 3 to 5 ambiguous start cycles on the path (L width 4,930 to 5,913 ps against the depth-8 window), not skew. 50 of 397 start edges are ambiguous. | Use the recipe of record, not defaults: `CA_PLAN_ARGS="--start-tree clock --start-retime-up --start-lift --start-retime-max 16 --max-depth 16 --depth-guard-ps 0 --start-native-clocks --start-partition-origins --strap-window --min-lat-cycles 1"` (epyc10 `fable-die-s81/reach_codex/run_current_r4_ca_phase.sh`; on ECOv3 it gives 993 crossings, fail 0, 376/376 clean). |
| B3 | **The adopted K table does not belong to the clock of record** (carried since 11-16). `clock.landing_network.count_aligned_cycles` is the B6gsh table; the tree is ECOv3. LATCHECK 873/873 proves lane cycles, not landed phase margin. Also unexplained (V): `r4j/ca_plan.log` prints worst_margin_lo -310.4 ps (sid_s_0S_C__s_0N_C__1) and 447 crossings below 100 ps, while the handoff quotes +106.2. | S81-DIE-R3: state which number is the landed margin of r4j. Then one clock event after D8d: in-place K refresh that keeps the adopted start network (r4g/r4j form: 33 depth-ups on 14 types, svc_0 +32 ps on leg 11401 = two inverter pairs). No recompose. |
| B4 | **t7 / t53 station sites off grid** (2 leaf types cannot place). | Copy two rows from `plan_d8d_nudge.json`: `partition_types.ot_s81sl_leaf__t7.ft_slots[ft3].bit_sites_um` (277 bits, shift +0.0064/-0.0044) and `...leaf__t53__clb66fa5cb.ft_slots[ft0].bit_sites_um` (669 bits, +0.0027/-0.1289). I checked both land on the grid (82.944 = 1536 x 0.054, 176.85 = 655 x 0.27). Do not restart d8dr2 for it: next row event. |
| B5 | **93,626 die clock cell sites are reserved by no type** (R2, open since 11-16). Every type signed before the reservation needs an occupancy check. 42 of 394 are signed, so the cost is still small. | Adopt `clock.reserved_sites_um` in the same clock event as B3, with a read-only census of the signed DBs first; ECO only the hits. |

## Reset and the 780 hops

- Reset reach: D8f has no tap change, so the two D8c R-REACH-5 errors should not return; the build's bind -> local_reset_writeback -> rebind fixpoint is the right check. The new serdes RTL (BOOT_RELEASE3) can re-pick names once; expect NWB > 0 on pass 1 and 0 on pass 2.
- Insertion skew (V, ECOv3 TT tap arrivals): 1,449 to 12,262 ps, 24 to 196 stages, i.e. 13 cycles from the s_3S/s_4S centre to the fW5 corner. It is covered by K (K -10..+9 in r4j) and must not be floorplanned away. It costs margin only through unshared-path OCV, which is why B3 has to be measured, not assumed.

## Not checked

Hold on signed views (0 measured pairs, 41 core views missing); PG; the D8f bind, LATCHECK and G0 in-tree (build d8dr2 is in elab);
STA_LEGACY of my CA run (still running when I wrote this, `ca/sta_legacy.log`); ECOv3 arrivals on the D7w plan (B1 rerun).
