# FABLE-PD-KV-1945: q2 M3 spacing at the SRAM edge, head-core abstracts, what blocks the first 7u kits (2026-11-15 20:20 PST)

Read-only technical PD review. MEASURED = read by me today from the named DEF, report, LEF, log or table. REPORTED = from
a lane post. INFERENCE = my reasoning, not run. I ran no build and no OpenROAD; two small Python DEF parsers on epyc10
(`/tmp/fpk_edge.py`, `/tmp/fpk_m2use.py`). Nothing was launched, stopped or edited.

## 0. Answers

1. **q2 DRC: the cause is the SRAM y site, 13.26.** The macro's bottom edge is 30 nm above the row-boundary M2 track
   (y 13.230). An M2 wire on that track is legal (21 nm from the macro), but every M2-M3 via on it is not: the M3
   via enclosure ends at 13.244, 16 nm from the blanket M3 OBS at 13.260; the rule is 18 nm. The track is 2 nm short
   for vias along the whole 94.8-um edge of both bottom SRAMs. MEASURED. The same site (13.26) is in q0, q2 and q3.
   A re-route moves the via along the track; it does not remove the track.
2. **Head-core blanket OBS is not a detail-route pin-access risk; it is a global-route run-time cost.** No KV kit
   with head cores has reached detail route, and the one-macro proof routes 1351 pin nets with 0 violations at the
   macro (REPORTED KV-ABSPIN). The capacity-0 pin gcells are what kept m7hg_g in congestion iterations for hours
   (MEASURED in FABLE-PD-KV-1450). The right form is a GRT-side fix, not a new abstract.
3. **The first 7u kits are blocked by three different things, per family:** non-pv / non-hg types by the tree only
   (smoke ETA about 21:00-21:30); pv by the 7p event; hg / hgi by the ring split, which has a new problem I measured:
   **34 of 103 ring cores sit more than 340 um from their band, 80 more than 110 um** (section 3a).

## 1. KV-Q2-CLK: one M3 spacing violation at the SRAM bottom edge

### 1a. Measured (epyc10 `/srv/opentallas-scratch2/claude/kv-q2-clk/b_fix`)

| item | value | source |
|---|---|---|
| SRAM `ot_sram_1r1w_128x256_m1_r2c2` | 94.824 x 41.064; OBS M1, M2, M3 = full outline, M4 from x 0.072; pins M4 on the west edge | `macros/*.lef` |
| sites | (15.12, 13.26) MX, (133.488, 13.26) MX, (15.12, 127.404) R0, (133.488, 127.404) R0 | `macro_place.tcl`, `6_final.def` |
| rows | from y 4.32, pitch 0.27; boundary at 13.230 = 4.32 + 33 x 0.27 | DEF `ROW` |
| M2 tracks per row | +45, 81, 117, 153, 189, 225, 270 nm | `make_tracks.tcl` |
| the 3 violations | all `Metal Spacing`, M3, y 13.244-13.260, x 29.313 / 16.821 / 20.241; macro `u_a...g_macro[0].u_s` against net5362, net5362, `qd_r[354]` | `5_route_drc.rpt`, `ripnet_drc.rpt`, `ripwin_drc.rpt` |
| the wire | net5362: M2 at y 13.230 from x 13.221 to 29.313, M3 stub (29.313, 13.185)-(29.313, 13.230), M2 at y 13.185 on to x 53.397 | `6_final.def` |
| M3 ends at that position in other routes | a, b, c, d, e, base: 0 (all DRC 0); b_m10, b_m10_p2, b_fix: 1 (the same wire) | my scan of 6 DEFs + 9 DRC reports |
| channel load at x 20-29, y 8.9-13.3 | 82-91 of about 112 M2 tracks used, 57-67 M4 tracks; M2 y 13.230 used at both x | `6_final.def` |
| DRT iterations 10 to 60 | 1 violation in each report | `5_route_drc.rpt-*.rpt` |

Arithmetic: via centre 13.230 + 9 (half cut) + 5 (M3 enclosure) = 13.244, the measured box bottom. 13.260 - 13.244 = 16 nm.

- The clean routes (a-e, base) never put a via there. The hold ECO route (m10) did, in the busiest part of the channel.
- The site was chosen for the M4 pins: MX at 13.26 puts the `clk` pin centre at y 53.544 = track 1115 of the 48-nm
  M4 grid. Nothing checked the edges against the M2 rows.
