# FABLE-VISUAL-0030: visual layout review of the unclosed type representatives (2026-11-21 01:2x PST)

Lane FABLE-VISUAL-0030 (Fable). Advisory only, never a gate. Read-only on every kit: nothing cancelled, signalled or patched.
Answer to the owner question: before this round the unclosed types had automatic geometry checks and ISSUES-ACCEPT verdicts only. This round 24 representative kits were rendered and looked at (Read tool on every PNG named below).

## 0. How the renders were made

- Dump: `tools/autopilot/geom_dump.tcl` (the AUTO-GEOM dump) on the newest stage ODB of each kit, plus `gui::dump_heatmap Routing` (GRT ODB) or `RUDY` (place / CTS ODB), in the ORFS image, kit mounted read-only, through ot-run on the kit host.
- Picture: `fv_render.py` (matplotlib, my own dir). Two PNG per kit and one `stats.json`:
  - `A_place_taps.png`: left = placement, cores grey, station flops magenta, face / pin registers green, reset flops and relays red, clock cells orange, pins, every flop -> buffers -> flop hop over 300 um as an orange line, core gaps under 10 um yellow. Right = flops coloured by clock tap, tap pin as a star with its sink count. Classes come from the kit's own `ot_face_flops.txt`.
  - `B_cong_paths.png`: left = congestion heat map with the overflow gcells of the kit's latest `congestion*.rpt` in cyan. Right = the worst setup (red) and hold (blue) paths of the kit's newest STA report drawn cell to cell.
- Location: `<host>:/srv/opentallas-scratch2/claude/fable-visual-0030/out/<label>/`. Scripts in the same dir on each host (`fv_run.sh`, `fv_dump.tcl`, `fv_render.py`). Kits on intel1 and epyc10 could not be admitted (memory) or rendered (no matplotlib on epyc10): their ODB and logs were copied to `epyc8:.../fable-visual-0030/mirror/` and rendered there.
- Limits of the pictures, so nobody over-reads them:
  - A place-stage ODB has one clock root (taps are split at CTS), so tap coverage is judged only on the CTS / GRT kits.
  - Place-stage timing is `3_detailed_place.rpt` (ideal clock): its setup paths show length and depth; its hold numbers are not real. CTS numbers are post-hook only (`4_cts_post_hook.rpt`, `postcts_gate_*.log`).
  - RUDY is an estimate and paints every hard core orange; only the colour in streets and at pin faces counts.
  - "FF without traced tap" are flops on forwarded / recovered clocks or not reached from a clock port.
- Not rendered: S81 svc (no placed ODB exists on any host; the types are 3.3 to 5.1 M cells and sit in synthesis or floorplan), S81 serdes t4 (no placed ODB; t13 used), a GRT ODB of hd_lep0N tr2s (CTS used). The whole-die renders of the live plans did not finish (section 5).

## 1. Summary: seven layout causes that repeat

Ranked by how many families they explain. Each has a structural fix; none is a setting.

