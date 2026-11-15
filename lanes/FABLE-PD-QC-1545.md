# FABLE-PD-QC-1545: structural review of QC plan event S4q6

2026-11-15 15:50 PST, FABLE-PD-QC-1545. Read-only. Nothing stopped, changed or launched except six small read-only
python checks through ot-run on epyc9.
Subject: epyc9:/srv/opentallas-scratch2/claude/die-qc-103/treeA/physical/die_plan/qwen_compute/plan_of_record/
zz_s29_qc103_s4q6.json (+ sidecars), compared with s4q3b / s4q3c / s4q4c and QC-SC-ROWS s4q3csb.
Scripts and outputs: epyc9:/srv/opentallas-scratch2/claude/fable-pd-qc-1545/ (b1..b6.py, b1..b6.out).
MEASURED = read or computed by me today from those plans / the named kit. INFERENCE is marked.
State when written: S4q6 bind (run9 first bind) and treeA G0 (g0A_s4q6) still running; neither result is in this review.

## 0. Verdict

**S4q6 is structurally sound in geometry (straps, bands, hc strip, new station rows), with one functional error that
must be fixed before adoption: the sc <-> fe lanes are priced 1 cycle and the plan carries 3 stations on each of them.**
Neither 1 nor 2 is right. The answer is the sum, 3 (4 on one lane). It is a lane latency error, not a reach error, and
the as-bound LATCHECK does not see it.

## 1. Ranked findings

