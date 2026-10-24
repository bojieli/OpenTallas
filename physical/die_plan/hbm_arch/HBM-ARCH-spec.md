[CORE-HBM 10-23 20:40] -> HBM-ARCH: HBM LEAF CORE INVENTORY. COORD stopped the d4g re-pin; this is input for the redesign. Data: claude/core-hbm-1023 physical/die_plan/hbm/cores/harden/ (other_status.json; recipes*.json = RTL file lists + params per leaf; canonical_ports_split.json = canonical-port RTL tops for split pieces, rtl/hbm_accel/cores_split/). Synth = ORFS yosys, ASAP7 RVT, TC. "view" = an existing closed LEF/lib view under physical/ref_tile/. pin-reg = register-on-every-pin audit.
- SM: native_col (ln) 253.5k cells / 29.5k um2 + 1 SRAM 64x512, pin-reg 12 unreg; lx (attn) 127.9k / 16.2k + 4 SRAM 128x256, 98 unreg (tcc_* into G1 select); tp 42.5k / 7.1k, PASS. lx<->tp cut is 2,950 b per lx: keep lx+tp in one core (tx = 2 lx + tp ~298k).
- SM svc: group_rel_id 36.5k um2 (FAIL: 1,225 in / 1,234 out unreg, 1,164 const outs); xcal_rel_t 1.2k PASS; xload cl2_bdring 9.6k PASS, view matches; xq_pegress 3.7k (3 unreg in), view.
- VM: kshare_splitstrap 15.4k (3,636 unreg in = the k data straps); calendar_f20_role x3 1.7k each PASS; wb_kport (16 unreg in, fill >70% at plan outline).
- IDX: score hcol (twin ot_hidx_score_hcol HALF 0/1) 198-207k cells / 23.1-24.5k um2 each (x64, needs ~42-45k um2 outline); score tail ot_hbm_idx_tail_native 53k / 6.1k; rootctl_am 10.0k (144 unreg out vm_rq/index_rr); selector_sel + topk_link synth still running (topk_link needed >64 GB); argmax_sw_vm_r2 3.0k (19 unreg in), view; collar_idx256r 2.7k PASS, view = core.
- COLL: tkm tp192 tile (ot_hgi_coll_tkm_tp192_tile_core) 252k / 23.1k x32, tkm root core RTL; gq_land 4.5k PASS, view; gq_issue (1-3 handshake bits); inj_idx_join_rg 7.7k PASS, view; coll_q2 ring_ag/reduce/body piece RTL (body 39 MB generated).
- SFU: split3 lane (ot_hgi_sfu_split3_lane_core) 304k / 36.9k x16 (needs SYNTH_MEMORY_MAX_BITS 16384 for the 15.6-kb LUT); opstore_a/opstore_b/ctl piece RTL (open: sp2 vs plain twin boundary); programme_store_r10 8.6k PASS; dma_back 4.6k (8 unreg in rr).
- SU: pgslice side_softplus / side_rest / lane pieces RTL only, not synthesised (SU was held).
- Other: h9b pc_ctrl leaf 43k / 5.7k + 2 SRAM, routed (see CORE-HARDEN); host_cp_rxs 4.0k PASS; ep_static 3.5k PASS, view; pdie_serdes 402k cells (over 400k), view LEF does not match the plan pins.
Hardening lessons for the redesign kits: pins on the 0.024 lattice; skip M5 PG tracks x mod 4.32 in [1.992, 2.328]; snap SRAM y to the LEF M4 pin phase; CTS -delay_buffer_derate 0.5 on SRAM cores (else -64 ps FF hold on SRAM inputs).
[CORE-HBM 10-23 20:58] -> HBM-ARCH + HBM-P7: FIX REQUEST svc_pc_ctrl_leaf_cfg_h9b (rtl/hbm_accel/loader/service_native/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv; GEOM-REVIEW7 PASS-COND, COORD: register every pin, no tie-offs; then re-REQ GEOM-REVIEW8). I am ending, so I made no RTL change. (1) The 3 'unregistered' inputs are already pin flops, but with a SYNCHRONOUS reset: g_phy_return.v (if(!reset_regions[1]) v<=0; else v<=dram_rvalid, l.84-85), kv_q (reset_regions[4], l.153-155) and kr_rdy_q (reset_regions[5], l.163). Yosys puts an AND gate in front of D, so the pin reaches logic before the register. Fix: give these 3 flops an async reset (always @(posedge clk or negedge reset_regions[i])), the same as ot_dp_st epoch bits; the pin then drives D directly. No cycle change. (2) The 9 constant outputs are port width above what this config uses: col_bank[4:2] (q_cb from cb: 4 banks used of 5 bits), row_row[18:15] (15-bit rows used of 19), kr_beat[3:2] (4 beats used of 4 bits). Fix: parameterise the widths (BANKW=2, ROWW=15, BEATW=2) so the ports shrink, and drop the 9 pins from the plan pins_file (HBM-P7) or the redesign leaf interface (HBM-ARCH). Kit generator and GEOM render are ready to rerun: claude/core-hbm-1023 cores/harden/gen_core_kit.py (recipe recipes_other.json h9b, macro_place). Also open from the route gate: FF hold -64 ps at the SRAM wd_in pins, because CTS puts 9 delay buffers on the SRAM clk (-delay_buffer_derate 0.5 had no effect); try clock_tree_synthesis -no_insertion_delay or post-CTS hold repair on those pins.
[CORE-HBM 10-23 20:58] leaf inventory update: selector_sel + topk_link synth NOT COMPLETED (flat yosys EXTRACT_FA > 40 min-2 h, topk 67 GB): use hierarchical synth (HIER=1) as the die views did. All other numbers in my inventory above stand (claude/core-hbm-1023 @5164894c9 other_status.json).

