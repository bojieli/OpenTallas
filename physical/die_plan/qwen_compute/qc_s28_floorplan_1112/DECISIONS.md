# QC hand floorplan HF-1 (QC-S28-FLOORPLAN, 2026-11-12)

Base: plan_qc99_s28 2f0c17d5f1a3 (claude/qc-event-s28-1111@88018018ef). Stage S1 (die floorplan). Not applied to the plan.
Drawings:
- qc_dataflow_column.png/.svg: data flow, one column
- qc_floorplan_column_cur_vs_hand.png/.svg: column E0, current vs HF-1, seam bits, taps, clock branch
- qc_floorplan_die_cur_vs_hand.png: whole die, changed slots outlined in red

## 1. Data flow (from the lanes, latency table and port chains; per column, all 12 the same)

- **E-W slice ring.** fe(k) <-> fw(k+1) at the column seam, about 2.6-3.3 kb in each direction (st 1088, dd 548, dr 520, rd/ard 512, hr 453; 4-5 c). l9 is the wrap return.
- **Mid-row pipeline.** fw -> stm -> sc -> fe. The 7.1 / 6.4 / 5.9 kb port loads on these seams are mostly through-traffic.
  - fw<->fe inside the slice: 2.7 kb, 10-11 c, crossing stm and sc.
  - stm<->fe: 1.1 kb.
- **ctl hub.**
  - ctl -> st_a 1.1 kb / st_b 0.65 kb.
  - b_hw ctl -> hc0..3: 4 x 1573 b, 4-9 c (hc0 via st_a, hc3 via st_b).
  - ctl <-> fw: 1.26 / 1.6 kb.
  - stm -> ctl: 2.1 kb.
  - ctl -> su_c: 1655 b, 12 c, via sc.
- **su row.** su_c <-> su_l1: 1.5 / 0.9 kb. su_c <-> su_l0: 1.5 / 0.9 kb.
- **Vertical trunks.**
  - cws0-3, hc -> bn: 4 x 516 b, 22-26 c.
  - rsn/rsf, bn/bf -> st_a: 2 x 514 b, 23 / 52 c.
  - hc -> tn: 4 x 516 b, 3-7 c.
- **cb rows.** A 4x4 A0 tile ring per column: 514-1546 b links at 4-22 c.
- **W strip.** coll / serdes / ucie: coll_f4 <-> W5 fw 3.97 kb. The PHY seams are fixed.

## 2. Verdict on the current s28 placement

The topology is already right: every heavy pair abuts, and there are 0 non-adjacent hops. At die level the worst seam is 0.47 of the 12 pin/um budget (ctl|sc). On a first-order through-traffic model (route_supply pitches/derates, ft_frac 0.5, core M6/M7 only, halved), the worst block is sc at H 0.27 / V 0.24. So no die cut is starved. The failures are in-slot, and three die-level choices cause them:

- **V1. Shape and fill outliers in the hc row.** hc0-3 are 613-622 x 1339 (aspect 0.46). They have no hard cores, cell fill 0.02-0.22, and ~0 ft through hc1/hc2. GEOM-VIS-2 found the cells in a 436x466 blob with the N 63% empty.
- **V2. The mid row is the crossroads, 1339 tall.**
  - sc carries 9.1-9.4 kb of ft against 0.57 kb of its own I/O.
  - stm carries 5.6-5.9 kb.
  - fw/fe carry 10.5-13.9 kb of bus bits on 622 x 1339 slabs: the fw ring is red on all faces, sc core_V is 1.12-1.19, and stm mstreet H is 1.18-1.33.
- **V3. Detour routes** through sc/fe/st_b:
  - x_fw_ctl_p2: fw>stm>sc>fe>st_b>ctl, 536 b.
  - x_fw_ctl_p1: fw>stm>sc>ctl, 536 b.
  - x_su_l1_ctl: su_l1>su_c>sc>ctl, 456 b.

## 3. HF-1 decision table (per column; all 12 columns, W slices the same order)