1. **Pin registers and stations are placed at the face, the logic that reads them is placed up to 1 to 2.4 mm away, and the hop between them has no station.** Seen in 17 of 24 kits as thick orange bundles. Worst: KV pv_v3 2,411 um, S81 bk_sel 2,518 um, KV hub_C 2,010 um, S81 lepe 1,456 um, QC coll_core 1,446 um, S81 c1x_C 1,434 um, KV pc_v3 1,283 um. Fix: station rows by measured placed length on these buses (one station per 300 um), or move the face window next to its consumer. This is the largest single cause of the negative setup paths drawn.
2. **Reset reaches cores and far flops in one cycle from one relay.** Worst setup path is a reset relay in 7 kits: lepe (-1,293, rrl_11 -> core ln3, 886 um), cbf_q00 (-438, 1,721 um), bk_sel (-824, 2,113 um), hub_C (-2,395, 4,280 um of wire round the tile edge), hub_Eo (-747, 2,220 um), pc_v3 (-1,508, 98 levels), slice_station t36 (-724, 2,035 um to the monitor ring). Fix: relay sites per bank on the placed geometry (RESET-RELAY-GEN-R3 form; io_cor_v1 bank_taps already in D27c).
3. **Cores placed in the way of the data flow.** sle_ctl: u_ctl sits between the east stations and u_tap, so a 710 um path is 1,377 um of wire. coll_core: path detours 1,175 um round u_fs for 439 um. c1x_C: the north-face bus runs 1.4 mm through the memory array slits. Fix: core move / rotate inside the type (core shapes kept).
4. **Tiles over the 400 k run cap, visible as a river of logic with no structure.** hub_C 968 k, pv_v3 783 k, pv_v8q 597 k, c1x_C 477 k, hub_Eo 449 k, lep0N 422 k. Fix: type split (pv split D28 posted; hub and slice C need the same).
5. **Clock taps: a few taps carry several times the cap, many carry almost nothing.** col_h9_r1: t25 3,000 / t1 2,998 / t2 2,866 sinks against a median of 324. col_h10_r0: 7 taps over 2,000, median 408. pc_v3: t1 10,960 and t7 9,982 sinks. slw_hc3: clk 9,196 and t113 7,462 against 1,200. leaf t39: 79 taps, median 44 sinks. hroot: 12 taps with under 10 sinks in an empty west half. hd_serdes: 25 taps inside a 250 x 250 um encoder. Fix: tap grid from the placed flop density (TAP-GRID-R2), one tap per register bank, no tap in empty area.
6. **Logic and macros squeezed into a band or slit much smaller than the tile.** hd_lep0N: 49 macros and 420 k cells in a 330 um band between four cores, 6,410 station flops in slits under 20 um, RUDY over 100 % across the whole band. kv_leaf t5 and c1x_C: stations in the 8 to 20 um slits of the lane-core / memory arrays. bk_sel: all logic in a 200 um strip under seven cores, 4.3 mm long. hd_serdes: all logic in a 1,000 x 380 um blob of a 2,886 x 1,227 um tile.
7. **Congestion follows pin faces of side cores and single trunk streets, not cell density.** hgi_v8 (49,891 overflow, all in x 0-480 y 950-1140 at the ectl_Q landing core on the west face), pc_v3 (38,508, at the kvpc1_f / kvpc3_f side cores), pv_v8q (one N-S street at x 1,080), sle_ctl (the street under the two cores at y 320).

Types whose picture is clean and whose failure is not layout: col_h9_r1 and col_h10_r0 (GRT max 100 %, overflow 36 and 2; the remaining -47 / -61 ps is the ROM core-to-core loop of FABLE-CLOSURE-STRATEGY section 0.1), slw_hc3 old plan (GRT max 53 %, TT +16.6, hold -17), slice_station t36 (hops all under 295 um, RUDY max 81 %), io_cor_v1 (TT +6 at place).

## 2. S81

### col (col_h9_r1 / col_h10_r0) - owner FAM-S81-COL
- Renders: `epyc8:.../out/s81_col_h9_r1/` (5_1_grt.odb 11-21 08:06 UTC, kit s81-geom-opus-d8g d8i tree6 pvf0f1ccb2); `epyc9:.../out/s81_col_h10_r0_e9/` (5_1_grt.odb, pvd7af8531).
- What I see: 81 / 95 cores in a regular array, streets open, GRT routing max 100 %, overflow 36 / 2 gcells. Data flow matches the floorplan: frame stations in rows at the N strip (y 1,185) and S edge, ROM pairs in four quadrants. Stations are in open rows, none in a slit (station slit p10 55 um).
- Worst setup h9_r1: -46.7 ps, ROM e6_u_w (SE pair) -> qbank bn6, 10 levels, 439 um of wire for 308 um, launch tap clk_c8, capture clk_t7. h10_r0: -60.8, cfg7 core s4 -> ROM e4_u_w, 384 um, clk_c0 -> clk_c13. Both are core to core on different taps. Hold at GRT +13 / +25: fine.
- Long hops: 5,050 (h9_r1) and 18,571 (h10_r0) over 300 um. The h9_r1 bundle is the N station row (x 480-560) to the lpl registers at y 940 across a ROM column (520 um); h10_r0 the same bus at 757 um.
- Taps: three taps on the S pin row carry 35 % of all flops (t25 3,000, t1 2,998, t2 2,866; t2 reaches 426 um).
- Fix, by impact: (1) register the ROM input and output at the ROM face (the lever FAM-S81-COL started 00:03); (2) one more station on the frame_int_i0 -> lpl bus so no hop is over 300 um; (3) split the three S-row taps into bank taps of 1,000.