# HBM-ARCH CONCEPT SPEC v2 (10-23, after COORD early review) -- branch claude/hbm-arch-1023, physical/die_plan/hbm_arch/

## 0. Verdict
**Lead = B2.** B2 is an 8-SM die built from 2 mirrored quad tiles under 1 HBM3E PHY: 25.19 x 18.32 mm = 461.5 mm2 (fits the 26 x 33 reticle).
- G0: PASS.
- G0C: 0 errors on die_io_plan, cut_lines, reach, face_tracks, ft_budget, abutment, faces, complete and replicated-pin tables.
  - The only open item is hard_cores 208 = "no pins listed". These are the CORE pin tables (section 7).
- 49 masters / 88 partitions.
  - NE = MY mirror of NW: 39 shared tile masters, each with one pin table checked by G0.
  - Remaining types: 2 io (the NW one carries the host UCIe), PHY_N, root, and 6 seam chunks.
- d4g failure causes, removed by construction:
  - (1) There is no VM|SU face. VM, the HBM access units (svg / vmks / ctl), COLL, IDX q, SU qcore and HC qhub sit in ONE hub per tile. The SU / SFU / IDX slices abut the hub.
  - (2) There are 0 forced internal stations. Every lane rides an M4-M7 face or a budgeted M8/M9 ft slot. Stations are <= 850 um apart = 0.85 x reach.
- B (v1, 449 mm2) is superseded by B2. A (16 SM, 853 mm2) is not viable (section 5).

## 1. COORD review items (10-23)
**(1) Margins.**
- Router targets: face <= 0.75, ft (transit + M8/M9 endpoint pins) <= 0.80 of the budget. Routing is PathFinder negotiated congestion.
- Endpoint ports go to 3 layers only where a face would pass 0.75 (23 lane hops). Their M8/M9 pins are charged to the ft budget, as are the clock spine tracks.
- Measured on B2:
  - Max face occupancy 0.693 (hub|su10).
  - Max ft 0.788 incl. clock tracks (spt V, the HBM corridor). spu0 V 0.775.
  - Worst die cut 0.133. Worst partition segment 0.44.

