# HBM-NEXT-DIE: P = 4 next-release HBM die floorplan (2026-10-19, not a release gate)

Lane HBM-NEXT-DIE (programme HBM-NEXT-PROG, owner go 10-19 00:05). Branch `claude/hbm-next-die-1019`, merged into `claude/hbm-next-1019`.

**Basis.** The frame is the d4g GEN2 plan, COPIED to `physical/hbm_next/die/frame_d4g_copy/`. The d4g plan, grants, GEN2 scripts and rp4lp pin file are copied verbatim; no GEN2 file is edited.

**Evaluator.** All numbers come from the d4g plan tool chain, used read-only:
- `plan_study_1017.write_plan` provides the v6_eval pins and lanes, the sliding-window pin cut with full PHY-row supply, `hbm_globalfp` bit-mm and the 480-um lane stages.
- The chain reproduces d4g exactly: 641.83 mm², cut 0.397/0.431, 0.797 M bit-mm, stages_bw 7.035.

**SM column at P = 4 (stand-in until SM4 publishes `sm4/geometry.json`).**
- MTP-AREA measures +99.83 mm² over 16 SMs, which is +6.24 mm² per SM column (13.49 → 19.73 mm²).
- The column stays a 4 x 4 grid of rp4 tiles with 2 leaves each. Each P = 4 tile (`hnx_rp4lp4`) holds 2 leaves x 4 lanes of {bdc, tcl x2, tct, xs}.
- Tile size is 673.92 x 1684.8 um = 1.135 mm² (≥ 1.122 needed). It is on the 43.2-um lattice (+5 / +2 lattice steps) with aspect 2.5:1, against 3.5:1 today.
- The column is 2,803.68 x 7,300.8 um.
- x-only tile growth (717.12 x 1598.4) would make the SM row 26.66 mm, wider than the 25.5-mm usable reticle short side, so it was rejected by construction.

## ADOPTED (Phase-1 binding constraints, STUDY.md @ claude/hbm-next-1019 794bd51a0): `f4c_t5`

Phase-1 (HBM-NEXT) made two things binding:
- the taller re-shaped SM tile, ~632 x 1,824 um (frame 23.8 x 31.5 = 752 mm²);
- 5 COLL delivery lanes.

`f4c_t5` applies both to the f4c re-pack:
- **SM tile.** 630.72 x 1,814.4 um on the 43.2 lattice (+4 / +5 steps) = 1.144 mm² ≥ 1.122; aspect 2.9. The SM column is 2,631.0 x 7,819.2 um.
- **COLL.** L = 5 delivery lanes, giving COLL_VM / COLL_RING / COLL_EP bits x1.25.
- **SU groups.** The SU-group HC-client / SFU-group plan blocks are set to the GEN2 grant outlines (216 um, slot 259.2 um), not the d4f-era 500 x 500 / 500 x 800 placeholders. This lets the one-row quadrant band fit the 11.7-mm quadrant.

| plan | die mm | mm² | cut v / h | bit-mm | stages_bw | longest | relay flops at 405 (landed regions) | reticle margin short / long |
|---|---|---:|---|---:|---:|---:|---:|---|
| d4g (P = 1) | 20.20 x 31.77 | 641.8 | 0.397 / 0.431 | 0.797 M | 7.04 | 10.8 mm | 2.24 M | 5.80 / 1.23 mm |
| f4w_t: Phase-1 tile, d4g band template grown | 23.89 x 33.50 | 800.4 | 0.407 / 0.433 | 0.810 M | 7.21 | 10.5 mm | n/a | **fails reticle** (33.5 > 32.5) |
| **f4c_t5 (ADOPTED)** | **23.89 x 29.01** | **693.1** | **0.469 / 0.399** | **0.694 M** | **6.23** | **10.0 mm** | **2.01 M** | 2.11 / 3.99 mm |
| f4c_t + COLL x2 reserve | 23.89 x 29.01 | 693.1 | 0.585 / 0.417 | 0.808 M | 6.69 | 10.0 mm | | |

**Frame size.**
- The Phase-1 frame arithmetic assumed the d4g band and got 31.5 mm. Put through the d4g evaluator (f4w_t), the d4g band with the Phase-1 tile comes out at 33.5 mm, over the reticle.
- The re-packed band makes the die 693 mm²: 59 mm² under the 752 budget and 50 under ~743. That slack is reserve for:
  - the HC N-row engine (Phase-1 gate 1);
  - the VM growth Phase-1 calls "worth doing if the area is free" (2^18 → 2^18.6 words, +~0.6 x VM);
  - the real SM4 / ATT4 outlines.

**Clocking.** 76 regions, all ≤ 4 mm except the SM columns, which carry their inner landed regions. There are 369 landed crossings (206402 b). The maximum hop count is 30.

**Pins.**
- hnx_rp4lp4 W/E: 3,705 pins each, densest 3.3 / um.
- COLL W face 5.05 b/um at L = 5, which is ≤ 6.
- File: `physical/hbm_next/die/f4c_t5/`.

**Die case (stand-in integration, fleet ot-epyc4, 2026-10-19 ~00:55): GEN_OK.**
- The case is `case_f4c_t5`. Artefacts are in `case_f4c_t5/`: `layout.png`, `gen_summary.log`, `overreach_case_f4c_t5.log`.
- Placement: 1,214 instances, 1,058,039 nets, 942 homes, 0 placement problems, 0 excluded.
- Clock (regional): 66 stream regions, 835 / 4,523 / 9,834 clock buffers (hbm / serial / stream), the same scale as GEN2a.
- The reset gate gives FAIL_DIAG with no_regional_tree x1,857. This is the same as the d4g GEN2a baseline in diag mode, and the reset forest belongs to the release chain.
- Overreach on the relay-free case at the 405-um hop: **682,640 nets against 710,093 for d4g GEN2a on the same contract and views (-3.9 %)**. The worst RELAY net is 27.1 mm against 26.1 mm.
- The first try (`f4c`, older grants) failed: there was no placed pin `pll_hbm` on the ckgen slot (fixed in GEN2 3ca4d2b98, so the 3ca4d2b98 grants are now copied), plus 2 PHY-row overlaps (the PHY-row leaves now keep their d4g PHY offsets).

The sections below record the first pass (f4c, the D2-scaled tile 673.92 x 1,684.8). Their method, cuts and costs carry over to f4c_t5, with these per-plan numbers:

| | f4c_t5 |
|---|---|
| SM_HBM | 5.25 stages |
| SM_X | 6.46 stages |
| COLL_VM | 14.5 hops at 405 |
| COLL x2 reserve | 0.585 |

## 1. Floorplan candidates (`plan/plan_p4.json`, PNGs in `plan/`)

| plan | die mm | mm² | density | cut v / h | bit-mm | stages_bw | longest link | relay flops (graph) | reticle margin short / long |
|---|---|---:|---:|---|---:|---:|---:|---:|---|
| d4g (frame, P = 1) | 20.20 x 31.77 | 641.8 | 0.655 | 0.397 / 0.431 | 0.797 M | 7.04 | 10.8 mm | 1.48 M | 5.80 / 1.23 mm |
| f4w: frame grown, nothing re-packed | 25.27 x 32.46 | 820.5 | 0.648 | 0.402 / 0.472 | 0.808 M | 7.23 | 10.2 mm | 1.51 M | 0.73 / 0.54 mm |
| **f4c: re-packed (PROPOSED)** | **25.27 x 27.97** | **707.0** | 0.753 | **0.484 / 0.468** | **0.691 M** | **6.33** | **9.9 mm** | **1.28 M** | 0.73 / 5.03 mm |
| f4c + COLL x2 payload reserve | 25.27 x 27.97 | 707.0 | 0.753 | 0.585 / 0.413 | 0.854 M | 6.98 | 9.9 mm | 1.59 M | same |
| f4c, VM hub mid-quadrant | 25.27 x 27.97 | 707.0 | 0.753 | 0.527 / 0.413 | 0.755 M | 6.82 | 14.7 mm | 1.41 M | same |

**Why f4c.**
- **f4w.** Growing the frame widens the die by 5.07 mm and the height by 0.69 mm. Its 820 mm² is mostly white space at the band edges, and it eats the long-side reticle margin (535 um against the 500 required).
- **f4c re-packs the band for the wider quadrant (12.4 mm).** Each quadrant gets:
  - one row of 8 VM banks lying directly on the SM row's inner face. SM_X (34.9 kb, the largest class) drops from 10.37 to 6.8 bit-weighted stages, and the LG links become 0–3 stages.
  - above that, one row of the 4 SU groups (SU slot + SFU group + HC client, plus the quantiser in the bank row).
  - at the inner end, beside the 400-um centre lane channel: the VM hub, SFU core, HC engine slot and the small core column (DMA back, SU core, SUCX, HC client, CIJ, IDX query).
- **The centre strip (1.8 mm) holds:**
  - the SerDes pairs at the die edges;
  - the COLL engine pairs (S over N, so the COLL N/S ring hop is adjacent), at 4.5 mm from the centre line;
  - the SFU programme stores;
  - the IDX selector/link, top-k merge, IDX die control and host CP.
- **COLL position sweep** (bit-mm / stages_bw / longest), for the COLL pair centre at 0.6, 2.5, 4.5, 6.5 and 8.5 mm from the centre line:
  - 0.742 / 6.85 / 12.7
  - 0.723 / 6.65 / 11.6
  - **0.691 / 6.33 / 9.9**
  - 0.678 / 6.26 / 11.9
  - 0.674 / 6.25 / 15.9

  4.5 mm was picked for the shortest longest link (the COLL ring latency matters: COLL is co-critical at P ≥ 2). The 2.5-mm point has a 0.585 window.
- **Area.** 707 mm² is 36 mm² under the programme's ~743 (641.8 + 101 as a sum of block areas). The re-pack removes the band white space instead of adding it. The slack is reserve for the non-SM unit growth (IDX query store, Sinkhorn x2, the COLL x2 outline) and for the SM4 / ATT4 real tile outlines.
- **No empty area on link paths.** The quadrant core sits against the centre channel. The banks sit against the SM row. The white space left is at the band's outer ends and around the PHY corners, and no link crosses it.

**Costs of f4c (and of any P = 4 frame with this SM row).**
- **SM_HBM grows from 2.88 to 5.88 bit-weighted stages.** The outer SMs sit 7.2 mm from their PC (4.2 mm in d4g), because the 8 SM columns now span 25.2 mm over an 8.5-mm PHY.
  - SM_HBM is a fixed-latency static lane (SM_HBM / HBM_K widths unchanged).
  - The +3 stages (+~1.5 cycles at half-cycle hops) are paid once per SM record. That is noise against ~1.4 M verify cycles a step (as D2 §5).
- **COLL_RING / COLL_EP longest links are 9–10 mm** (5.8 in d4g). VM_HUB and HBM_VM are unchanged or better.

## 2. Cut analysis (BEFORE RTL; rule ≤ 0.55–0.60)

The measure is the same as d4g: a sliding 1-mm window pin cut over usable tracks with full supply over the PHY rows (`cut_phy_unmasked`).

| cut | d4g | f4c | f4c + COLL x2 | note |
|---|---:|---:|---:|---|
| worst vertical window (hub / quadrant core) | 0.397 | **0.484** (x 13.6 mm, y 11.2–12.2: quadrant-core column) | 0.585 (x 7.1 mm, COLL_VM lanes) | within 0.55 at x1; x2 at 0.585 is inside 0.60 only if the COLL_VM lanes are spread (see below) |
| worst horizontal window | 0.431 | **0.468** (y 17.2 mm, band-to-strip face) | 0.413 | |
| SM column N face, xw window | 2,063 b over 360.72 um = 0.549 (5.72 pins/um) | 2,063 b; the face is 2,803.68 um, so the window can widen to ~720 um: **~0.28** (2.9 pins/um) | same | lane addressing is internal, so bits are unchanged (D2 §2) |
| result window (SM_OUT) | 271 b | 271 b (lane-major publish + 1-b lane tag) | same | |
| COLL ring / EP face | coll W face 4.67 b/um (x1) | same | **9.3 b/um: over 6/um**; the COLL outline must grow ~1.6x (1080 x 880 → ~1300 x 1300; the strip has room) | from UNITS/CMTP P = 4 collective BW |
| PHY-masked measure (`cut_lanes`) | 0.397 | 1.088 at x 9.1 mm in the N PHY row | same | the known PHY-row supply-mask artefact (d4f_a2p README pc637): the HBM_K lanes enter the PC row there; the unmasked rule above is the adopted measure |

**Rule result.** f4c passes at ≤ 0.55 with the as-built COLL widths. With the COLL x2 reserve, the plan passes at 0.585 (within 0.55–0.60). Two prerequisites come first: a COLL outline growth, and spreading the COLL_VM bank lanes over two lane rows. Both are recorded as DIE-P4-2 in the pending list.