- The top edge of the same macros (y 54.324) has the same class one track up: M2 track 54.351 is legal by exactly
  18 nm, its via enclosure is 13 nm from the OBS. No route uses it today (0 hits in 6 DEFs).
- The top SRAMs (127.404 / 168.468) are clean: the nearest M2 tracks are blocked for M2 itself.
- Why the router keeps the violation for 50 iterations instead of leaving the track: not traced. INFERENCE: its cost
  for a via next to a macro obstruction is weaker than the checker's rule at this 2-nm margin.

### 1b. Class members (repo `physical/die_plan/qwen_kvsys/cores/macro_sites/*.json`, MEASURED)

| core | bottom SRAM site | bottom edge | top edge |
|---|---|---|---|
| qkd_ectlk_q0 | (15.552, 13.26) MX | bad track 13.230 | bad track 54.351 |
| qkd_ectlk_q2 | (15.552, 13.26) MX | same | same |
| qkd_ectlk_q3 | (20.736, 13.26) MX | same | same |
| q1 | no json of its own; not checked | | |
| kv3_pv_pair (8 SRAM sites) | other master, height not read | not checked | |

Rule for any macro edge at offset e inside a row (nm): a bottom edge is bad when e - t is 27 to 31 for an M2 track t;
a top edge is bad when t - e is 27 to 31.

### 1c. Fixes

| # | fix | removes | owner |
|---|---|---|---|
| 1 | This database: keep the running obstruction route, but make the M3 obstruction a strip along the full bottom edge of both bottom SRAMs (x 15.12-109.944 and 133.488-228.312, y 13.19-13.26) and along their top edge (y 54.324-54.40), and **leave it in the database**. Rip only the nets with a via on y 13.230 under the macro. The window rip of every net with a pin in x 8-60 moved 1 violation by touching hundreds of routes | the instance, and any later ECO pass on this database | KV-Q2-CLK-1115 |
| 2 | Kit rule: `macro_sites.py` writes those strips for every macro edge that meets the 27-31 nm test, into the pre-global-route hook, so GRT, DRT and every ECO route see them. q0, q1, q3 take it on their next route or ECO; no re-place | the class on existing placements | KV-ECTLK-RL (script), KV-102 (review) |
| 3 | On the next full rebuild of q0-q3: bottom site y 13.26 -> 13.50. That is +5 M4 pitches (pins stay on track) and puts the bottom edge on the row boundary 4.32 + 34 x 0.27; the top edge offset becomes 24 nm, clean. Not for the current q2 database: a macro move re-places and re-times the clock | the class at the source | KV-ECTLK-RL |
| 4 | `macro_sites.py` check, fail-closed: the 27-31 nm test on all four edges of every site (M2 rows for bottom / top, M3 columns for west / east), listed in the test file | new sites | KV-ECTLK-RL |

Not a fix: shrinking the SRAM M3 OBS by 2 nm (the real macro metal is not known to end there); a fourth re-route
without a persistent obstruction; more DRT iterations (10 to 60 changed nothing).

## 2. KV-ABSPIN: blanket M1-M5 OBS on the 13 kvgeom7u hard-core LEFs

| question | answer | basis |
|---|---|---|
| DRT pin access at risk? | No evidence. One-macro route of kv3_head_eighth_e2 (1351 pin nets): 0 violations at a macro pin, no DRT-0073 | REPORTED KV-ABSPIN 18:45 |
| Any KV kit with DRT pin-access errors near these cores? | None exists to read. No hg / hgi kit has reached detail route | MEASURED FABLE-PD-KV-1450 |
| KV DRT-0255 near a hard core? | No. kv3_io_cor attempt_8 stops in iteration 1 on a ring net `u_cland_i_host_fdi/...dsel/net30819` with the unreachable access point on layer index 5 (M6) at the box boundary (537.510, 54.432). hroot and io_cor_v1 are also `u_cland_*` ring / ft nets. That is the PG-pair-row class of FABLE-PD-DRT-1350, not an abstract | MEASURED epyc7 `5_2_route.log` l.311-314; REPORTED 1350 |
| GRT at risk? | Yes, in time. 49 of 53 final overflow markers of m7hg_g were inside head cores at capacity 0-1; the last 10 iterations cost 2 h 47 and the incremental pass ran 5 h 51 silent | MEASURED 1450 |