### leaf t39 - owner FABLE-FIX-S81-LEAF-R2
- Renders: `epyc9:.../out/s81_leaf_t39/` (4_cts.odb 11-21 02:35 UTC, s81-die-r4-leafspread tree_Cc); `epyc7:.../out/s81_leaf_t39_p1/` (fable-fix-s81-leaf-r3 p1, 4_cts).
- What I see: 27 cores packed in the SE two thirds with 8 gaps under 10 um; the N and NW 30 % of the tile holds only a grid of reset relays. 27 k face flops sit in blobs on the W edge and the S edge.
- Hops: 11,132 over 300 um, median hop 307 um, max 1,032. Two fans: from the station cluster at (800, 210) and from (500, 190) up to the register cloud at (900-1,000, 550-650). One flop, lpad_leafdn_i0.q[594], drives flops 1,032 um away.
- Worst setup -674 ps: vp source register at (1,150, 600) -> lane core vp_g_ln_0 at (800, 820), 4 levels, 811 um; second -670 to ln_5 at (820, 115). The 16 lane cores stand in a ring 600 to 800 um from the one register cluster that feeds them.
- Hold -241 ps between two vp source flops 10 um apart: 79 taps with a median of 44 sinks, so neighbours sit on different taps.
- Congestion (RUDY): S edge strip x 300-600 (S face 3.06 pins / um) and the SW corner of core ve_u_m: pin-face crowding. Overflow 88 only.
- Fix: (1) one vp source register bank per lane core, placed at that core's pin face (removes the 800 um hops and the -670 class); (2) stations by length on leafdn bit 594 and the cst fans (reset_leg_plan rows are the right form); (3) merge taps so a register bank and its neighbours share one tap (the pair pass was the wrong lever, as measured); (4) spread the cores into the empty north third to open the 8 gaps under 10 um.

### slice_station t36 and c1x_C - owner FAM-S81-SLICE
- Renders: `epyc9:.../out/s81_slice_station_t36/` (3_place.odb); `intel1 kit, epyc8:.../out/s81_c1x_C_t3/` (3_place.odb).
- t36: no cores, 71 k station flops in regular rows, every hop under 295 um, RUDY max 81 %. The layout is right. The one bad path is the monitor ring: rrl_268_t -> cland_monitor_0, 2,035 um, 44 levels, -724 (the known MON_UM, fixed by J6 monitor-home). Nothing else to change.
- c1x_C t3: 477 k cells (over the cap), 47 cores. The memory array (two columns of 12) stands in the NW with 58 gaps under 20 um; 2,243 station flops sit inside those slits. The N-face bus (x 80-150) runs as one bundle through the array to the register cloud at (380-540, 250-330): 22,587 hops over 300 um, max 1,434. Worst setup -511 ps, 50 levels, 1,775 um (xg xf_q -> vo_d). RUDY is over 100 % in the array slits (x 180-380, y 500-1,100) and round core xr.
- Fix for C: (1) split the type (cap); (2) move the N-face window of the xg bus to above its consumer or add four station rows on the way; (3) no stations in the memory slits: station row outside the array.

### lepe_mu_LP t2 - owner FAM-S81-LEPE
- Render: `epyc9:.../out/s81_lepe_mu_LP_t2/` (4_cts.odb 11-21 07:53 UTC, opus-p8-local r4).
- What I see: four ln cores across the N, 49 small cores clustered in the centre (67 gaps under 20 um). 6,111 hops over 300 um: one bundle from the E-face output registers (x 1,440, y 430-470) to the logic at (250-600, 300-450), 1,150 to 1,456 um with buffers only (rop -> roq), and diagonals from the m-core column to the SE face. The lane's placed-hop gate read PASS (credit / land / reset hops under 300); these register-to-register hops are apparently outside what it measures (inferred, not checked in the gate code).
- Worst setup -1,293 (place report): reset relay rrl_11 -> core ln3, 886 um.
- Reset: 549 reset hops over 300 um, max 662 (g_reset_balanced group_r -> local_r).
- Fix: (1) output pipe registers rop / roq placed along the way (three stations) or the E window moved to the west half; (2) reset relay next to each ln core; (3) local_r relays placed inside their group.

### serdes t13 - owner FAM-S81-SERDES
- Render: `epyc7:.../out/s81_serdes_t13/` (3_5_place_dp-failed.odb 11-21: detail place failed).
- 370 k cells in a 2,886 x 1,227 tile. Hops: decoder syndrome pipe 1,540 um (am_a -> am_ok), rck_transport4 -> pv_a 1,209 um, a reset relay to an ft station 1,195 um. 1,141 pins are inside the tile, the rest on W and S only.
- Fix: decoder pipe registers placed as a chain (regions), and the type split proposed for J7. t4 has no placed ODB.