**(2) Hub.**
- Was 5.5 x 3.5 mm at 0.34 fill. Now 4.84 x 4.15 mm at **0.45 fill** (6.26M cells).
- Changes that got it there:
  - svg / vmks / ctl moved in, which removed the 13k-bit hub|spu face.
  - SFU core 2x2 sits on its W face and IDX score 2x2 on its E face, so each block gets a whole hub face.
- Hub faces now 0.62-0.68 (mid-range).
- A split into two hubs was tried on paper and rejected: VM <-> SU / x / HBM traffic is ~72k bits per quad, so a split only adds an internal face. Fill is set by the face perimeter that traffic needs.

**(3) Spines.**
- They are intentional M8/M9 corridors, and are now sized to need:
  - SM-row spine spt/spb narrowed 2039 -> 1814 um (spt V 0.787 = HBM PHY <-> hub corridor).
  - The SU-row spine spu keeps 2506 um (V/H 0.6-0.75) by trimming the SU near halves (fill 0.75).
- The bottom spine spb0 now holds the S-edge SerDes (beachfront).
- Still empty:
  - spb1 and vsN1/vsN2 (seam beside the bottom SM row): ~3 x 2.7 mm2.
  - The two PHY-row corners mca (2 x 8.7 mm2 = 3.8% of the die). They are reserved for die PLL / clock gen, thermal, test/JTAG and decap.
- The die width is set by the SM rows (2 x 5046 + spine per tile). The empty corners are a consequence of the centred PHY over two tiles.

**(4) HBM path per SM row** (hbm_rows.json; the controllers sit in the hub):
| leg | bits | mean / max cycles | mm per bit | bit-mm |
|---|---|---|---|---|
| PHY -> hub | 4112 | 17.5 / 25 | 10.9 | 44.9k |
| hub -> PHY | 5248 | 15.9 / 29 | 10.4 | 54.5k |
| hub -> SM, near row (sm0/1) | 6850 | 5.8 / 12 | 2.6 | 17.8k |
| hub -> SM, far row (sm2/3) | 6850 | 7.6 / 9 | 3.8 | 26.3k |
| SM -> hub near / far | 554 | 8.5 / 10.0 | 4.7 / 5.5 | 2.6k / 3.1k |
- Read path PHY -> hub -> SM: **near 22.3, far 24.1 cycles.** The asymmetry is small because the hub sits between the rows.
- The static schedule uses per-SM fixed offsets: the plan latency table feeds CAL-AUTO.
- **The price uses the far row** (SM_HBM 25.1 incl. the P5 +1).

**(5) Masters.** 88 as-placed types became **49 masters**.
- NE instances are orient MY. Windows, slots and buses are mirror-generated, and G0 checks for identical pin tables.
- The as-built per-quadrant variants (__pvN, glue_nw_t; quant / idx_share / vmm present only in NW) become one hub master plus a quad-ID strap (RTL delta).

**(6) G2 + array.** See section 10.
- HBM-NET array_net_1017 verdict_c: 384 8-SM dies reach one tier only with 100G single-lane ports (TU 512 x 100G, 32 planes, 12,288 cables). That port mode is not primary-source-confirmed for TU; without it the array is a 2-tier Clos (3 x 377.6 ns).
- **Asks HBM-NET to confirm.**
- B2 keeps the d4f SerDes per die: 5 macros x 6 lanes on the beachfront.
  - W/E io: N0, N2.
  - S edge: vsN0 S1, plus spb0 S0/S3.
  - Host UCIe in NW io.

## 2. Die (B2)
- Each quad tile, NW frame, memory side up:
  - [SM0 | spt | SM1]
  - [su00 su01 | spu0 | su10 su11]
  - band: [io | sfuc 2x2 | HUB | idx 2x2 | hc ring 4 cols x 2 rows]
  - [su20 su21 | spu1 | su30 su31]
  - [SM2 | spb | SM3]