Form:

1. Keep the 13 LEFs as they are. A blanket OBS with edge pins on the same layer is the normal abstract; the signed
   databases are not on the fleet, so an exact-OBS or pin-window view cannot be built honestly today.
2. Do not adopt the 1.0-um cut-back. It models no core metal (KV-ABSPIN says the same).
3. Fix the GRT side in the kit: bound the congestion iterations for types with hard cores (fix 5 of 1450:
   `-congestion_iterations 15` on the full route and on the incremental call). A capacity-0 pin gcell with usage 1
   cannot be cleared by rip-up, and allow-congestion already lets the flow continue. INFERENCE that 15 is enough:
   1450 measured 416 markers at iteration 20 and only core-internal residue after.
4. The centre-of-core pins (clk / rst_n cluster at y 124.5 inside head*_e0, 3 markers in 1450) are the one place where
   an exact view would help. Take them when the e0 database is exported with the next signed head-core build.

## 3. First KV kits after kit_rtl passes

State at 20:03 (REPORTED KV-102): tree `src_kv_kvgeom7u_c1` has all of `tools/` from main 8989ba7b1755; 7u on it:
G0 0 errors, R8 recheck 0, LATCHECK 2404/2404; strict bind fails only on 64 `HARD_CORE_PARAM_ALL` errors
(pv_join_t RESET_PIN 1 vs 0, 16 pv types). Smoke bind with `OT_HCPARAM_ALL=0`, kit_rtl smoke pending.

### 3a. hg / hgi: the ring split (KV-HGSPLIT)

MEASURED from `lanes/handoff/KV-HGSPLIT-1115-rows.tsv` (106 rows, 103 OK, 3 NO_SITE, 16 masters), column `disp_um`:

| | value |
|---|---|
| median | 212 um |
| 90th percentile | 1175 um |
| maximum | 1560 um (kv3_hgi_v3 ft27_i) |
| over 110 um | 80 of 103 |
| over 340 um | 34 of 103 |

- The 15:10 post gave median 9 um, maximum 226 um. The later site rules (8.64 um off clock taps, 4.33 um off reset
  sites and station bits, tap table byte-equal to 7u) pushed the cores away. I read `disp_um` as the distance from the
  old band to the core site; if the file is older than v18, KV-HGSPLIT should restate the numbers for v20.
- A ring core 1.2-1.5 mm from its band puts an unregistered bus of 652-1560 bits across the type between the face
  pins and the ring. The plan's own hop law is about 340 um per cycle. These 34 rings will not meet -42 ps.
- The reset relay renumbering (18 EMIT errors on v18) is the same root: the reset solver, the tap grid and the raw
  rows all depend on where hard cores sit, and each was fitted as a separate pass.
- 3 rings stay soft (`i_ectl_Q_N_tN` W1560 on hgi_v3 / v4 / v5): no site.

Fix, in order:

1. Put the ring core where the band was and move the taps, reset sites and stations of that type around it, in one
   compose step. The band is already reserved area on the face; taps inside it are the things to move. Accept a
   changed tap table for the 19 hg / hgi types (they have no signed kit to protect). Gate: `disp_um` at most 110 um
   for every ring, or a station row for the excess with its cycle declared.
2. Fixed compose order for these types: hgsplit -> tap / reset solve -> RAWFIX raw rows -> bind. Raw rows are
   generated output of the bind, never carried as literals across a delta.
3. Before volume: list the 16 ring masters with sign-off state. Unsigned masters make every hg kit a WAIT-CHILD.
4. Do not launch any hg / hgi type on 7u without the split: the plan cell estimates are 3.0-5.0 M (REPORTED KV-102).

### 3b. pv: core_link_pipe depth (KV-PVGEN)

- D = 3 on 1275-1337 um legs is 425-446 um per stage. The plan hop law used by KV-PVGEN itself is 340 um. MEASURED
  from its own numbers: three stages leave each hop about 100 um over. D = 4 gives 319-334 um.
- The depth is cheap to change now and expensive later: +3 already moves every matched source to 9 / 9 / 10 and
  TRUNK_D 63 -> 73. Decide D once, from a placed CTS read of one pv type on 7p, before the pin table is adopted.
