# FABLE-CLOSURE-STRATEGY 2026-11-15 15:30 PST: seven levers, c2_t37 guide measurement, stop list

Read-only review by FABLE-CLOSURE-1530. Technical physical design only. HBM parked. Nothing launched, stopped or changed.
Read: the 13:55 strategy, FABLE-PD-DRT-1350 / S81-1415 / S81-1515 / KV-1450 / QC-1245, the queue 13:40-15:20 (r148-r172),
`failure_breakdown.py` (15:10). Measured by me: `route.guide` of the DRT-0255 proof `c2_t37` (epyc9, GRT ended 23:05 UTC)
against the unchanged t37 kit, both `5_1_grt.log`, and the proof log times on epyc8 / epyc9 / intel1 / epyc10.
Scripts: `lanes/fable-closure-1530/gd2.py`, `gd3.py` (text parse of the guide file; no database opened, no STA run).
MEASURED = read or computed by me today. REPORTED = from a lane post or a Fable PD review. INFERENCE is marked.

`failure_breakdown.py` 15:10, technical rows: S81 types 40/394 (104 held, 3 running); HEAD 19/26 (5 running, hd_ctl
detail route error, hd_host_e stopped after CTS); QC 6/127 (84 held, 35 running); KV 5/56 (34 held, 13 running, kv3_hub_Wo
ring band). Since 13:29: S81 +4, QC +3, HEAD 0, KV 0.

## 0. The six levers of 13:55: what moved

| 13:55 lever | state at 15:20 | moved |
|---|---|---|
| 1 `DRT-0255` | Cause named by FABLE-PD-DRT-1350 (M6 guide in the M6 PG pair row, 4 of 4 databases). Variant C was a no-op (stripe smaller than a gcell). Gcell-aligned form c2 running on 3 kits; c2_t37 finished GRT, no DRT result. Keep-out flag stops GRT (`DPL-0033`, 4 of 4). 5 more wave failures 14:08-15:02 (kv3_io_cor, sle_su_l1, coll_s, hd_ctl, slw_hc2) | cause yes, cure no; see lever 1 |
| 2 landing strips | hc rows READY (11 types, band 71-87 / 43-52 um, pilot geom GRT overflow 0). cb: density 0.45 fits 47 of 81 bands, 1.0 fits 61 | yes |
| 3 S81 Event F part 2 | Reset: no new form, hold build (S81-1415). col3_c pinwire view: one-macro DRC 138 -> 0, full route running. New input: element face IFN (S81-1515) | diagnoses yes, no pilot result |
| 4 svc synthesis | Kits generated on B6gE, synthesis running; `sdc_lint` fails on core tap windows until Event G | no result |
| 5 post-CTS setup stops | hd_host_e root cause measured (u_epc 488 ps internal clock, lever 6). hd_host_w RTL passes bind + LATCHECK. sc rows set A gated | yes |
| 6 KV | 7u adopted 14:47; wave not switched at the last lane post; KV-HGSPLIT started | partly |

## 1. Levers, ranked

| # | dies | lever | unblocks | owner | state |
|---|---|---|---|---|---|
| 1 | all 4 | `DRT-0255` class A: the capacity cut leaves the ft-station trunks in the dead rows; read c2 with that split, and build fix 3 (cells off pair rows) now | about 50 types | DRT0255-PROOF-1115, GENBUG-IMPL | NEW measurement |
| 2 | S81 | Measured per-port tap window for col (flat 208 ps today). It is the common term of the reset removal, the IFN face and the ROM link | 216 col types | S81-TAPROWS, DIE-S81-92 | no rows posted; critical path |
| 3 | S81 | One col integration pilot: pg reset rows + hold build + IFN 0 halves + window + col3_c pinwire view | same 216 | S81-GOTAG-SETUP-1115, S81-SEAM-RST-1115, S81-COLABS-1115 | three separate pilots today |
| 4 | QC | S4q6: hc strip rows, sc rows, cb strap sites, cb bands at 1.0; one kit GRT of slw_hc1 as the proof | 84 held types | DIE-QC-103, QC-HC-STRIP-1115, QC-CB-GEN-1115, QC-SC-ROWS-1115 | rows ready, bind due |
| 5 | KV | Wave on 7u, two pilots to CTS, ring cores for the 19 hg / hgi types, `OT_MAXWIRE_UM` 143 | 34 held types | KIT-OPS-5, TYPES-KV-FAIL-1115, KV-HGSPLIT-1115 | waits on the switch |
| 6 | HEAD | hd_host_e early core tap for u_epc; hd_serdes tap sink count conflict; hd_ctl die phase without keep-out | 4 of 7 open types | HEAD-HOST-CLOSE-1115, HEAD-100 | pilots at GRT |
| 7 | KV, S81 | Core abstract pin rows with capacity 0 (head_eighth) and pin wires as OBS (col3_c): one pass over all hard-core masters | GRT run time on hg; col route markers | S81-COLABS-1115 (extend), new lane for KV masters | col3_c proven on one macro |