- The NE tile = MY mirror.
- The vertical seam between the tiles: root at band + SU height; vsN chunks beside the SM rows. The hc ring sits next to the root (hc_eng), so no ring crosses the tile.
- PHY_N is centred: 8502 x 1184 macro, 1900 signals at 55 um. PHY row height 2074.
- IO: UCIe host 144 at 45 um, plus 5 SerDes. die_io_plan: 0 errors.
- Lanes: 298 lanes / 204.6k bits; 1650 ft stations, 0 forced.

## 3. Fabric, static schedule, collectives
- Neighbour-only links, registered at both faces. ft slots on M8/M9 with stations at <= 850 um.
- Class stages measured from the plan (stages_arch.py, P5 SM-split adders):
  - SM_HBM 25.1 (far, incl. PHY leg)
  - SM_X 8.6
  - SM_OUT 13.0
  - HBM_VM / VM_HBM 2 (in hub)
  - VM_RING 17.0
  - COLL_VM 2
  - COLL_EP 7.0
  - HC_CORE 10.0
  - HC_ENG 10.3
  - SU_CORE 4.3
  - SFU_CORE 4.2
- Static schedule: the compiler places every transfer on a fixed calendar. There are no credits or backpressure on die. Elastic boundaries exist only at HBM, SerDes/d2d and host.
- Collectives:
  - Tree inside a quad, to the hub COLL engine.
  - Ring of 2 between the quads through the seam: VM ring 2838 b/dir.
  - Die root (tkm etc.) in the seam to 5 SerDes endpoints. Array ring/tree as in c_L4 (2 COLL engines x 2 delivery lanes).

## 4. Clock, reset (OWNER decision via COORD 10-23: industry multi-source CTS)
- **Structured symmetric H-tree on M8 (H) / M9 (V).** See clock_htree.py, B2/clock_htree.json and B2/clock_htree.png.
  - Wires: NDR 2W2S + VSS shields = 5 tracks per wire.
  - Trunk: a balanced binary tree ALONG THE SEAM (M9) from the root at the die centre to 4 rib nodes.
  - Ribs: at each rib node, a mirror pair of W/E ribs (M8), each a balanced H-tree over its tile band.
  - Leaves: 256 tap drivers on a uniform 16 x 16 grid (cell 1.57 x 1.14 mm). Each drives the R4 partition taps (<= 400 um) of its cell by a short local tree.
  - Size: 510 segments, 8 levels.
- **Seam neighbours on the same branch.** NW_x and NE_x at the same height hang off the same rib node. Their common path is the whole trunk, which CPPR removes, and the W/E ribs are mirror-identical.
- **Hard cores.** SM and PHY each take one clock pin. Leaf delay = common latency 250 - the core's lib insertion, so the core's pin flops land on the common latency.
- **Reservation.** The spine's tracks are charged to the ft budget per type: type ft_budget M8/M9 = 0.6 - reserved / usable tracks. The router counts them too. The worst type is spu0 V, 30 tracks.
  - With the spine included, max ft is 0.788.
- **Gate.** Related-pair skew with CPPR <= 80 ps at TT and FF (kit STA / CP1 method). Common latency 250.
- **G2 die probe** routes the clock and reset spines with 0 overflow (section 10).
- **Reset.** Regional async-assert / sync-deassert per partition. Pin flops use async reset (the h9b lesson).