## 3. Clocking plan (landed regions, 10-18 standard): `clock_plan_f4c.json`, `physical/hbm_next/die/f4c/region_map_hnx_f4c.json`

**Regions (75; d4g has 45).**
- One region per SM column (16). Inside each, the column parent holds 16 rp4 tiles x {ck_n, ck_s} landed regions in the PL-SMT form. It is judged per linked child pair at the child flops: TT and FF ≤ 80 ps.
- 2 PCs per region (8), 1 region per PHY, per IDX corner (4) and per XQL pair store set (8).
- 1 region per SU group: bank pair + SU slot + SFU group + HC client, ≤ 2.4 x 3.4 mm (16).
- 2 per quadrant core: VM hub / SFU core / HC engine, and the small core column (8).
- 1 per config leaf, and 3-mm strip boxes.
- The largest non-SM region is 3.43 mm (`core_SW`). **No region exceeds 4 mm. No balanced or zero-skew tree spans more than one region.**

**Crossings.** Every link between regions is a LANDED crossing: a 4-slot ring with fixed latency and no backpressure (lanes/LANDING-CONTRACT.md), placed at the sink block input. There are 370 of 482 plan links (200.7 kb). The intra-region links are the LG bank→SU/SFU/HC links, QUANT_VM and HBM_K.

**Reach.** Links are planned at 405 um with repeaters inside registered hops, using forwarded half-cycle relay hops on the long lanes.
- Relay flops at 405: **1.99 M against d4g 2.24 M (-11%)**. The maximum hop count per link is 28 (d4g: 33).
- Per class (bit-weighted hops / max):

  | class | hops | max |
  |---|---:|---:|
  | SM_X | 8.1 | 28 |
  | SM_HBM | 6.9 | 13 |
  | HC_CORE | 17.7 | 28 |
  | COLL_VM | 15.1 | 24 |
  | VM_HUB | 16.0 | 26 |
  | HBM_VM / VM_HBM | 22.5 | 25 |
  | COLL_RING | 12.3 | 26 |

**Boundary.** Each neighbour pair (180 pairs, outlines within 600 um) is matched by parent compensation or by the landing. No absolute-insertion or sink-count split is applied (owner 10-17).

## 4. Pin plan (top-down, owner 10-13): `physical/hbm_next/die/f4c/pin_plan_f4c.json`, `hnx_rp4lp4_pins.tcl`

**`hnx_rp4lp4` (673.92 x 1684.8).**
- The pin set is the rp4lp set unchanged: W rin/bin, E rout/bout, N gin/xs/rst_n/ck_n, S gout/xss/ck_s. The source is the rp4lp pin file of claude/pl-smt-1018 2444d768c, copied.
- Faces, layers and order are kept. Positions are scaled x1.472 on N/S and x1.054 on W/E, so the 4 x 4 abutment stays aligned.
- Pins per face: W/E 3,705 each, densest 3.5 pins/um per 10 um (3.7 before); N 128; S 227 (1.6 / 1.5 per um).
- ck_n / ck_s keep their face sites, beside each landed region's register mass. Pin registers come by default (the rp4lp pin_regs.json carries over).

**`hnx_rp4a4`.** The same set, plus the ATT4 line-mask input (P bits per KV line) on the N face beside gin. Pending ATT4 geometry.

**SM column parent (P = 4).**
- The plan pin model gives ≤ 0.4 b/um on every face.
- The real xw window: 2,063 b on the N face, which can be spread to ~720 um (2.9/um). SM_HBM enters on the S face.

**COLL.** The W face is 4.67 b/um at x1 and 9.3 b/um at x2. At x2 the outline must grow before the ≤ 6/um rule holds (§2).

## 5. Early die-level integration with stand-ins (fleet): `physical/hbm_next/die/hnx_case.sh`

The run is a relay-free die placement case in the GEN2a form. Inputs:
- the GEN2 pre-relay contract (1,214 instances) and the GEN2 views (`src_1e3a3fcb5` tree);
- **the SM stand-in**: the as-built P = 1 `smh_attn` view, centred in each P = 4 column slot on its inner edge;
- the hnx plan / lanes;
- `grants_hnx_f4c.json`: the d4g grants moved with their plan blocks. 96 non-plan GEN2 slots (COLL sub-tiles, programme stores and slices, calendars, fault leaves) are homed nearest-free beside their functional anchor, inside their own quadrant. The GEN2 corner engines are placed as GEN2 places them: idx_s0 / idx_s1 in the W PHY corners, the single hc_eng in the S-E PHY corner;
- `region_map_hnx_f4c.json`;
- regional clocks, die repeaters at 405, and the reset gate in diag mode.

The result is in `case_f4c/` (see the lane file). The input file is `physical/hbm_next/die/f4c/`.

**Finding (the GEN2 element set vs the plan graph).**
- The plan graph (H-PLANSTUDY) carries 4 quadrant HC engines (`hce_*`) and 4 IDX scorer quarters (`idxs_*`).
- GEN2 actually binds ONE `hc_eng` (5,223 x 1,953 um at the S-E PHY corner) and two `idx_s` scorers (4,764 x 1,953 at the W PHY corners).
- f4c keeps the `hce_*` slots in the quadrant core as reserved area, for D2 risk M2 (HC row II) and the 2 extra Sinkhorn units. The stand-in case uses the GEN2 single engine.

## Files

| file | contents |
|---|---|
| `tools/hbm_next/die/plan_p4.py` | plan generator + evaluation + plan / flow PNGs |
| `tools/hbm_next/die/hnx_case_inputs.py` | grants + region map for the die case |
| `tools/hbm_next/die/clock_plan_p4.py` | region / landing / 405-hop accounting |
| `tools/hbm_next/die/pin_plan_p4.py` | tile and parent pin plan |
| `results/arch/hbm_next_1019/die/plan/` | the plans; `f4c.png`, `f4c_flow.png` (flow PNG), `f4w*.png`, `f4c_collx2*.png`; `plan_p4.json` |
| `results/arch/hbm_next_1019/die/clock_plan_f4c.json`, `clock_plan_d4g_ref.json` | the clocking plan, and the same accounting for d4g |
| `physical/hbm_next/die/frame_d4g_copy/` | the copied d4g frame (plan, graph, plan_d4g.py, d4g_sm_frame.py, gen_d4g2.sh, rp4lp pins) |
| `physical/hbm_next/die/f4c/` | grants, region map, pin plan, `hnx_rp4lp4_pins.tcl` |