### Lever 1. DRT-0255: the cut works on the area, not on the row that failed

Evidence (MEASURED, epyc9, `gd2.py` / `gd3.py`; pair phase from FABLE-PD-DRT-1350: VSS 135.744-136.032, VDD 136.128-136.416,
pitch 4.32; gcell 0.57; a track is legal when the wire keeps 0.032 to both stripes):

| t37 | unchanged kit | c2_t37 (gcell-aligned cut, adj 1.0, M5 664 / M6 564 / M7 332 regions) |
|---|---|---|
| M6 resource reduction (`GRT-0053`) | 32.24 % | 37.27 % |
| M5 / M7 reduction | 25.96 / 32.39 % | 29.15 / 34.83 % |
| M6 guide length, total | 476,632 um | 447,772 um |
| M6 guide in rows with 0 legal M6 tracks | 3,826 um | 1,019 um |
| M6 guides longer than 5 gcells in such rows | 98 | 33 |
| the same in rows with 1 legal track | 126 | 90 |
| GRT overflow | 0 | 0 |

- Row share by my track model: 6.2 % of gcell rows have 0 legal M6 tracks, 2.8 % have 1. The pair pitch is 7.58 gcells,
  so the pair sits at a different phase in each period; only about one pair in three has a fully dead row.
- The 33 guides left in c2_t37 are in 3 rows only (gcell rows 238, 276, 2148 = y 135.66, 157.32, 1224.36). 31 of 33 are
  ft output nets (`ft<k>_o[*]` 17, `u_bound.u_ft_ft<k>_o_*` 14), 1 landing fault net, 1 other. Length 3.4-97.5 um, median 9.1.
- Row 238 is the row of the original failure. In c2 it still holds a chain of 15 `u_ft_ft0_o_*` trunks on M6 from x 10.8 to
  x 1,173.6, each up to 97 um (unchanged kit: 14 trunks, x 5.1-1,087.6). The failing net of the kit,
  `u_ft_ft0_o_5/net176850` (x 5.13-103.17), has no guide under that name in c2; the first trunk of the row there is
  `u_ft_ft0_o_5/net176921` (x 10.83-108.30).
- In the unchanged kit the pins of `net176850` are at y 127.68-128.25 and the guide goes up on M5 to the M6 trunk at
  y 135.66. So GRT chose that row; the pins are not in it. The pin row (127.68) is itself under a pair (127.104-127.776).
  This corrects FABLE-PD-DRT-1350 section 1.2 for t37 ("pins sit in the same gcell row as the trunk").
- Proof state 23:12 UTC: c2_fe, c2_hroot, su_A_m7, su_B_cut, p_t49 still in `5_1_grt`; c2_t37 past GRT, no route log yet.

Root cause (MEASURED position, INFERENCE for the reason): the full-width ft station chains keep their M6 trunk in a dead
row even with the region adjustment at 1.0. The adjustment added 5.0 points of M6 reduction; cutting every gcell row that
touches a pair would add about 11-14 (28.7 % of rows, less what the stripes already take). So either part of the pair
rows is not cut, or these trunks are placed without regard to the layer capacity of that row. Not determined.