- The FIRM sites of the `u_pc_lp_*` stages decide the result; with no sites the placer clumps the 256-bit groups at
  one end. They are plan rows (KV-PVGEN ask 4) and I find no post that they are in 7p.
- 143 pv bands stayed one-column (pv_v7 48, pv_v12 47, pv_v3 / v3n 15 each; REPORTED KV-102): those types will fail
  place on the band, not on timing. Do not launch pv_v3 / v7 / v12 from 7p before PLACED-SCAN posts the station form.
- A bind made with `OT_HCPARAM_ALL=0` is for the smoke only. No pv kit from it.

### 3c. DRT-0255 on kv3_io_cor, kv3_hroot, kv3_sys_SD

- Same class as the QC / S81 ring nets (section 2 row 3). DRT0255-PROOF 20:00: the gcell cut (C2) failed 3 of 3
  including c2_hroot; obstruction variant B failed; the die-phase PDN without keep-out passed iteration 1 on t49 and
  is still clean on hd_spn / hd_ctl. REPORTED.
- kv3_sys_SD_v1 and kv3_io_ft_v1 signed off today on the same flow (REPORTED 16:15), so the KV failures are local
  to where a ring sits against the PG rows, not the whole die.
- For KV: wait for the die-phase verdict (iteration 2 on hd_spn / hd_ctl), then one KV proof on kv3_io_cor from 7u
  with the same keys. No band_spread, no keep-out, no unchanged relaunch.

## 4. Ranked fixes

| # | fix | basis | owner |
|---|---|---|---|
| 1 | q2: persistent full-edge M3 strips (1c fix 1), sign off this database | MEASURED 1a | KV-Q2-CLK-1115 |
| 2 | Ring split: cores at the band, taps / reset / stations re-solved around them; gate on `disp_um` | MEASURED 3a | KV-HGSPLIT-1115, KV-102 |
| 3 | Post the c1 tree sha after the smoke; lift holds for non-pv, non-hg types only; hub_C, pc, phy, io_ft first | REPORTED 20:03 | KV-102, WAVE-HOLDS-1115 |
| 4 | pv: D from one placed CTS read (3 vs 4), FIRM sites for `u_pc_lp_*` in 7p | MEASURED 3b (arithmetic), INFERENCE on timing | KV-PVGEN, KV-102 |
| 5 | Macro-edge strips + site check in `macro_sites.py` (1c fixes 2, 4); y 13.50 on the next q0-q3 rebuild | MEASURED 1b | KV-ECTLK-RL |
| 6 | GRT iteration bound 15 on full and incremental route for types with hard cores | MEASURED 1450 | GENBUG-IMPL |
| 7 | One kv3_io_cor proof on 7u with the die-phase PG keys once DRT0255-PROOF posts the verdict | REPORTED | TYPES-KV-FAIL-1115 |
| 8 | List sign-off state of the 16 ring masters | 3a | KV-HGSPLIT-1115 |

## 5. Stop list

1. No further q2 re-route without a persistent obstruction; no LEF OBS shrink; no SRAM move on the current q2 database.
2. No pinwire, cut-back or window view for the 13 KV hard-core LEFs; no lane on "pin access" for head cores.
3. No hg / hgi launch on 7u without the split, and no adoption of a split delta with a ring over 340 um from its band
   and no station row.
4. No literal `landing_raw_branches` rows carried across a delta that adds or moves a hard core.
5. No pv kit from a bind with `OT_HCPARAM_ALL=0`; no pv_v3 / v7 / v12 launch before the station form.
6. No unchanged DRT-0255 relaunch of io_cor / hroot / sys_SD; no band_spread or keep-out for it.
7. FABLE-PD-KV-1450 section 4 stays in force.

## 6. Not checked

- Why the detail router does not leave the y 13.230 track by itself (1a last bullet).
- q1 and kv3_pv_pair SRAM sites against the edge test.
- The age of `KV-HGSPLIT-1115-rows.tsv` against v18 / v20, and the exact meaning of `disp_um` (read from the 15:10 post).
- Whether y 54.432 on kv3_io_cor is an M6 PG pair row: the kit files are deleted, only logs remain.
- Timing of any pv leg at D 3 or D 4; no placed pv kit on 7u / 7p exists.