## STEP 2 (10-19 ~01:30-02:10, fresh DIE agent): PROG decisions, COLL L=5, SM lever frames, SM_HBM cost, relay/landing chain

All plan numbers: `tools/hbm_next/die/plan_p4.py` (new options `--hc one|quad`, `--vm-dh`, `--vm-dw`, `--coll-l5`), same d4g evaluator; reproduces f4c_t5 exactly (693.09, 0.469/0.399, 0.694 M). Plans + PNGs + flow PNGs in `plan/` (`plan_p4.json`).

**ADOPTED f4c_t6c** = f4c_t5 + VM 412k + ONE HC engine as root + 4 ring quarters in the quadrant slots + COLL L=5 as UNITS-COLL measured it:
23.89 x 29.01 = **693.09 mm²**, cut **0.484 / 0.490**, bit-mm **0.669 M**, stages_bw **6.03**, longest 10.0 mm, 0 overlaps, reticle margins 2.11 / 3.99 mm.

| plan | mm² | cut v / h | bit-mm | stages_bw | longest | note |
|---|---:|---|---:|---:|---:|---|
| f4c_t5 (step 1) | 693.09 | 0.469 / 0.399 | 0.694 M | 6.23 | 10.0 mm | COLL x1.25 on VM/RING/EP |
| f4c_t6: + VM 412k | 693.09 | 0.484 / 0.414 | 0.690 M | 6.17 | 10.0 mm | VM bank +86.4 um tall (5 macros) |
| f4c_t6e: VM 524k (Engram ~490k option) | 693.09 | 0.478 / 0.400 | 0.688 M | 6.19 | 10.0 mm | bank +151.2 um (6 macros) |
| f4c_t6_hccorner: ONE engine at the S-E PHY corner (GEN2 place) | 688.18 | **0.879** / 0.499 | 0.901 M | 7.82 | **22.8 mm** | REJECTED |
| **f4c_t6c: t6 + COLL L=5 measured** | **693.09** | **0.484 / 0.490** | **0.669 M** | **6.03** | 10.0 mm | ADOPTED |

- **VM >= 412k words (PROG decision 1).** The VM bank holds 3 x ot_sram_1r1w_1024x256 (2^18 words). 412k needs 5 macros (437k), the ~490k Engram option 6 (524k).
  - The bank slot is pin-perimeter bound (31 % fill), so the extra macros are stacked in one column, keeping the 47-um pin ring. That makes the bank +86.4 um tall (5 macros) or +151.2 um (6).
  - **Die cost: 0 mm² for both.** The quadrant band's height is set by the HC quarter column (SFU core + HC slot, 3.43 mm), and the taller bank row (rowB +86 / +151) stays under it.
  - The Engram ~490k delta is therefore a free option in area. Its cost is 32 more macros only (bank fill 47 % -> 57 %).
- **ONE HC engine (PROG decision 2).** The plan's 4 `hce_*` slots are 4 x 2.555 mm² = the GEN2 split engine's area (5,223 x 1,953 = 10.2 mm²; "hc_eng slot / 4").
  - Moving the ONE engine to the S-E PHY corner, as GEN2 places it, frees 0.19 mm per band (-4.9 mm² net). But the 4 x 2,100 b HC_ENG links then cross the SM row: HC_ENG 0.5 -> 40.5 bit-weighted stages, longest 22.8 mm, cut 0.879 at x 14.4 mm (> 0.60). **Rejected** (`plan/f4c_t6_hccorner_flow.png`).
  - ADOPTED form: ONE engine (one root, 2,048 MAC lanes, 250 cyc/row as UNITS measured on hnx RTL) laid out as its **4 ring quarters in the 4 quadrant slots** (the d4g U form that tb_hnx_hc_eng4 benches). The root sits by the centre channel.
  - **Nothing is released to the SM tile.** The 4 slots already ARE one engine's area, and the corner form, the only one that frees band height, fails the cut rule. "4 quadrant engines" (4 x 10.2 mm²) was never in the plan.
  - Plan-graph gap: the root <-> quarter ring links are not in the d4g graph (HC_ENG models only hc_q <-> quarter). They are quadrant-adjacent (≤ 5 mm across the centre).
- **COLL sizing (DIE-P4-2), from UNITS-COLL (units/coll/README.md).** At P = 4, COLL delivery is busy 125-157k of 492.5k cycles (25-32 %). L = 5 adds 586 + 1,044 b per quadrant (hb_coll -> cxdl_<q>4 -> SU), quadrant-local; ring and EP are unchanged.
  - The plan carries these as +1,630 b COLL_VM per quadrant (coll_<q> -> su_<q>0; the SU landing port is an open UNITS-SUDMA decision). The flow PNG shows that su_<q>3, the inner group, would cut this link from ~4 mm to ~1.5 mm: landing lane 4 there is the DIE recommendation.
  - **No x2 widening and no COLL outline growth are needed.** The new bits leave on the COLL S/N face toward its own band: 1,630 b over 963 um = 1.7 b/um. The W face is unchanged at 4.67 b/um.
  - The x2 reserve (0.585) is withdrawn.
- **SM_HBM (DIE-P4-4)** (`sm_hbm_cost.json`):
  - d4g: 2.88 bit-weighted stations, worst 8 (2.9 mm).
  - f4c_t6c: **5.25, worst 14 (5.0 mm; outer SMs 6.6 mm from their PC)**, i.e. +2.37 avg / +6 worst stations.
  - Cycles per SM record: **+1.2 avg / +3 worst at forwarded half-cycle hops; +2.4 / +6 at full-cycle relays**. This is fixed latency on a static lane, paid once per record (latency, not throughput). Sent to CMTP/VEH.

### SM area levers on the measured frame (DIE-P4-3), basis f4c_t6

**Frame limits.**
- The SM row is 8 columns of 4 x 4 tiles in the 25.5-mm usable reticle width. The tile width is therefore ≤ 673.92 um, which holds exactly 2 lane units of 336.96 across with no channel.
- The 32.5-mm usable height limits the tile height to ≤ 2,246 um.
- The largest tile inside the reticle is 673.92 x 2,203.2 = 1.485 mm² (`f4c_t6_Lmax`, 811.8 mm², cut 0.59 / 0.38, SM_HBM 5.88).
- SM4's linear lever table (die = 693 + 256 x Δtile) under-counts. Tile growth enlarges the column (4 x Δth) and pushes the band, it does not only add area.