Fix:
1. DRT0255-PROOF-1115: expect c2_t37 to fail again near y 135.66 (INFERENCE). If it does, that is not a verdict on the
   cut. Read c2 by row: failures outside rows 238 / 276 / 2148 count against the cut; failures inside them do not.
2. DRT0255-PROOF-1115, 15 minutes: print the rectangles of the 564 M6 regions of c2_t37 and check that 135.660-136.230,
   157.320-157.890 and 1224.360-1224.930 are covered; if covered, the adjustment does not bind for these nets and the
   capacity form cannot close the ft class alone.
3. GENBUG-IMPL: FABLE-PD-DRT-1350 fix 3 (station and ring cells off the std rows under the M6 pair, `ft_bit_sites.tcl`,
   `landing_placement.tcl`, `istations.tcl`) moves to first place for the ft and ring classes. It is in the same branch
   (`claude/drt0255-pg-rows-1115-1`); prove it on t37 from floorplan with the cut on. Pass = 0 long M6 guides in 0-track
   rows by `gd2.py` on the new `route.guide` (3 minutes, before any detail route).
4. Use `gd2.py` as the advisory post-GRT line of r153 (2): it needs only `route.guide` and the pair phase.
5. Class B (face pin under the M7 strap: hd_ctl `b_i[101]` at y 6.8-10.8 failed 14:24, hd_spn, t49): the die phase alone.
   REPORTED: the GRT stop comes from `OT_PG_CELL_KEEPOUT`, not from the phase. Run the phase proof without the keep-out.
6. `OT_PG_CELL_KEEPOUT`: class C is 11 of 192 blocks. Fix the TAP-cell skip, nothing more.

### Lever 2. S81 col: the flat 208 ps tap window

Evidence (REPORTED, FABLE-PD-S81-1415 and -1515, measured there on col_h9_r0_p6 and col_h10_r2 at `4_cts.odb`):
- Reset removal: 208 of the worst -229 ps is the window (`set_clock_latency -source -early -208` on all 32 ports), 70 is
  real insertion difference. Window 0: 198 failing pins -> 12, worst -21.
- Hold: 18,059 FF hold cells on the type = 16.9 % of 106,927 logic cells.
- Element face with IFN 0: h9 he rising-edge pins are at setup -102.8 TT with hold +74.4 FF; the window is charged on
  both sides (416 of 833 ps). h9 he needs at least 61 ps off the window.
- ROM -> cfg7_seq: -220 (h9) / -305 (h10) with the window, -12 / -102 at window 0.
- Tap trees 225-434 ps against a 250 target; clk_t13 / t14 / t15 carry 1,291-2,738 sinks, up to 259 ps inside one tap.

Root cause: one modelled number, the same on every port, is paid in full by every cross-port pair of the type.