### svc - owner FABLE-FIX-S81-SVC
- No render: no placed ODB exists. 3.3 to 5.1 M cells cannot be placed as one type. Split first; a visual review follows the first placed piece.

### bk_sel t2 - owner S81-BKSEL-R5
- Render: `epyc10 kit, epyc8:.../out/s81_bk_sel_t2/` (3_place.odb, attempt_14, old rows).
- What I see: a 4,329 x 1,227 tile; seven cores in a row fill the upper 80 %; all standard cells live in a 200 um strip along the S edge. Every pin register sits at x 1,200-1,420 on the S face while the cores reach x 4,250.
- Worst setup -2,696: core u_tx (x 3,900) -> output register bout_tl_o0 (x 1,180), 3,196 um, 64 buffers, one cycle. Reset relay rrl_428 -> core rs1 2,113 um, -824. 1,375 hops over 300 um, max 2,518.
- Fix: the chain_r4c rows (flt_o0 writer start, hub re-site, face rows at 200) are the right class. From the picture the dominant need is 10 stations on every u_tx / u_q bus along the S strip, and reset relays every 300 um in that strip.

### kv_leaf t5 - owner FAM-S81-MISC
- Render: `epyc9:.../out/s81_kv_leaf_t5/` (3_place.odb).
- 16 lane cores in two west columns with 21 gaps under 20 um; 759 station flops in those slits (station slit p10 24 um). Worst setup -273, 32 levels, 899 um (mix a3 -> x); reset relay rrl_232 -> vp relay 958 um, -163. RUDY is over 100 % in the slit between the two lane columns (x 150-200, y 380-720) and under core vn_u_a.
- Fix: widen the slit between the lane columns to a 40 um street (space exists east of them), stations out of the slits, one reset relay per lane column.

## 3. QC

### sle_ctl__cla4f6f12f - owner QC-PLAN-R8 (proof kit unowned since FABLE-FIX-QC-SLE stood down)
- Render: `epyc7:.../out/qc_sle_ctl/` (3_place.odb 11-21 07:34 UTC, N46R6V1 attempt_4).
- What I see: station rows cross the whole tile; the two cores u_ctl and u_tap stand in the centre. 19,750 hops over 300 um, max 1,125: bundles from the stations east of u_ctl to the station at (960, 170), and from lpad_b_tw_data (330, 470) over the cores to (660, 330).
- Worst setup -599: lpad_x_fw_p2_i -> core u_tap, 22 levels, 1,377 um of wire for 710 um: u_ctl stands in the way and the route goes round its south side.
- Congestion: the street under both cores (y 320, x 250-860) and the vertical strip at x 215 are over 100 %. All four faces are full (S 5.6 pins / um).
- Fix: (1) swap u_tap to the east of u_ctl (or rotate u_ctl) so fw_p2 reaches u_tap directly; (2) a second street under the cores; (3) stations on tw_data.

### slw_hc3 - owner FAM-QC-HCST
- Render: `epyc7:.../out/qc_slw_hc3/` (5_1_grt.odb 11-17, plan L2; newer V1 attempts stop at gen / place on landing placement, no ODB).
- Clean layout: GRT max 53 %, TT +16.6, hold -17. Two taps over cap (clk 9,196, t113 7,462 against 1,200). 577 hops over 300 um, max 724: xh3.n_d -> output register bout_cw_n3 (N face uses 14 % of its span).
- Fix: split the two big taps; one station on cw_n3. The open failure is the tool class FAM-QC-HCST already owns, not layout.

### slw_st_a_v2 - owner FAM-QC-HCST
- Render: `epyc8:.../out/qc_slw_st_a_v2/` (3_place.odb 11-21 07:58 UTC).
- Median hop 310 um, 9,446 over 300, max 925 (bin_b_tw_data_i -> pd1 r3). Worst setup -96.7: table read register -> core u_r3, 875 um. RUDY over 100 % in 60 k gcells; E / N / S faces at 3.6 to 4.8 pins / um.
- Fix: stations by length on b_tw_data (three), read register at the u_r3 face.