## 5. Comparison (pricer plan_study_price_1017, X 377.6)
| metric | d4g | A (16 SM) | B (v1) | **B2** |
|---|---|---|---|---|
| die mm2 | 667 | 853 | 449 | **461.5** (25.2 x 18.3) |
| dies in array | 1x | 1x | 2x | **2x** |
| masters / partitions | 60 / 187 | 185 / 185 | 88 / 88 | **49 / 88** |
| lanes / bits | 5483 / 1.01M | 728 / 504k | 346 / 226k | **298 / 205k** |
| bits per mm2 | 1517 | 590 | 504 | **443** |
| bit-mm (mm/bit) | 1.78M (1.76) | 1.91M (3.80) | 0.59M (2.61) | **0.66M (3.21)** |
| ft stations (forced) | 22,973 (1511) | 4,450 | 1,771 (0) | **1,650 (0)** |
| max hop/reach | 0.74 | 0.85 | 0.85 | **0.85** |
| worst cut / partition seg | 0.145 / 0.27 | 0.169 / 0.64 | 0.099 / 0.34 | **0.133 / 0.44** |
| max face / ft util | -- | >1 / 1.76 | 0.89 / 0.83 | **0.69 / 0.79** |
| G0C plan errors (excl. pin tables) | 1,644 | 754 | 0 | **0** |
| AR tok/s | 1896 | (2083\*) | 1780 | **1671 (-11.9%)**; 1756 (-7.4%) d4g convention |
| MTP tok/s | 3214 | (3606\*) | 3049 | **2840 (-11.6%)**; 3001 (-6.6%) |
| Qwen tok/s | 945 | (964\*) | 917 | **908 (-3.9%)**; 915 |

- \* A is priced on a non-closing plan.
- B2 headline = conservative, with SM_HBM = the full PHY -> hub -> far-SM path.
- "d4g convention" = SM_HBM from the service partition to the SM only. That is how d4g and B were priced: their PHY -> ctl leg was not counted. For B, that leg is ~6 mm.
- All values are within the 15%/design budget.
- c_L2 (1 lane per COLL engine) would be 1391 / 2389. **B2 needs the c_L4 2-lane delivery.**
- Lever for later (not taken): put svg + ctl for the near SM row at the PHY row. That cuts SM_HBM for half the SMs, but moves 16k bits of vmks<->ctl traffic onto the spine.

## 6. Files (branch claude/hbm-arch-1023)
- physical/die_plan/hbm_arch/:
  - gen_arch.py (--variant A|B|B2)
  - emit_mirror.py (mirror router, PathFinder, 3-layer endpoints)
  - roles.py
  - finalize.py
  - stages_arch.py
  - hbm_rows.py
  - metrics.py
  - B2/ (die_plan.json, g0/die_plan.png, g0c, hbm_rows.json)
  - price/ (st_B2*.json, price_B2*.json)
  - A/, B/ (kept for the comparison)

## 7. Core list (CORE-HBM leaf facts; every core <= 400k cells, registered on every pin)
- **SM**: tx = 2 lx + tp (~298k; lx<->tp cut 2,950 b, kept in one core). native_col 253.5k.
- **Hub, HBM access**:
  - group_rel_id: **pin-reg FAIL** (1,225 in / 1,234 out unregistered; drop 1,164 constant outputs).
  - xcal_rel_t: PASS.
  - xload cl2_bdring: PASS.
  - xq_pegress: **FAIL**, 3 in.
  - h9b svc_pc_ctrl_leaf_cfg: **FAIL**. Fixes:
    - Async-reset pin flops for g_phy_return / kv_q / kr_rdy_q.
    - Ports BANKW=2, ROWW=15, BEATW=2 (drops 9 constant pins).
    - SRAM-clock hold -64 ps at FF: clock_tree_synthesis -no_insertion_delay, or post-CTS hold repair on wd_in.
- **VM**:
  - kshare_splitstrap: **FAIL**, 3,636 k-strap inputs; register at the bank face.
  - wb_kport_q: **FAIL**, 16 in.
  - calendar_f20 x3: PASS.
- **IDX**:
  - score hcol HALF0/1, ~200k, x16 per idx partition. tail 53k.
  - rootctl_static_am: **FAIL**, 144 out.
  - argmax_static_sw_vm_r2: **FAIL**, 19 in.
  - collar: PASS.
  - selector_sel and topk_link: **hierarchical synthesis (HIER=1)**. Flat yosys stalls; topk_link peaks at 67 GB.