Fix (S81-TAPROWS with DIE-S81-92; the lane's last post says "NO rows posted yet"):
1. Per-port measured window for the col types (`die_sta_related --kit-window-out` + `tap_window_floor.py`), first for
   the bs / s tap ports and the `clk_c` ports of col_h9_r0_p6 and col_h10_r2. Target 150 ps or less on those pairs.
2. ROM tap rows: each `s<k>` on the tap port of its ROMs `c<k>_0..6`.
3. Split the three overloaded taps (sink cap near 1,500) in the same rows file.
This goes before the IFN pilot read, not after: without it h9 he fails by 30-100 ps (S81-1515 expectation).

### Lever 3. S81 col: one integration pilot

State: three pilots on col lineages answer one variable each: pg + hold build (S81-SEAM-RST-1115), IFN 0 halves
(S81-GOTAG-SETUP-1115), col3_c view full route on a DEF round-trip database (S81-COLABS-1115; 233 MB against 565 MB, so
the route carries less than the wave kit). They interact: the pre-GRT hold build pads the IFN 0 face (S81-1515: about
1,400 he pins below 0 at FF before repair), and each pad ps comes off the h9 he setup; the hold cell count depends on
the window.

Fix: as soon as the IFN 0 halves exist, one col_h9_r0_p6 kit with all five (reset replicate rows +
`OT_TAP_RESET_AFFINITY`, `clock.pregrt_ff_hold`, IFN 0, measured window, col3_c `_pw` LEF) to route. That kit is the
proof for the col delta; the single-variable pilots do not need to finish their routes. Two tool checks from S81-1415
are still open: the hold build must include RESETN / SETN endpoints and must repeat until a call adds 0 cells.

### Lever 4. QC S4q6

Evidence (REPORTED): hc: band depth 24 um fits 1 strip row where 4 were asked; with 71-87 um the pilot has 5 rows and geom
GRT overflow 0 (kit GRT was 40,527). The wave `OT_CLAND_STRIP_DENS=1.0` overrides the plan key. cb: a 576-bit ring band
holds 1.19 flops/um2 in 10.8 um; density 0.45 has no overlap-free box on 34 of 81 bands. cb crossers: 48 of 48 on cbn_q11
are static strap nets of 0.5-1.2 mm from one strap hub; 12-207 per cb type. sc: 34 station rows, 46 lanes +1 / +2,
LATCHECK 1921/1921.

Fix:
1. DIE-QC-103: bind S4q6 with the four row sets; KIT-OPS-5 sets `OT_CLAND_STRIP_DENS=0.45` per item on the 11 hc types.
2. First slw_hc1 kit to `5_1_grt`: the geom GRT is not the kit GRT. Read overflow at y < 90 um.
3. cb at density 1.0 only restores a legal band (+19 % area); it does not thin the clump of FABLE-PD-QC-1115. For the
   34 bands that cannot reach 0.45, the remaining variable is the pin span (band width), not depth: QC-CB-GEN-1115
   lists them with free width on the face. INFERENCE: cbn_q11 SW corner will still show overflow at 1.0.
4. M8 type band shift (`type_m8_grant.phase_um`): keep it to the 3 named types. FABLE-PD-DRT-1350 itself found the M8
   band is not the common factor, and the t37 measurement above shows the trunk row is a GRT choice on M6.

### Lever 5. KV

Evidence (REPORTED): no hg / hgi kit was ever built on a stationed plan. kv3_hg 434k -> 504k cells, one GRT stage 15.5 h.
Count-only on kv3_hgi_v3: max wire 120 / 143 / 200 gives 42,079 / 20,171 / 6,111 buffers. 106 rings of 250 bits or more
map to existing ring masters, many unsigned.

Fix: KIT-OPS-5 switches the wave to 7u; TYPES-KV-FAIL-1115 reads the two pilots at CTS (`ti_b` banks 6 of 6, setup
against -329 / -739 ps); `OT_MAXWIRE_UM` 143; KV-HGSPLIT-1115 posts the list of ring masters that are not signed, since
each is a new core dependency of the 19 types. The q2 clock variants and the pc keep-out rows continue unchanged.

### Lever 6. HEAD

Evidence (REPORTED, HEAD-HOST-CLOSE-1115 on the kept `5_1_grt.odb`): hd_host_e: 646 of 647 violating endpoints start at
u_epc outputs; u_epc has 488 ps of clock tree inside the macro and its pin sits at 308 ps, effective 791 against 450.
With the early core tap the kit check reads -38 + 488 = 451. hd_serdes: plan taps had 16 of 22 at x 1900-2800 with the
sinks at x 1250-1650; NF9 carries the k-means taps, but G0 counts clk_t20 6,569 and clk_t21 1,817 sinks against the
lane's largest cluster 1,090.

Fix:
1. HEAD-HOST-CLOSE-1115: the two counts use different sink sets (INFERENCE: `pma_rck[0]` has 13,524 sinks on its own
   taps and the checker may assign them to the clk taps). Read the `OT_TAP` lines of the first NF9 hd_serdes CTS; do not
   re-site taps on the G0 number.
2. hd_host_e early core tap row to HEAD-100 when the post-CTS setup estimate is at or above -42 ps.
3. hd_ctl: class B of lever 1 (item 5).

### Lever 7. Hard-core abstracts: pin rows without routing capacity

Evidence: col3_c: 64 M5 pin wires were OBS, one-macro DRC 138 -> 0 with the pinwire pass (REPORTED). kv3_hg: 49 of 53
final GRT markers are inside head cores at capacity 0-4, 19 on the e2 north pin row 0.3 um inside the core; the last 10
GRT iterations took 2 h 47 for them, then 5 h 51 silent (REPORTED, FABLE-PD-KV-1450). r170 parked the iteration bound.

Root cause (INFERENCE for KV): the abstract closes the gcell that holds the pin. The structural fix is in the abstract,
not in the router bound.

Fix: S81-COLABS-1115 finishes the 13 S81 masters; a new lane runs the same scan on `kv3_head_eighth_*` (pins whose
gcell has capacity 0 on the pin layer and the layer above) and proposes the OBS pull-back at the pin rows. Check on the
first 7u hg pilot GRT: markers inside head cores.

## 2. In flight: wrong or redundant

1. Reading c2_t37 as the verdict on the capacity cut (lever 1, items 1-2).
2. Die phase proofs bundled with `OT_PG_CELL_KEEPOUT`: the bundle cannot reach detail route.
3. Three col pilots without a combined kit (lever 3).
4. IFN 0 pilot read with the flat window only: it will report h9 he as failing (S81-1515) and look like a failed form.
5. M8 band shift on all QC types in S4q6 (lever 4, item 4).
6. cb bands at density 1.0 counted as the cbn_q11 clump fix.
7. Seam reset forms pg4, pg2, ph, plrc, plrs in `claude/s81-seam-rst-1115`: stopped by S81-1415; the branch still
   carries plrc / plrs miters.

## 3. Stop list (technical dead ends)

1. Unchanged relaunch of a type that failed `DRT-0255` (slw_su_l1, sle_su_l1, kv3_hroot, kv3_io_cor, coll_s, slw_hc2).
2. `OT_PG_TRACK_TRUTH=1` as the class A cure; the stripe-sized region form (no-op); `OT_PG_CELL_KEEPOUT` in `die_gen_env`.
3. `MAX_ROUTING_LAYER = M7`, more route iterations, density or `band_spread` as `DRT-0255` fixes.
4. New reset forms for col removal; reading async removal on `4_cts.odb`; margin changes to pass removal.
5. Sender cores on `clk_c`; per-pin IFN split; link station (+1 cycle) before the IFN 0 pilot; IFN 0 halves signed
   against `in_min -40`.
6. S4q5; hc height growth; unchanged hc relaunch.
7. hg / hgi kits from kvgeom5 / kvgeom6; m7hg_g; M7 core close as a KV family default; M8 / outline / density forms for
   KV congestion (usage 13.9 %).
8. Hold pads for the KV output-port contract (die STA obligation, r168).
9. Routing col before the pinwire views; routing lepe / lepw `mu_LP__t2` before the `safe8_ntf` view.
10. svc kits from tree `7073a6b4a59`; svc without `-noshare`.
11. Kept: `hold_hb4` pads for KV ports; cbn_q11 as built; snapping a built die clock tree onto a site template;
    B6gslcf / B6gshcf, S4x / S4v2, KV 7m / 7n / 7g.

## 4. Not checked

- Why GRT keeps the ft trunks in rows 238 / 276 / 2148 of c2_t37 (lever 1, item 2). One kit, one die.
- My legal-track model uses the layer minimum spacing 0.032 to a 0.288 stripe; with a width-dependent rule more rows are dead.
- `route.guide` of c2_fe, c2_hroot, su_A, su_B (still in GRT). Any detail-route result of any proof.
- The KV abstract reading of lever 7 (no head_eighth LEF opened). The hd_serdes sink sets.
- S4q6 bind state, the 7u wave switch, Event G1d compose result, the svc synthesis result, t14 form R route.