### coll_core - owner FAM-QC-COLL
- Render: `epyc9:.../out/qc_coll_core/` (4_cts.odb, pkw4).
- 29 cores fill a 786 x 1,590 tile; the logic lives in the 20 to 30 um streets between core columns (606 stations in slits under 20 um). 6,975 hops over 300 um, max 1,446: one bundle from the centre (440, 950) to the E face (730, 1,150-1,500), one down the W edge from the NW corner.
- Worst setup -479 (post-hook): sring rdq -> out_data, 24 levels, 1,175 um round core u_fs. Hold -390 on the srl / rrl relay chains (160 um, neighbours on different taps).
- Congestion: streets at x 215 and x 350 between the sram columns.
- Fix: (1) out_data register at the read side of u_fs (the read-register class of pkw4 is right, it needs the register on the near side); (2) relay chains on one tap per chain; (3) one 60 um street instead of two 25 um ones.

### cbf_q00 - owner FAM-QC-CB
- Render: `epyc7:.../out/qc_cbf_q00/` (3_place.odb 11-21 02:24 UTC, N46R4A4 attempt_3).
- Four tile cores of 460 x 1,150; logic in the 150 um centre street and 80 um edge strips. 20,613 hops over 300 um in the centre street and the E strip (lpad_bc_i00 -> tap_d, 665 um).
- Worst setup -438: reset relay rrl_356 -> segment run flags, 46 levels, 1,721 um along the top edge and down the centre. Second -296: latch -> tile core t10, 526 um, 2 levels.
- Fix: (1) reset relay per tile core face; (2) latch stage at the core pin face (tile clock contract of the V2 compose); (3) stations on bc_i00.

## 4. KV and HEAD

### pv (v3 / v8) - owner OPUS-FIX-KV-PV-R4
- Renders: `epyc7:.../out/kv_pv_v3/` (3_place.odb, D25e3 attempt_5); `epyc7:.../out/kv_pv_v8q/` (3_place.odb 11-21 07:28 UTC).
- v3: 783 k cells, 32 cores in a 4 x 5 grid, 60 um streets. One bundle of owner_response_data runs 2,411 um corner to corner (40,945 hops over 300 um). Every street crossing is over 100 % RUDY. Setup -12.5 ns.
- v8q: 597 k cells; hops down to 8,917, but lockup latches sit up to 1,042 um from their capture flop (response_data sg9). One N-S street at x 1,080 carries the tile.
- Fix: the split (D28 / split28) is the only fix that fits the cap. Within it: the response bus needs stations per pvg row, and a lockup latch must sit at its capture bank.

### hgi v8 - owner KV-PLAN-R4 (kit fable-fix-kv-hgi b8)
- Render: `epyc7:.../out/kv_hgi_v8/` (4_cts.odb 11-21 05:42 UTC).
- 16 head cores 4 x 4. TT +51 at CTS, hold -25 on relay chains (srl_244 -> 245, 2 um apart on different taps). Median hop 351 um: 81 % of hops are over 300 um (29,530), max 901 (ectl ring -> bin_i_ectl_Q).
- GRT: 49,891 overflow, all in x 0-480, y 950-1,140, at the ectl_Q landing core on the W face beside head2_e6.
- Fix: (1) move the ectl_Q landing core off the head2_e6 corner or give it a street to the east; (2) relay chains on one tap; (3) stations in every street (the hops are street length).

### hub_C / hub_Eo - owner FAM-KV-HUB
- Renders: `epyc7:.../out/kv_hub_C/` (3_place.odb 11-17), `epyc7:.../out/kv_hub_Eo/` (3_place.odb 11-20).
- hub_C: 968 k cells, 2.4 x the cap; logic is one diagonal river; setup -2,395 on a reset relay path 4,280 um long. hub_Eo: 449 k; bundles of 1,546 um from the W face to the E river; host_die_rst_n -> core astk_EN 2,220 um, -747.
- Fix: split both; reset per bank; W-face buses of hub_Eo need five stations or an E-side window.