| block / family | HF-1 position (die y, col-local x) | size | why | channel / seam bits (HF-1) | change vs s28 | family lane must |
|---|---|---|---|---|---|---|
| W strip IO/PHY (serdes x3, ucie_kv, coll_ucie), coll_*, glue, native59, tt_ctlm | unchanged | unchanged | Neighbour-die seams are fixed by the PHY face windows | coll_f4 <-> W5 fw 3966 b over a 700-um overlap: 0.47 | coll_ftc E-face ft windows (y 306-1016 local) must repack into y >= 336.96 (470 um of windows in 700 um), because W5 fw now starts 34.56 higher | DIE-QC-99: one window edit on coll_ftc |
| cb rows tf/tn_01/bn_01/bf (A0 4x4 ring) | unchanged | 1235.52 pitch | Fully abutted across 31.2 mm; ring order fixed | 514-2574 b seams, 0.02-0.17 | none | S28-D: in-slot (views, rings) |
| cbn_q00 rows (tn_00, bn_00) | tn_00 bottom -34.56, bn_00 top +34.56 | 1235.52 x 2566.08 (+34.56 H) | S28-B gap: cbn_q00 x2 H +34.56. **FITS**: absorbed inside the slice band, die outline unchanged | - | 24 parts, 3 types grow H | S28-D: re-floor cbn_q00 inside +34.56 |
| cbx_q10 in the tn_10/bn_10 rows | origin unchanged | unchanged (type shared with tf_10/bf_10) | A shared type must not split | 34.56 x 1235.52 filler strip beside each (24) | 24 die filler strips | none |
| su row su_l1 / su_c / su_l0 | y 10177.92-11517.12 (+34.56) | unchanged 622/1227/622 x 1339.2 | Dense (core_frac 0.53-0.57); keep | su_c-sc 2232 b 0.30, su_c-stm 1521 b 0.21 | move only | none (S28-B su_l1 ring form stays in-slot) |
| **mid row fw / stm / sc / fe** | y 11517.12-13348.80 | **1831.68 tall** (+492.48); widths fw 622.08, stm 613.44, **sc 656.64 (+43.2)**, **fe 578.88 (-43.2)** | +37% H supply for the E-W crossroads (sc/stm/fw/fe); sc gets +43.2 V street (core 244.6 wide). Covers the S28-B 'sl_sc N-face +54 um' (**FITS**: sc gets +492 H and +43 W). fe keeps 1.06 mm2 (+27%) | fw-stm 7477 b 0.34; stm-sc 5765 b 0.26; sc-fe 5803 b 0.26; fe-fw(k+1) 5507 b 0.25; stm-ctl 4906 b 0.67 (highest; stm N pin window ~410 um); sc-ctl 2450 b 0.33. Through ratio sc H 0.27 -> 0.15, V 0.24 -> 0.17; stm H 0.18 -> 0.12, V 0.07 -> 0.14 | 48 parts / 40 types reshaped (shape freeze holds: cores keep shape) | S28-B (sc) and fw/stm/fe owners: re-floor in the new outline. sc: core centred, V streets both sides. stm: ROMs in one column with the N face (ctl) open. fw/fe: landing rings on W/E faces, now 1832 long |
| ctl row st_a / ctl / st_b | y 13348.80-14688.00 (+527.04) | unchanged 622/1227/622 x 1339.2 | ctl hub stays central over stm+sc; st_a/st_b over fw/fe | ctl-st_a 4748 b 0.30, ctl-st_b 3491 b 0.22, fw-st_a 3227 b 0.43 | move only (36 parts) | street-rule forms stay (S28-B) |
| **hc row hc0-hc3** | y 14688.00-15465.60 | **622/613 x 777.6** (aspect 0.79-0.80) | No cores, fill 0.02-0.22: the GEOM-VIS-2 re-floor ask (~600x520, aspect <= 1.2). W hc fill 0.21 -> ~0.36 | hc-ctl/st 2.1-2.6 kb 0.28-0.36; hc-tn 516-1544 b 0.07-0.21 | 48 parts / 18 types reshaped | hc family: re-floor (cells around the S pins). N FIRM chain cw_n1 (3 stations over 1273 um) shortens |
| ft re-routes R1 + R2 (plan lanes) | - | - | R1: x_fw_ctl_p1/p2 -> fw>stm>ctl (removes the 5-hop detour). R2: x_su_l1_ctl -> su_l1>su_c>stm>ctl (mirrors su_l0) | -1528 b from sc, -536 b from fe/st_b; +1528 b on stm (stm-ctl 0.67) | ft_slots on fw/stm/sc/fe/st_b/su_c/ctl types | DIE-QC-99 composer: plan ft chains + ft RTL. Group x_fw_ctl/_p1/_p2 pads 21 -> about 16 c (tok/s gain) |
| die clock | root (15608.16, 12821.76) unchanged; H-tree per column | - | Root now inside the W0 fe slot (M8/M9 only, no conflict) | - | tap_um re-derived for the 96 reshaped + 72 moved slice parts (generator); landing rings re-sited by type | clock owner: rerun the plan clock tool; no spine change |