- **COLL**:
  - tkm tp192 tile 252k x32 (root).
  - coll_gq_issue: **FAIL**, handshake bits.
  - gq_land, inj_idx_join: PASS.
  - coll_q2 pieces: RTL only.
- **SFU**:
  - split3 lane 304k x16 (SYNTH_MEMORY_MAX_BITS 16384).
  - programme_store: PASS.
  - dma_back_static_vp4_banks_cp: **FAIL**, 8 in.
- **HC**:
  - hc_qhub: **FAIL**.
  - Over cap, split before kits:
    - hcb bank_q ~840k: split into 3 x ~280k.
    - hc_eng root 1.51M: split into 4-5 x <= 350k.
- **SU**: pgslice pieces are not synthesised. This is the first CORE item, because SU sets the SU-row fill (0.69-0.75).
- **IO**:
  - **pdie_serdes 402k: split** into lane core + ctl (2 x ~200k). Re-pin it: its view LEF does not match the plan.
  - host_cp_rxs, ep_static: PASS.
- **Pins**: top-down from the plan with re-pin v3c (connectivity-aware, claude/core-hbm-1023).
  - Pins on the 0.024 lattice, avoiding the M5 PG tracks. SRAM y snapped to the M4 phase.
  - This clears G0C hard_cores (208).

## 8. RTL deltas (after sign-off only)
1. Quad hub wrapper: VM + 8 banks + svg/vmks/ctl + COLL + IDX q + SU qcore + HC qhub, plus a quad-ID strap that replaces the per-quadrant __pvN variants.
2. Registered band interfaces for SFU / IDX / hcb slices.
3. 8-SM die top: 2 tiles, seam root, 1 PHY, 5 SerDes. TP split s=4, G1=384, c_L4 delivery.
4. The 10 pin-reg FAIL fixes.
5. Splits: pdie_serdes, hcb, hc_eng.

## 9. Risks
- SU pgslice cells are unknown. Near-half fill is 0.75, so there is little room: if SU grows more than ~10%, SUH grows.
- Array: one tier needs the TU single-lane port mode (HBM-NET).
- HBM read latency, conservative SM_HBM 25 vs d4g ~6: -12% AR is inside the budget, but it is the largest single cost.
- Empty corners: mca 3.8% of the die.

## 10. G2 (B2)
- Probes are read-only OpenROAD GRT in docker on ot-epyc7, from plan B2 r1. B2 r1 is the same partitions as the final B2; the final adds the 2 S-edge SerDes and the clock reservation.
- **Die probe** (clock + reset spines on M8/M9, partitions blocking M1-M7, PG grid): **0 overflow**.
  - Wirelength 594 mm. M8 usage 0.01%.
  - root -> tap reach: clk max 21.2 / p90 15.2 mm over 980 taps; rst max 18.6 mm.
  - The H-tree above makes this a balanced structure. Insertion is common up to the leaf (CPPR).
- **Partition FT probes** (exact pins, a boundary flop per pin bit, ft stations, GRT M2-M9, adjust 0.5): all **0 overflow, 0 pin-access warnings**.
  - q_b000 (hc ring bank): WL 3.65 m; M2 9.2%, M4 10.7%, M8 6.0%.
  - q_b102 (IDX slice, E-W transit 0.79): WL 6.09 m; M4 15.6%, M6 10.2%.
  - q_spu0 (SU-row spine, HBM corridor): WL 31.6 m; M2 28.3%, M3 19.9%, M5 8.5%.
  - q_su01 (SU near half): WL 14.4 m; M3 10.3%.
  - q_su30: WL 15.7 m; M2 21.4%.
  - q_hub (80,085 pins / flops): **0 overflow** on every layer (M2-M9 at <= 0.06%); pin access 160,298 pins with 0 lacking an access point. Total wirelength 570 mm. The probe peaked at 132 GB and ran 41 min of DRT pin access, so the hub kit is pin-heavy. Its kit needs a >= 160 GB admission (or the R8 bus groups to halve the boundary flops).