| # | finding | mark | owner |
|---|---|---|---|
| F1 | **sc/fe lanes: fixed_cycles 1, stations 3.** In S4q6 the sc types carry the QC-SC-ROWS row (`x_fe_o` / `x_fe_i`, 1 station) AND the fe types carry the S4q4c row (`x_sc_i` / `x_sc_o`, 2 stations). Bind rule (native_istations.annotate, reach_fix.native_rule, QC-FWST's own note "lane bumps SUM the src-end and dst-end station deltas"): fixed_cycles = source stations + destination stations. Per lane (src, dst, fixed): 11 x `sl_*_sc__x_sc_fe` (1, 2, 1); 11 x `sl_*_fe__x_fe_sc` (2, 1, 1); 1 x `sl_*_sc__x_sc_fe` on the sle_sc_v3 / sle_fe_v3 pair (2, 2, 2). Latency table: `sl_W5_sc__x_sc_fe` cycles 3 = boundary 2 + fixed 1. Each owner priced its own end only (S4q4c alone: 0 + 2 = 2, correct; s4q3csb alone: 1 + 0 = 1, correct); the merge took one side instead of adding. These 23 are the ONLY lanes in S4q6 with fixed below source + destination (1,372 stationed lanes checked; the other 150 mismatches have fixed above the sum, all present in S4q4c or s4q3csb already). | MEASURED | DIE-QC-103 |
| F1b | Physical distance agrees with 3. sc leaf pin (546.96, 984.96) -> 1 station -> E face: 655-790 um in 2 hops of 328-395 um; fe W face -> 2 stations -> core centre (311.04, 915.84): 831-966 um in 3 hops of 277-322 um. Whole link 1,500-1,760 um, 5 flops (3 stations + 2 face flops), longest hop 395.2 um (slw_sc_v2/v3 `x_fe_o`). The v3 pair: sc 947 um with 2 stations (3 x 315.6), fe 1,122 um with 2 stations (3 x 374.0), so 4. With all stations built there is no setup risk from distance (every hop under 405). Setup fails only if someone removes stations to match the 1: the sc end alone would be one 655-790-um hop, the fe end one 831-966-um hop. | MEASURED hops, INFERENCE on the consequence | DIE-QC-103 |
| F1c | What happens if adopted as is: kit_istations builds "exactly len(regs_um) stages" per bus in each kit, so the built lane has 3 station cycles against 1 in `qwen_compute_lat_pkg.sv` (`LAT_SL_*_SC__X_SC_FE`): +2 cycles on 22 lanes, +2 on the v3 lane, in both directions. The bind lands only fixed_cycles as pads, so LATCHECK `--pricing as-bound` compares bind with table and passes (same blind spot as the 63 QC lane errors of 11-12). The lanes are in no latency_group (0 of 12 groups name them), so nothing else balances them. | tool text MEASURED, outcome INFERENCE | DIE-QC-103 |
| F2 | **Strap sites: no collision.** 56 moved `strap_u_t_*_tile_id` on 14 cb types against the S4q6 plan: 0 inside a core bbox + 4.32 um, 0 inside any landing band (including the bands deepened after the straps were applied), 0 within 8.64 um of a clock tap, edge-clock tap or reset tap; every column is 6.46-6.50 um off its core face. Against generated pins (kit qc-cb-gen-1115/gen1/cbn_q11__cl5cc92dfe/plan_pins.json, 4,351 pins, 223 interior): generated interior pins are clk_t* (86) / clk_c* (4) / fclk / cland / arst_n / start_i, all on M7; straps are M5. Nearest generated pin to a moved strap site 58.0 um (clk_t66); 0 other M5 pins on any strap's M5 track. cb has no reset spine pins (one arst_n M7 pin). | MEASURED (kit pins for cbn_q11 cl5cc92dfe only; other 13 types against plan data only) | QC-CB-GEN-1115 |
| F2b | Near objects are FIRM cell sites, not pins: reset relay cells 2.2 um from the strap column on 4 straps (cbf_q00 x2 `u_t_0_1` rst_rl_521 / 515; cbn_q11 cl5cc92dfe `u_t_2_2` rst_rl_166, `u_t_2_3` rst_rl_345); reader-start stages 2.9-6.5 um (cbn_q01 clab6e67f2 / cld9ff4c40 `u_t_0_2`, `u_t_0_3`; cbf_q00 `u_t_0_1`); fab `a_d` pipe relay sites r[1] / r[4] 4.3-7.1 um on 9 straps (cbf_q11, cbn_q11 x2, cbx_q10 x4 `u_t_3_*`). Effect is 16 strap input buffers legalised beside FIRM flops. No move needed. | MEASURED positions, INFERENCE effect | none |
| F3 | **The 28 non-fitting cb bands are three classes, and only 6 are real.** All 28 sit at 1.17-1.19 flops/um2; the other 53 are at 0.82-1.00. (a) 10 are not bands at all: cbn_q00 cl622f65d2 (and cldbcda913, same rects) hold `cl_na_i00`, `cl_rsf_i`, `cl_nb_i00`, `cl_bc_i00`, `cl_bc_i10` as HARD CORES of 88.56 x 51.84; the band rect is the macro, the tool fails on overlap with its own core, and a strip density key does not apply. (b) 12 are "NO FIT hop" 2,540-3,856 um: gen_cb_strip.py prices the hop as `abs(x - px) + abs(y)`, which is the S face only; all 12 are N- or E-face buses (`nb_i12` E x5, `na_i00` / `nb_i00` N x7) and their real pin-to-band hop is 113-226 um. (c) 6 are real: `na_i22` on cbf_q11 and cbn_q11 x2 (SW corner, blocked above by `bc_i22` at y 108.288), `na_i00` on cbn_q00 cld7bf7197 (140.4 x 32.4 at the N face), `rsf_i` on cbn_q01 cldd6ea846 / clab6e67f2. | MEASURED | DIE-QC-103 (tool, classes a and b), QC-CB-GEN-1115 (class c) |
| F4 | **cbn_q11 clump is unchanged in kind.** W strip x 19.44-71.28 holds `na_i22` (y 17.28-106.13, 1.17) and directly above it `bc_i22` (y 108.29-214.13, 1.00): 10,800 ring flops in 10,200 um2 over 197 um of one 51.84-um column. `bc_i22` pins are on the S face at x 94-183 and its u_bin is at (352, 54) in the S strip, so the bus goes west and up into the W strip (max hop 316.8 um) and then back east. The S strip under u_t22 (x 86.4-544.3, y 17.28-64.8, about 21,700 um2) holds only `nb_i22` as a 419 x 12.96 sliver. The 12 `strap_ca_k_*_i22` crossers still start at the hub (622, 1305-1326). | MEASURED | QC-CB-GEN-1115 |
| F5 | **hc strip: 5 rows is 0.53 flops/um2, one fifth of the failing form; expect the kit GRT to close.** Pilot place log (qc-hc-strip-1115/pilot/slw_hc1 cl144ee7b3): "2.65 flops/um2 at rows 1, target 0.45 -> rows 5 (needs 6, band fits 5, 218 columns, 8902 flops)", strip 64.80 um deep over pin x 4.83-409.08. Geom GRT: 0 overflow after 1 extra iteration, 3 min 13 s, usage M2 22.5 / M3 28.9 / M4 6.7 / M5 8.1 %. The S3R form failed the same geom GRT (stuck at iteration 10 of 50), so geom GRT does see this failure. The strip spans the whole pin window, not the band x range 149-408: at x 17-69, y 9-57 it shares ground with the `rs_n1` ring (2,983 FIRM flops), and the pilot's worst column estimate is exactly there: col_v 0.872 at (20.0, 57.5). | MEASURED; kit GRT outcome INFERENCE | QC-HC-STRIP-1115 |
| F5b | Sixth row: 6 x 12.96 = 77.76 needs more than the 77.76-um band; the cap y < 89 comes from the `x_hc0_ctl_i` band (64-bit ring, 84 x 4.6 um at y 96.8-101.5). Not needed for routing on this evidence. `sle_hc1__cl22c1ff36` has 71.28 um (others 77.76): expect 4 rows there. hc2 (6 types, bands 43.2-45.4 um deep, 441-482 wide) has no pilot at all. | MEASURED rects, INFERENCE rows | QC-HC-STRIP-1115 |
| F6 | **New station rows: no reach problem.** 653 new or changed `internal_stations` rows in the 78 types: 618 have every hop at or under 405 um; 35 have a first hop of 413-584 um that the sidecar u_bin splits at mid hop (QC-FWST form; sidecar rows present in S4q6, both halves under 405). Largest: slw_fw_v3 `dr_wi` 584 -> 292 + 292. Flops added by rows per type: fw 18,500-19,700, fe 4,900-14,400, su_c 9,550-11,500, st_b 2,854, sc 375. Only two row sites of different buses fall within 20 um of each other with more than 1,500 bits (fw `x_ctl_i` + `st_eo` / `st_wo`, 1,718 bits, 4 types). | MEASURED | QC-FWST |
| F6b | Baseline, not S4q6: 24 cb rows keep hops above 405 um (cbf_q00_s2 `bc_i10` 1,022 / 1,026 with no sidecar row; `bc_i00` / `bc_i10` / `bc_i30` 610-637 with sidecar; `nb_i12` 411-418; `y_o00` 413). Unchanged since S4q3c. | MEASURED | QC-CB-GEN-1115 (cbf_q00_s2 `bc_i10` first) |

## 2. Ranked fixes

1. **DIE-QC-103, before READY+ADOPT (blocking, 15 min + rebind):** set fixed_cycles = source + destination stations on
   the 23 sc/fe lanes (22 x 3, the sle_sc_v3 lane 4), `gen.py latency --inplace`, rebind as S4q6b. Let the running
   bind finish for everything else. Add to merge_s4q6.py: after the merge, list every lane with fixed below
   source + destination stations (b3.py does it in 40 s) and fail on any; an add-add on fixed_cycles from two row
   owners is a sum of deltas, never a pick. QC-FWST and QC-SC-ROWS-1115 confirm their end counts (2 and 1).
2. **KIT-OPS-5 + QC-HC-STRIP-1115:** first slw_hc1 kit to 5_1_grt on the adopted plan. Valid only if the place log
   says "target 0.45 -> rows 5"; "target 1.0" means the item_env was not applied. Read: overflow at y < 90 split at
   x < 70 (rs_n1 overlap) and x 100-380 (old hotspot), and NDR drops on clk_t* / fclk_in_b_hw_i (was 20). If the only
   overflow is at x < 70: start the b_hw_i columns at x >= 71 (east of rs_n1), not a sixth row. One hc2 kit
   alongside (no evidence either way).
3. **DIE-QC-103 (tool, next event, not blocking):** gen_cb_strip.py: skip bands whose rect is a `cl_*` hard core
   (10); price the hop from the bus face (N: H - y, E: W - x, W: x). Then the 12 class-(b) bands get the same
   in-place growth as the 53 (INFERENCE: room not checked band by band).
4. **QC-CB-GEN-1115 (next event):** one ring per strip in the SW corner of cbn_q11 x2 and cbf_q11, by reshaping, not
   depth. Area arithmetic: `na_i22` alone in the W strip x 19.44-71.28, y 17.28-214 = 10,200 um2 = 0.53;
   `bc_i22` to the S strip under its own pins x 86.4-290, y 17.28-64.8 = 9,690 um2 = 0.56 (hop under 200 um instead
   of 317, and on the way to its u_bin); `nb_i22` S strip x 292-544 = 11,970 um2 = 0.45. Needs the u_bin / reader
   start sites of the three buses re-derived (sidecar). Then move `strap_ca_k_*` to their ring band. Same method for
   the other 3 class-(c) bands. INFERENCE until a cbn_q11 kit GRT is read; the gen1 pilot on epyc2 has only reached
   place (no congestion report yet).
5. **QC-CB-GEN-1115 (baseline risk):** cbf_q00_s2 `bc_i10` 1,022-um hops without a sidecar row.

## 3. Stop list

- Do not post READY+ADOPT for S4q6 with the sc/fe lanes at 1 (or at 2). Do not remove station rows to match the 1.
- Do not read LATCHECK 1921/1921 or a clean G0 as clearing those 23 lanes.
- Do not hand all 28 bands to a "per-cland region" lane: 10 are hard-core rings, 12 are a hop-formula artefact.
- Do not deepen `bc_i22` further in the W strip, and do not expect S4q6 to change the cbn_q11 SW overflow.
- Do not move the `strap_ca_k_*` sites before the ring bands are final; do not move tile_id straps again for F2b.
- Do not chase the sixth hc row, the `x_hc0_ctl_i` band or hc height (S4q5) before the kit GRT is read.
- Do not launch hc1 / hc2 wave kits without `OT_CLAND_STRIP_DENS=0.45` in the item env (rows fall back to the 1.0 count).
- Do not re-site fw / fe stations for the 35 long first hops: the u_bin split is in the sidecar.

## 4. Not checked

- Bind and G0 results of S4q6 (running). Whether the bind itself rejects the 23 lanes: sc/fe types are kit-built, and
  the kit pricing branch skips a lane whose fixed is below the source count instead of failing.
- Strap sites against generated pins of the 13 other cb types (no S4q6 kit exists); tile_id consumer pin coordinates
  (core pins file not in treeA at the recorded path).
- Any kit GRT on S4q6: none exists. cb band growth room for the 12 class-(b) bands. hc2 strip row count.
- Whether the sc/fe protocol tolerates +2; treated as a latency error because the table feeds LAT_* parameters.
- No database opened; all evidence is plan JSON, kit pin JSON and pilot logs.