## 4. Die-level change vs inside the slot

**Die-level (one QC plan event):**
- 144 partition rects:
  - 96 slice parts reshaped (mid 48, hc 48; 58 types);
  - 24 cbn_q00 parts +34.56 H (3 types);
  - 72 slice parts moved, shape the same (34 types).
- 24 filler strips, 34.56 tall, beside cbx_q10.
- The coll_ftc E-window repack.
- The R1/R2 ft chains.
- Die outline 31216.32 x 25643.52 unchanged.
- Untouched: the W strip, every PHY face window, and every neighbour seam (S81/KV/HEAD).
- cb rows tf/tn_01/bn_01/bf are not touched. 245 of 377 parts keep their rects (all cb rows except the 24 cbn_q00, plus the W strip).

**Latency (estimate; exact numbers from reach_fix/plan regen):**
- 142 lanes die-wide (about 12 per slice: x_ctl_su_c x3, cws0-3, rsn, rsf, x_su_l1/l0_ctl, x_st_a_fe, x_su_c_ctl; 66 kb) cross the mid row vertically and get +492 um, so about +1 station each. The +1 cycle is absorbed only where pad >= 1 (12 of 154 today).
- cws0-3 start in hc (-280 um), net about +210 um.
- hc -> tn FIRM chains about -1 station.
- R1 cuts the x_fw_ctl group from 21 to about 16 c.
- Net TOK: needs TOK-VERIFY. Cycles are owner pre-approved.

**Inside the slot (family lanes):** core arrangement, street widths, landing-ring form, and pin windows inside the new outlines (S28-B..E). Cores keep their shape.

**Bit-mm** (centre-centre, all 2993 hops): 1,855,138 -> 1,857,736 (+0.1%). The die arrangement is not the lever; slot shape and supply are.

## 5. What HF-1 does NOT fix

These are the ring-class p99 values above 1.5:
- cbf_q01_s2 2.06
- cbf_q00_s2 1.98
- cbf_q11 1.74
- cbn_q11 1.74
- slw_su_l1 1.70
- cbn_q00 1.66

They are A0 M6/M7 over-core and landing-ring forms (S28-A views, S28-D cb, the su_l1 monitor ring). The cb lattice cannot grow in x, so no die room exists there. Form d (M8/M9) for rsf/cws/serdes trunks stays an option once the PG strap audit over the A0 75-um bump field is done.

## 6. BATCH RE-SIGN LIST (OWNER ruling 11-12: signed slots are not constraints)

The source is the release cache (plan_qc99_s27 counted). QC has 2 signed types and 31 signed core designs. HF-1 was drawn for die closure only. No slot was kept because it was signed, and none needed to be.

**Signed types**

| signed type | slots | what HF-1 changes | re-sign scope |
|---|---|---|---|
| coll_ft__cla4a25d77 | coll_f1, coll_f2 | nothing (W strip; rect, faces, windows and neighbours the same) | none. If the counter keys on the plan sha, RE-SIGN on the same routed DB only |
| coll_ftn | coll_f5 | rect and windows the same. Its E neighbour becomes W5 fw (taller) instead of fw + st_a. No lane crosses that face | same as above: same-DB re-sign only if the counter needs it |

**Signed cores** (31 designs; core-shape freeze, pins the same):

- sc2 leaf x3 variants. They sit inside the 9 reshaped sc types and may move or flip inside the slot. The view is unchanged: no core re-sign. The parent sc types need a fresh kit (they are unsigned today).
- su_c cores x6 and su lanes l0-l7. Their su row only moves +34.56: no change.
- cland cores in slw_su_l1: no change.
- a0c nk/nl. cbn_q00 grows 34.56 in H, and the core positions inside the slot may shift. The view is unchanged: no core re-sign.
- cland w515/w517 cores in cbn_q00. In-slot position only: no core re-sign.

**Parent types that need a re-kit** (none signed today): 58 reshaped slice types, 3 cbn_q00 types, and 34 moved types. For the moved types the outline is the same, so they re-kit only for the tap/landing re-derive and the new neighbour pin windows. coll_ftc needs its E-window repack.

**Net batch re-sign: 0 types, 0 cores** (at most 2 same-DB re-signs for plan-sha bookkeeping).

## 7. HF-1b: DIEVIEW row re-pitch merged (supersedes the HF-1 row heights; drawings regenerated)