| option (SM4 tile mm² at 0.441 fill) | tile on lattice | die | mm² | reticle | cut v / h | SM_HBM | vs SM4 estimate |
|---|---|---|---:|---|---|---:|---:|
| (a) shared xs4, 1.718 | 630.72 x 2,764.8 | 23.89 x 36.61 | **874.8** | **FAILS (36.6 > 32.5)** | 0.484 / 0.403 | 5.25 | 839.8 |
| (a) at the largest legal tile | 673.92 x 2,203.2 = 1.485 | 25.27 x 32.12 | 811.8 | fits | 0.59 / 0.38 | 5.88 | needs hard fill 0.51 (757k / 1.485M), not 0.441 |
| (a)+(b), 1.245 | 630.72 x 1,987.2 | 23.89 x 30.39 | **726.1** | fits | 0.478 / 0.44 | 5.12 | 718.7 |
| P3+(a), 1.343 | 630.72 x 2,160 | 23.89 x 31.77 | **759.2** | fits (0.73 mm long margin) | 0.484 / 0.373 | 5.12 | 743.8 |

(The 673.92-wide variants of (a)+(b) / P3+(a) are 741.9 / 776.9 mm² with cut 0.63 / 0.59; rejected.)

**Verdict for the owner decision.**
- (a) alone does NOT fit the reticle on this frame unless SM4 packs the (a) tile at ≥ 0.51 hard fill into 673.92 x 2,203 (2 lane units abutted, no channel). SM4 must check that packing before (a) can stand.
- (a)+(b) fits inside the 752 budget at 726 mm².
- P3+(a) fits the reticle at 759 mm², 7 mm² over the 752 budget.

### DIE-P4-1: stations / landing layer / GEN / GRT on f4c_t5 (stand-ins), fleet ot-epyc4:/srv/opentallas-scratch/claude/hnx/die_p4
Chain `physical/hbm_next/die/hnx_p4_chain.sh` (the GEN2 S4..S8 form, forked by copy; normal priority; hnx_ outputs only).
- **S4.** Root sites + pins + stations at 405: 2,385 buses routed (2,351 relayed, 673,569 b), 68 hop violations (> 405 um, worst 760 um: svg / sfus / idx sinks).
- **S5.** Lanes: 1,899 rows re-planned, 85 hop violations; 30,772 -> 32,596 stations.
- **LANDING layer.** 2,107 buses, **1,451 landed links / 2,358 landing tiles** (624: 655, 136: 1,243, 48: 460), 1,065 inter-region buses, 154 fork buses, 28 hops over reach.
  - It shows 16 problems (svg_<q><i>.fault: no contract bits), the same 16 as GEN2.
  - NO_E 1,451: there are no per-link E/K for the hnx regions; the d4g land plan is used as given (GEN2 is NO_E 964 too).
- Splice / bind / lockstep / GEN / GRT: see the lane file + pending_results (running at the time of writing).

## STEP 3 (10-19 ~03:00-03:40, fresh DIE agent): SM4 lever (a) shape, ATT4 A1 reserve, VM 2^19 -> lever table on f4c_t7