### hroot, io_cor_v1, pc_v3 - owners KV-PLAN-R4 (hroot), FAM-KV-IOPC
- Renders: `epyc8:.../out/kv_hroot/` (4_cts), `epyc7:.../out/kv_io_cor_v1/` (3_place 11-21), `epyc8:.../out/kv_pc_v3/` (4_cts).
- hroot: all logic in the east half; the west 45 % is empty but holds 12 taps with 2 to 14 sinks. 4,427 hops over 300 um from the S pin row to clusters at y 400.
- io_cor_v1: sparse, 469 hops over 300 um (three ft bundles of 350 to 457 um); the reset relays fan from one point at (320, 190), as FAM-KV-IOPC found. TT +6.
- pc_v3: one diagonal bundle NW -> SE, 1,283 um, 8,266 hops. Taps t1 and t7 hold 10,960 and 9,982 flops in the centre street. GRT overflow 38,508 at the side cores kvpc1_f and kvpc3_f. Setup -1,508 on host_rst_n -> fault, 98 levels.
- Fix: hroot: drop the west taps, stations on the S row. io_cor_v1: bank_taps rows (in D27c). pc_v3: stations on the slg / o_ctl diagonal, split t1 / t7 into bank taps, 20 um more at the _f core pin faces, reset relay per core.

### HEAD hd_serdes sdr2c - owner FABLE-FIX-HEAD-SERDES-R3
- Render: `epyc7:.../out/head_serdes_sdr2c/` (5_1_grt.odb 11-21 07:38 UTC).
- All logic is one 1,000 x 380 um blob at the S centre of a 2,886 x 1,227 tile. The input pin registers bin_coll_i0 are at x 1,850-2,030, the encoder at x 1,250-1,400: 375 hops over 300 um, max 727.
- Worst setup -103: enc.d0 -> ch_q, 853 um, tap t12 -> t28. Hold -142 inside tap t5 (enc.p_d -> ptx.l, 5 um). The encoder is a patchwork of about 25 taps in 250 x 250 um, as the lane measured.
- Fix: (1) one tap per encoder rank bank (sdr2d direction); (2) coll_i0 window above the encoder or two stations; (3) GRT overflow 651 on the S face x 1,440-2,160: spread the S pin row.

### HEAD hd_lep0N tr2s - owner OPUS-FIX-HEAD-LEP0N-R2
- Render: `epyc10 kit, epyc8:.../out/head_lep0N_tr2s/` (4_cts.odb 11-21 08:32 UTC).
- Four pair cores in the corners; 49 small cores (19 gaps under 5 um) and all 420 k cells in a 330 um band between them. RUDY is over 100 % across the whole band and both edge strips. 6,410 station flops in slits under 20 um. 9,376 hops over 300 um from the N face and the W face into the band (up to 923 um).
- Fix: (1) the m cores into two rows with 40 um streets using the roughly 100 um N-S street between the pair cores; (2) stations in the N-S street, not in the band; (3) the type is over the cap: a split of the band logic is the safe form.

## 5. Whole-die views

- New renders of the live plans (S81 D8i `plan_h2_2249.json`, QC `zz_s29_qc103_s4q9n46r4_final_preview.json`, KV D25e3 `plan_c.json`) with `tools/die_plan/render.py` did not finish: all three hit my 1,500 s limit (rc 124) on epyc8. No live-plan die picture exists.
- Viewed instead (older plans, floor unchanged in outline): `lanes/dieview-s81-1113/s81_die_floorplan.png`, `lanes/dieview-qc-1113/A_floorplan.png`, `lanes/kv-vn2-1112/kv_vn2_floor.png`.
- S81: column frames fill the W and E thirds; the centre holds the leaf grid between two station columns, two slice_C rows, the svc block at the S centre and serdes on the N / S rim. The data flow leaf <-> station column <-> col is consistent with the type pictures. The types that fail on long hops (leaf, slice C, lepe, bk_sel) are the centre types whose pins face three or four neighbours.
- QC: 24 regular columns. Every failing QC family in this review lives in the thin middle band (y 10 to 15.5 mm) or the W edge column, where tiles are narrow and lanes densest.
- KV: column plan with the hub row across the middle. pv is the centre column, hgi the columns beside it, pc at the edges: the same three families that show street-length hops.
- Missing at die level: a current render per live plan. `render.py` needs a fast mode for 250 MB plans.

## 6. Leftovers

- My files: `fable-visual-0030/` on epyc7, epyc8, epyc9, epyc10, intel1 under `/srv/opentallas-scratch2/claude/` (dumps and heat-map CSVs, a few GB per host; `mirror/` on epyc8 2.1 GB). Free to remove with ot-delete once read.
- Local copies of all PNG and stats: localhost scratchpad `img/<label>/`.