DIEVIEW proposed content-natural rows: hc ~520 / fw-row ~1780 / st 1339 / su ~1400, a total of 5039 against 5357 today. Two things change the split:
- the cbn_q00 rows need +2 x 34.56;
- GEOM-VIS-2 saw the hc cell blob at about 436 x 466 (W hc fill 0.21 at 1339, i.e. ~0.54 at 520, which is above the 0.42 QC GRT-fail density).

**Adopted rows** (die y, the same in all 12 columns, sum 5287.68 + 69.12 = 5356.8, no die growth):

| row | y range | height | vs s28 | basis |
|---|---|---|---|---|
| bn_00/bn_10 (cbn_q00 +34.56) | 7611.84-10177.92 | 2566.08 | +34.56 | S28-B gap |
| su | 10177.92-11577.60 | 1399.68 | +60.48 | DIEVIEW: macro-bound 1355 need; opens the su_l1 1.3-um street |
| fw/stm/sc/fe | 11577.60-13409.28 | 1831.68 | +492.48 | DIEVIEW: pin-bound 1780 need (7.5 kb per E/W face); 51.8 um margin; covers FW-EFACE-BIN structurally |
| st_a/ctl/st_b | 13409.28-14748.48 | 1339.2 | same shape, moved | DIEVIEW 1222 need: OK |
| hc0-3 | 14748.48-15465.60 | 717.12 (aspect 0.85-0.87) | -622.08 | fill ~0.39 for W hc, under the 0.42 line; DIEVIEW's 520 is too dense for the observed blob |
| tn_00/tn_10 (cbn_q00 +34.56) | 15465.60-18031.68 | 2566.08 | +34.56 | S28-B gap |

Mid-row widths are unchanged from HF-1: fw 622.08 / stm 613.44 / sc 656.64 / fe 578.88. R1 and R2 are unchanged.

**Scores current -> HF-1b:**
- sc through ratio H 0.27 -> 0.15, V 0.24 -> 0.17.
- stm through ratio H 0.18 -> 0.12, V 0.07 -> 0.14.
- Highest seam: stm|ctl 0.67.
- Bit-mm 1,855,138 -> 1,856,939.

**Neighbour seams.**
- The E/W faces of the strip rows meet only the next column (the fe(k)|fw(k+1) ring) and, for W5, the W strip.
- S81, KV and HEAD meet QC only through the W-strip PHYs (serdes x3, ucie_kv, coll_ucie), whose rects and face windows do not change. **No neighbour-die seam moves.**
- coll_ftc E-face ft windows must repack into local y >= 397.44, because W5 fw now starts at 11577.60: 470 um of windows into 639 um, which fits.
- coll_ftn (signed) and coll_n faces: no lane crosses them toward W5 fw/st_a, so nothing changes.

**Clock.**
- The root (15608.16, 12821.76) is unchanged; it now lies inside the W0 fe slot (M8/M9 only).
- The per-column trunks are unchanged.
- tap_um and the landings are re-derived for all slice types by the generator.

**Die event scope (HF-1b):**
- Every slice-band partition changes rect: 168 parts in 4 rows x 14 families x 12 columns.
  - Reshaped: su (36), mid (48), hc (48), 132 in total.
  - Moved only: st/ctl (36).
- Plus 24 cbn_q00 parts (+34.56 H), 24 filler strips beside cbx_q10, the coll_ftc window repack, and R1/R2.
- 185 of 377 parts keep their rects: all other cb rows and the W strip.

**Latency estimate:**
- Lanes that cross the mid and su rows vertically get about +553 um, so about +1 station.
- cws from hc gets net about +240 um.
- The hc->tn FIRM chains lose about 1 station.
- R1 saves about 5 c.
- TOK-VERIFY is needed. Cycles are owner pre-approved.

**Re-sign (updates section 6):** the signed QC types are still only coll_ft__cla4a25d77 and coll_ftn. Both are in the W strip, unchanged. **No signed type is in the slice band, so the re-pitch changes the outline of 0 signed types.**

Signed cores inside re-pitched parents keep their views (core-shape freeze):
- su_c cores x6, su lanes l0-l7, and the cland cores in slw_su_l1 (su row +60.48);
- the sc2 leaf x3 variants (sc).

Those parents re-kit fresh; none of them is signed.

**Batch re-sign: 0 types and 0 cores.** At most 2 same-DB re-signs of the coll types if the counter keys on the plan sha.