**New basis f4c_t7** = f4c_t6c + VM 2^19 words (6 x 1024x256 per bank, bank +151.2 um, covers CMTP's 481.7k Engram need; 0 mm², as f4c_t6e) + ATT4 A1 reserve (shared PV merge tile hnx_rp4a4_spvm, +5.9 mm² outline per die; modelled as ONE lattice row +43.2 um per SM tile = +7.3 mm² of SM column area ≥ 5.9). Same evaluator and arguments as t6c (`--hc quad --grp-side 259.2 --coll-d 4500 --coll-l5`; `f4c_t6c_chk` reproduces 693.09 / 0.484 / 0.490 / 0.669 M exactly).

| plan | tile (um) | die | mm² | reticle | cut v / h | bit-mm | stages_bw | SM_HBM | longest |
|---|---|---|---:|---|---|---:|---:|---:|---:|
| **f4c_t7 (P=4 base + A1 + VM 2^19)** | 630.72 x 1,857.6 | 23.89 x 29.36 | **701.35** | fits | 0.484 / 0.435 | 0.667 M | 6.01 | 5.25 | 10.2 mm |
| t7_La: (a) re-shaped to the frame width, no A1 | 673.92 x 2,160 (1.456 mm², hard fill 0.519) | 25.27 x 31.77 | 803.07 | fits | 0.576 / 0.416 | 0.720 M | 6.40 | 5.88 | 12.1 mm |
| **t7_LaA: (a) re-shaped + A1** | 673.92 x 2,203.2 (= the largest legal tile) | 25.27 x 32.12 | **811.81** | fits (0.38 mm margin) | 0.576 / 0.392 | 0.721 M | 6.43 | 5.88 | 12.3 mm |
| **t7_Lp3a: P3+(a) + A1** | 630.72 x 2,203.2 | 23.89 x 32.12 | **767.41** | fits | 0.484 / 0.366 | 0.679 M | 6.09 | 5.25 | 11.6 mm |
| t7_Lab: (a)+(b) + A1 (CMTP: fails MTP, rejected) | 630.72 x 2,030.4 | 23.89 x 30.74 | 734.38 | fits | 0.484 / 0.451 | 0.673 M | 6.07 | 5.25 | 10.9 mm |

**SM4 lever (a) tile `hnx_rp4lp4x` (claude/hbm-next-sm4-1019@62db69520): 1,080 x 1,339.2 = 1.446 mm², hard fill 0.523.**
- As drawn it does NOT fit the frame. A column is 4 tiles across: 4 x 1,080 + 108 = 4.43 mm per column, so the 8-column SM row is 35.4 mm, over the 25.5-mm usable width.
- Transposed (1,339.2 wide) it is worse: the row is 43.7 mm.
- A 2 x 8 column (2 tiles across, 8 high) makes the row 18.1 mm wide, but the column is 8 x 1,339.2 + 561.6 = 11.28 mm tall, against 9.37 mm for the 4 x 4 column at 673.92 x 2,203.2. The die then needs ~2 x 1.9 mm more height = ~36 mm, over the 32.5-mm usable height. It FAILS.
- Re-shaped at the frame width (673.92 wide), the same area needs 2,145.6 tall, so 2,160 on the lattice: 1.456 mm² at hard fill 0.519 (≥ 0.51). This is **803.1 mm²** without A1 and **811.8 mm²** with A1, inside the reticle.
- SM4 estimated ~770 mm² on f4c_t5. That figure is the linear estimate, and it under-counts: tile height grows the column 4 x Δth and pushes the band, as in step 2.
- **Geometric feasibility of the re-shape is NOT shown.** SM4's leaf is 985 x 457.92: the face-split xs4 (501.12 x 289.44) has its 4 BF16 lane stacks (198.72 x 216 each) beside it, W and E.
  - At 673.92 wide, the lane stacks cannot sit beside the xs4 (4 x 198.72 = 795 > 674). They must go above or below it, and the xs4 W/E face-split pins then face away from them.
  - Rough count: 2 such leaves + the 259.2 middle band need ~2,200-2,400 um of height. So (a) lands at the largest legal tile (2,203.2, 811.8 mm²) at best, or over the ~2,246 cap.
  - SM4 must re-pack and re-pin to prove it.

**Verdict for the OWNER decision (P3+(a) vs (a)), on f4c_t7 (A1 + VM 2^19 included):**
- **P3+(a) = 767.4 mm²** (was 759.2 without A1). It fits the reticle at cut 0.484, inside the rule.
- **(a) = 811.8 mm²**, at best, and only if SM4 re-packs the leaf to 673.92 wide. Its cut is 0.576, inside the rule but near the 0.60 limit, and SM_HBM is 5.88 stations.
- (a) costs +44 mm² (+5.8 %) over P3+(a). CMTP gives the same AR/MTP/4-user targets as met by both (P3+(a): MTP 3,389.9 / 4-user 4,220; (a): 3,500.1 / 4,423.1). Per mm², P3+(a) stays ahead: MTP 4.42/mm² vs 4.31/mm².
- DIE supports PROG's recommendation of P3+(a).
- Both options are over the 752 budget once A1 is counted: P3+(a) by 15.4 mm², (a) by 59.8 mm². The P=4 base t7 is 701.35.

## STEP 4 (10-19 ~03:35-04:00, fresh DIE agent): IDXN + measured VM 2^19 + FUSED lanes -> lever table on f4c_t8

**New basis f4c_t8** = f4c_t7 with three measured or published unit areas placed as plan blocks (`plan_p4.py --vm-dh 90.72 --idxn --fused 259.2`, the other arguments as t7; `f4c_t7_chk` reproduces t7 exactly: 701.35 / 0.484 / 0.435 / 0.667 M):
- **VM 2^19 measured** (UNITS-VM 03:35, tile `hnx_vms_bank` 270 x 403.92 um, 4 SRAMs): bank +90.72 um, not the +151.2 um modelled in t7. The bank row gets 60.5 um shorter. Die area is still 0 mm²: the band height is set by the quadrant HC column (SFU core + HC ring quarter).
- **IDXN** (UNITS-IDXN, 0.82 mm² cell+macro, outlines at fill 0.7):
  - The 2 key replay buffers (0.486 mm² -> 0.69 mm²) are split half a buffer per quadrant scorer. Each `idxq_<q>` grows 560 x 300 -> 560 x 610.
  - The 3 selectors + issuer (0.338 mm² -> 0.48 mm²) go in a new block `idx_nsel` (805 x 600) beside `idx_sel` in the centre strip.
  - Both fit in existing slack (the quadrant core column and the strip): 0 mm².
- **FUSED** (UNITS-FUSED `hnx_fused_lane_1019`, x32, S face = its VM bank):
  - The kit outline 259.2 x 259.2 is the README's **guess**. Its area is pending the lane gate's `std_area_um2`. 32 lanes = 2.15 mm².
  - Each SU group's 2 lanes sit at the foot of the SFU/HC client column, on the inner corner of the bank pair. The SFU group and HC client move up by 558 um.
  - Two placements were rejected:
    - Row A beside the bank pair, side by side: the quadrant overruns the centre channel by 70-390 um.
    - Stacked in row A: this collides with the quantiser on the N quadrants.
  - 0 mm². The cost is wire: bit-mm +0.021 M and stages_bw +0.13, from the longer SU-group links.
- The region map puts the `fus_*` lanes in their bank pair's SU-group region, so all 76 regions stay <= 4 mm.

| plan | tile (um) | die | mm² | cut v / h | bit-mm | stages_bw | SM_HBM | longest |
|---|---|---|---:|---|---:|---:|---:|---:|
| **f4c_t8 (P=4 base + A1 + VM 2^19 meas + IDXN + FUSED)** | 630.72 x 1,857.6 | 23.89 x 29.36 | **701.35** | 0.484 / 0.419 | 0.688 M | 6.14 | 5.25 | 10.2 mm |
| **t8_LaA: (a) re-shaped + A1** | 673.92 x 2,203.2 | 25.27 x 32.12 | **811.81** | **0.585** / 0.490 | 0.742 M | 6.54 | 5.88 | 12.3 mm |
| **t8_Lp3a: P3+(a) + A1** | 630.72 x 2,203.2 | 23.89 x 32.12 | **767.41** | 0.484 / 0.458 | 0.699 M | 6.22 | 5.25 | 11.6 mm |
| t8_Lab: (a)+(b) + A1 (CMTP-rejected) | 630.72 x 2,030.4 | 23.89 x 30.74 | 734.38 | 0.484 / 0.419 | 0.693 M | 6.17 | 5.25 | 10.9 mm |

**Verdict:**
- The three unit areas change no die mm²: placed area +1.7 mm², density 0.765 -> 0.768.
- They do change the (a) cut. (a) re-shaped goes 0.576 -> **0.585**, 0.015 under the 0.60 limit, so any further band growth on (a) fails the cut. P3+(a) holds at 0.484.
- The lever stands: **P3+(a) 767.4 mm² vs (a) 811.8 mm² (+44.4, +5.8 %; the (a) re-pack to 674 wide is still unproven)**. DIE still supports P3+(a).
- The FUSED guess is the open risk. If the lane gate needs the x store in a macro or a larger outline, it may run past the remaining ~1.7 mm of SFU/HC-column slack (the lane pair could also move above the HC client). That would grow the band, so re-run t8 with the measured side.

**Case inputs ready (step 4):** `physical/hbm_next/die/f4c_t7/` and `f4c_t8/` hold grants, region map, pin plan and `hnx_rp4lp4_pins.tcl` from `hnx_case_inputs.py` / `pin_plan_p4.py`. They are staged with the plan dirs into the fleet case src (`ot-epyc4:/srv/opentallas-scratch/claude/hnx/die_p4/src`).
- The `fus_*` and `idx_nsel` blocks have no GEN2 slot or contract instance yet. In the case they appear as plan or region blocks only, until UNITS publishes those tiles.
- `cxdl_<q>4` (L=5) also still needs the UNITS-COLL contract entry.
- The next case runs `bash hnx_case.sh f4c_t8` on the fleet, then `TAG=f4c_t8 bash hnx_p4_chain.sh`. It starts once the t5 chain ends, because the chain's `$B/hnx_*` intermediates and `$A` logs are not tag-keyed.

## STEP 5 (10-19 ~06:10-06:30, fresh DIE agent): DIE-P4-1 GEN fix, case on f4c_t8, SM4 tile check

**DIE-P4-1 on f4c_t5 ENDED at S7 GEN** (exit 3 after 1 h 55 min): `no free area for hb_idx__s_SW (1508.976x1509.84)`. Lane rows 40,936 (63,311 tiles); 16,660 rows went to "row nearest free area".
- Cause: the contract slots `idx_s<k>_h<j>` match no grant slot. GEN therefore placed the four 1.5-mm IDX score quarters LAST, in free area outside plan blocks. In the relay-free case they found it (W/E PHY corners). In the relayed case the lane rows had already taken it.
- Structural fix (`hnx_case_inputs.py`, @694ce60c9): one die slot per quadrant, `idxs_<q>`, at the plan's IDX corner block, with the stand-in view outline. The GEN2 W-corner pair slots `idx_s0`/`idx_s1` are dropped. The S-E plan corner holds the single stand-in `hc_eng`, so `idxs_SE` goes to the free S-E corner E of it (x 21,905; this is where the relay-free GEN had put it). The case scripts slot-map `hb_idx__s_<q>` to `idxs_<q>` (tags with those slots), so GEN places them as grant slots BEFORE the lane rows.
- t5 relay outputs were deleted (a failed run). t5 logs are in `/home/ubuntu/artifacts/hnx/die_p4/t5_failed_1019/`.

**Relay-free case f4c_t8: GEN_OK.** 1,214 insts, **0 placement problems**, 11.6 min, 7.2 GB. IDX quarters sit in their slots (`case_f4c_t8/layout.png`). Relay-free overreach is 669,586 nets, vs 682,640 on t5 (-1.9 %) and 710,093 on GEN2a. The chain then runs S4..S8 on t8 (`hnx_t8_run.sh`).

**SM4 lever (a) tile `hnx_rp4lp4x` 1,080 x 1,339.2 on the f4c_t8 lattice (COORD 04:30 request; evaluator `plan_p4.py`, t8 arguments):**

| arrangement | SM column (um) | die (mm) | mm² | cut v / h | reticle (26 x 33, 0.5 margin) |
|---|---|---|---:|---|---|
| 4 x 4, as drawn (`f4c_t8_Lx`) | 4,428 x 5,918.4 | 38.27 x 25.21 | 964.68 | 0.522 / 0.44 | FAIL (38.27 mm side) |
| 4 x 4 + A1 row (`f4c_t8_LxA`) | 4,428 x 6,091.2 | 38.27 x 25.55 | 977.91 | 0.521 / 0.53 | FAIL |
| 4 x 4 transposed (`f4c_t8_LxT`) | 5,464.8 x 4,881.6 | 46.56 x 23.13 | 1,077.21 | 0.508 / 0.594 | FAIL |
| 2 x 8 column | 2,268 x 11,275.2 | band-bound W, H ~35.9 | - | - | FAIL: the plan builder rejects it (quadrant core overruns the centre channel); at the t8 band H = 13.37 + 2 x 11.28 = 35.9 mm > 33 |

**No lattice arrangement of the 1,080-wide tile fits the reticle.** As the 04:30 request said, SM4 should re-pack the leaf 673.92 wide (BF16 stacks N/S of the xs4). The (a) price stays at **811.81 mm²** (t8_LaA, cut 0.585), unproven until that re-pack is done.

## STEP 6 (10-19 ~06:40, P3-DIE agent): OWNER P3+(a) case f4c_t9p3, FUSED re-plan at the measured size, S6 fix, chain relaunched

OWNER 10-19 (HANDOFF 0le): the next-release die is P = 3 with the shared 3-lane x store (P3+(a)). P = 4 work stops.

**f4c_t9p3** = f4c_t8 with:
- **SM slot for P3+(a).** The P3+(a) lever geometry, 630.72 x 2,203.2 um: SM4's 1.343 mm² estimate plus the A1 row.
  - This is a stand-in until P3-SM posts the synthesis-sized `hnx_rp3lp3x` outline. Then re-run the same command with `--tile-w/--tile-h`.
- **FUSED lanes at the measured size** (FUSED-SRAM n3: ~104k um² std + 2 x 128x256 SRAM, 475.2² ≈ 0.226 mm²).
  - The lane is re-outlined to **345.6 x 648 um** (0.224 mm², aspect 1.875, on the 43.2 lattice).
  - Two lanes stack per SU group at the foot of the SFU/HC client column, beside their bank pair (S face = bank).
  - Why not square: a 475.2 square widens each of the 4 group columns by 216 um. The quadrant core then overruns the 400-um centre channel by 79-424 um, which would need ~+0.85 mm of die width (~+27 mm²).
  - Two other layouts were rejected (step 4): a separate lane row over the banks makes the die +0.8 mm tall, past the reticle margin, and lanes in row A overrun the channel.
- **FUSED parent per COORD 0kl.**
  - A small hub tile `fus_hub` (432 x 432 reserve) sits on the strip centre line. It holds the top's own logic: job decode, prologue, heap, divc, rsqrt.
  - The csum is a **tree over neighbour hops**: lane pair (stacked) -> g1->g0 and g2->g3 (neighbour columns) -> g0->g3 (quadrant node = the innermost group, lane 6) -> hub. The command and r broadcast use the same tree in reverse.
  - Graph classes: `FUSED_VM` 547 b (rq/rr/wq) and `FUSED_TREE` 441 b (up 268 + dn 140 + r 33), from the ot_hnx_fused_lane ports.
- Unchanged from t8: IDXN, VM 2^19 (measured bank), A1, COLL L=5, one HC engine as 4 ring quarters.

Command: `plan_p4.py --plans f4c --grp-side 259.2 --coll-d 4500 --coll-l5 --hc quad --vm-dh 90.72 --idxn --tile-w 630.72 --tile-h 2203.2 --fused 345.6 --fused-h 648 --fused-hub 432 --suffix _t9p3 --png`. The check `t8Lp3a_chk` reproduces t8_Lp3a exactly (767.41 / 0.484 / 0.458 / 0.699 M).

| plan | die | mm² | cut v / h | bit-mm | stages_bw | SM_HBM | longest | relay flops (graph) |
|---|---|---:|---|---:|---:|---:|---:|---:|
| t8_Lp3a (step 4: FUSED 259.2 guess, no FUSED graph) | 23.89 x 32.12 | 767.41 | 0.484 / 0.458 | 0.699 M | 6.22 | 5.25 | 11.6 mm | 1.28 M |
| **f4c_t9p3 (P3+(a), FUSED measured + tree + hub)** | 23.89 x 32.12 | **767.41** | **0.469 / 0.504** | **0.776 M** | **6.30** | 5.25 | 11.2 mm | 1.43 M |

- **Area: 767.41 mm²**, 90.6 mm² under the 858 reticle (26 x 33). Margins are 2.11 mm short and 0.88 mm long (≥ 0.5 required). Placed area is 601.8 mm², density 0.784.
  - The FUSED growth (2.15 -> 7.2 mm²) costs 0 mm². The lane columns rise to 2.0 mm, under the 2.8-mm SU slot that sets the band height.
- **Cuts ≤ 0.55-0.60.**
  - Worst v cut: 0.469.
  - Worst h cut: 0.504, at y 20.0 mm, x 8.5-9.5 (N band, FUSED tree/bank links beside the quadrant core). It is inside the rule, with 0.05 margin to 0.55.
- **Bit-mm +0.077 M**, all from the FUSED graph: FUSED_VM 17,504 b at 5.0 stages, longest 1.07 mm; FUSED_TREE 14,112 b at 4.66 stages, longest 6.2 mm (quadrant node -> hub).
- **Reach 405 + stations, landed-regions clocking** (`clock_plan_f4c_t9p3.json`):
  - 76 regions; the largest non-SM region is 3.43 mm (≤ 4 mm). Neighbour pairs: 189.
  - 389 landed links / 213,176 b (t5: 369 / 206,402).
  - Relay flops at 405: 2.29 M (t5: 2.01 M). Max hops: 33.
  - FUSED: lane<->bank stays inside its group region (0 landed, ≤ 8 hops). The tree has 16 landed crossings (group -> core -> strip).
- **FUSED latency for CMTP:** the worst lane -> hub tree path is 14.5 mm = 37 hops at 405 ≈ 18.5 cycles at forwarded half-cycle hops, each way.
  - This adds ~+37 cycles to c1 per FUSED record (up + broadcast down), plus 4 tree-add levels.
  - The row II is unchanged (the tree is pipelined).
  - The star form with RL = 4 relays per lane is not legal on the die (32 x 441 b into one hub).
- **Open (owners):**
  - UNITS-FUSED: re-outline `hnx_fused_lane_1019` to 345.6 x 648 (or say why it must be square).
  - UNITS-FUSED: move the csum adders into tree nodes, in the golden order. Lane `lid` = q*8 + bank must match the golden tree pairing.
  - UNITS-FUSED: kit `fus_hub`.
  - P3-SM: post the synthesis-sized `hnx_rp3lp3x` outline, then re-run t9p3.
  - The plan graph's SM_X / SM_OUT bits are still the d4g basis (not P-scaled), as in every P = 4 plan.
  - `fus_*` / `fus_hub` have no contract instances yet (plan / region blocks only in the case).
- PNGs: `plan/f4c_t9p3.png`, `plan/f4c_t9p3_flow.png` (LOOKED: lanes in the group columns, hub on the centre line, no overlaps). Case inputs: `physical/hbm_next/die/f4c_t9p3/` (grants, region map, pin plan; the SM pin tcl is the P = 4 stand-in).

**S6 structural fix.**
- The t8 chain died at S6 with SYNTH_MISSING on 8 hbfd masters: land0_48 NS/SN/WE, lh0_136 EW/NS/SN_f2, lh_136 EW/NS_f4.
- `hnx_p4_chain.sh` S6 now derives the missing list from the run's own view plan instead of stopping. It then:
  - pulls the plan rows and wrappers;
  - adds the wrappers to the case src `v16w/` (add-only; src lacked land0_48_NS/WE);
  - synthesises exactly those masters with `hnx_s6_synth.sh` (`NOCHAIN=1`; GEN2 synth_master/etm, normal priority, LIBCELLS=1 for lh0/land0);
  - fetches (source-checked), uploads, and re-merges.
- It still stops if any master stays missing (no stubs).

**Chain relaunched on the P3 case:** `TAG=f4c_t9p3 bash physical/hbm_next/die/hnx_case_run.sh` (replaces hnx_t8_run.sh). It runs S3 (relay-free GEN), then S4..S8. Log: `/home/ubuntu/artifacts/hnx/die_p4/chain.log`. The t8 logs are in `t8_dead_s6_1019/`, and t8 is not rerun.
- S3 relay-free case f4c_t9p3: **GEN_OK**, 1,214 insts, 0 placement problems, overreach 696,308 nets (t8 669,586; the die is 2.8 mm taller), `case_f4c_t9p3/layout.png` (LOOKED: SM = P=1 stand-ins in the P3 slots, IDX quarters in corners). S4..S8 running.

## Codex takeover: exact-source P3 S6 recovery (2026-10-19)

The P3 f4c_t9p3 chain passed splice, exact port binding (155 masters / 65,688 instances), and relay lockstep with three caught mutants, then stopped at S6S. The source wrapper for hbfd_land0_48_SN still named representative rf2119_k00_00_l0; the P3 generated wrapper names rf2106_k00_00_l0. Even this comment-only difference must fail immutable source comparison. The old add-only wrapper installation and ETM-log-only reuse were therefore unsound as a recovery recipe.

The recovery now freezes the current plan wrappers in a unique hardlink-copy source root (rsync replaces wrapper inodes), leaves previous sources/builds untouched, rebuilds every missing master under that root, and runs the unchanged v16_fetch source/contract/ETM checks before uploading any admitted views. No hash normalization, stub, or source-check waiver is used. Fleet submissions are unpinned and explicitly normal priority (OT_RUN_PRIO_ENV empty disables automatic die promotion). Local driver paths derive from its own worktree; A may select a new artifact directory without overwriting failure evidence. bash -n passes both edited scripts. This is an integration recovery, with the previously approved P3 frame/stand-ins and existing landed crossings unchanged; no new physical tile or schedule cycles are introduced.
