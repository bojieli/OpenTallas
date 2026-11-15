# FABLE-PLAN-EVENTS: review of in-flight structural plan events (2026-11-14 ~19:00 PST)

Read-only review, run in parallel with the binds; no bind is held by it. Event 1 was checked by the main reviewer; events 2-5 by parallel reviewers, with two findings re-checked by the main reviewer (marked "re-checked"). Statements marked "inference" were not measured.

| # | event | owner lane | verdict |
|---|---|---|---|
| 1 | S81 B5 | S81-LEAF-PLAN | PASS to bind; 3 amends go into B6 |
| 1 | S81 B6 (t34) | S81-LEAF-PLAN | AMEND before compose |
| 2 | S81 B3zs PG domains | DIE-S81-92 | PASS; 2 stale rects for the next event |
| 2 | SERDES-TXPIPE +1 stage | SERDES-TXPIPE | AMEND before RTL: +1 does not cover the distance |
| 3 | QC S3R3 | DIE-QC-103 | PASS |
| 3 | QC S3R2 pin move | DIE-QC-103 | AMEND, non-blocking |
| 4 | HEAD hd_ctl rp21z17 | HEAD-99 | AMEND before the private route |
| 5 | KV next event | KV-102 | AMEND: wait for the CTS canary; reuse tap_pair_affinity |

## 1. S81 B5 (B4L4 + 5 edge-squeeze leaf types) and planned B6 (t34 SW corner)

Owner lane: S81-LEAF-PLAN (cc TL-LEAFT34, DIE-S81-92). Verdict: **B5 PASS to bind, with 3 AMENDs for B6. B6 as described: AMEND before it is composed.**

Evidence: epyc7 `/srv/opentallas-scratch2/claude/s81-leaf-plan` `ev/B4L4.json` (58f4d1f24d2e), `ev/B5.json` (9d4bee9ea054), `cp5/*.log`, `cp6/t34*.log`, `run/b/G0B5/g0.log`, `log/compose_B5.log`. All numbers below were recomputed from the two plan JSONs unless a log is named.

### Measured root cause
TL-LEAFT34 (queue 18:2x): t34 a14 GRT ran 6.7 h without closing; the hot strip is x ~40 um on the W edge, capacity 5-8 against use 6-11, and ft5/ft2/ft1 nets dominate. In the plan, t34 `u_ve.u_m` sits 34.56 um off the W face and five N<->S ft chains run through that strip.

I measured the same thing on every type: at each y, the ft bits whose register chain runs inside the W strip, divided by the M5 + M7 tracks of the strip (36.5 tracks/um; `ft_slots[].layers` = M7, M5). This is a plan model, not a GRT result.

| type | B4L4 strip um / bits / share of M5+M7 | B5 strip um / bits / share |
|---|---|---|
| t24__cl81374cd8 | 25.92 / 944 / 1.00 | 112.3 / 2093 / 0.51 |
| t44__clf4ea6d4b | 43.2 / 1817 / 1.15 | 86.4 / 1817 / 0.58 |
| t4 | 43.2 / 1817 / 1.15 | 86.4 / 1817 / 0.58 |
| t53__clb66fa5cb | 34.56 / 1265 / 1.00 | 86.4 / 1265 / 0.40 |
| t45 | 77.76 / 2721 / 0.96 | 86.4 / 2721 / **0.86** |

### Does B5 fix it
- Yes for t24, t44, t4, t53: the ft share of the strip halves (1.00-1.15 down to 0.40-0.58). Every core in the 5 types is at least 86.4 um off the W face.
- **Not for t45**: the strip grows only 77.76 -> 86.4 um and still carries 2721 bits (ft0, ft1, ft2) at y 773, which is 86 % of the M5 + M7 tracks before any other net. That is above t21 (0.70); t34, the one measured GRT failure, is at 1.34. Inference: t45 stays at risk of the same GRT class.
- No core overlaps, no ft register under a core, max station hop 359.9-403.7 um (limit 405), in all 5 types.
- Die tables are untouched: `latency`, `lanes`, `ports`, `partitions`, `budgets`, `clock`, `reset` are identical between B4L4 and B5. Each of the 5 types has exactly one instance (s_6N_L3, s_5S_L3, s_5S_L2, s_0S_L3, s_1N_L3), so the cycle adds reach no other leaf.
- Cycle adds match the handoff: t44 +20 station rows and t4 +20 (vn -> vp.u_b0/u_b1, vni +1), t45 +52 (u, ver, vni +1), t24 and t53 none. The LF_CS netlist diff shows exactly those nibbles. LATCHECK on the bind is the proof; it has not run yet.

### What B5 misses or moves
1. **Station registers left under moved cores.** core_place reports `failed` 4 (t24) and accepts the type: the apply condition (core_place.py line 2168) does not test `srep["failed"]`. In B5, t24 has 4 station registers 8.6 um inside `g_ln[12]` (261 bits), t44 has 14 inside `g_ln[10]`, `g_ln[9]`, `g_ln[5]` (532 bits, up to 36.7 um deep), t53 has 10 inside `g_ln[3]` (524 bits); all three had 0 in B4L4. G0 does not check internal station sites against cores (only hop length), so G0B5 will not show them. These types do not set `realize_internal_stations`, so the sites are a plan model and the placer is free; the harm is that the hop model is wrong there, not an illegal placement (inference).
2. **One stale detour.** t44 station 278 (`u_vn.u_b.hw_d` -> `g_ln[11]`, 256 bits): pins are 136 um apart, the kept route goes 296 um west to x 164, then back (576 um total), through the strip B5 has just cleared.
3. **Narrower core slots.** Core pairs facing each other across less than 43.2 um: t24 34 -> 38, t44 33 -> 38, t45 24 -> 26, t4 38 -> 42, t53 29 -> 35; the smallest gap falls to 4.32-6.48 um (for example t24 `vn_a`|`vq` 4.32 um over 172.8 um). compose_B5.log shows the same as R-LEAF-3 +22. This is the congestion that moved; the short vn -> ln links with 2 registers (36 um long in t24) now have no room between the cores.
4. Clock: t45 `clk_t34` radius 292.7 um against a 200 target (was not listed in G0L4), `clk_t44` 1095 sinks. Advisory.

### B4L4 bind
`log/B4L4_bind.log`: `ELAB_RC=2`, `B4L4_RC=4` at 18:49 PST; `run/b/B4L4/elab.log` says `yosys failed (rc 137)`. That is a kill signal, not a plan error; epyc7 had 969 of 1007 GB in use one minute later. I could not read the kill record, so the memory cause is inference. B5 on epyc8 (which contains B4L4) was still in elaboration at 18:50.

### B6 (t34 SW corner)
- The cp6 trials (`t34b`, `t34s0`, `t34s4`, `t34_R0`; vq seeded at x 552.96) are all `applied False`: `ft_failed_slots ['ft2']`, and they need `link_reg u 13, y 8` plus `bus_reg leafup_o0: 4`. The last one is a register on the 668-bit S-face output bus, which is a die lane, so it changes the lane table and its partner. That is a larger event than "+1 register on 4 face links" suggests.
- The street only moves ft2 and ft5. The W strip then still holds ft0, ft1, ft3, ft4 = 1095 bits in 34.56 um = 0.87 of M5 + M7 (now 1692 bits = 1.34). That is the t45 level, not the 0.4-0.6 level of the types B5 fixed.
- The street itself is short: vsw spans y 423-648 and vq y 527-657, so it relieves only that 120 um stretch; below y 423 the gap x 389-570 is already 181 um wide.
- The cause in t34 is that `ve_m` and `ve_s` (x 34.6-388.8, y 34.6-423.4) cover the S windows of ft0-ft4 (x 6-394), so those chains must go round the pair. Same form in the ve-pair types.
- By the same measure the other open types are worse than t34: t28 2.03, t71 1.66, t51 1.28, t13 1.18, t7 1.15, t10 and t74 1.00. t73 (0.27), t1 (0.50), t75 (0.57) are not edge-squeeze cases; their problem is the ve pair against the face windows.

### AMENDs
- A1 (B6, t45): add t45 to B6; it needs a strip of about 130 um or one of ft0/ft1/ft2 moved off the W edge.
- A2 (tool): make `failed > 0` block the apply in core_place, or re-site those stations; fix the 28 registers and t44 station 278 in B6.
- A3 (B6 form, proposal, not measured): for the ve-pair family, pass the N<->S ft chains straight over `ve_m`/`ve_s` on M9 (cores stop at M7; the pair is 345.6 um tall, under the 405 um reach) under the owner's M8/M9 ruling, instead of round the W strip. Needs the die clock/power M9 shapes imported as obstructions and a count of free M9 tracks first. This avoids the `leafup_o0` lane change.
- A4: decide the `leafup_o0` +1 as a lane-table change with DIE-S81-92 before composing B6, or pick a form that does not need it.

## 2. S81 serdes: B3zs PG-domain fix and SERDES-TXPIPE

Owner lanes: DIE-S81-92, SERDES-TXPIPE (cc TL-SERDEST14). Verdict: **B3zs PASS; SERDES-TXPIPE AMEND before RTL.**

### B3zs
- Plan epyc7 `/srv/opentallas-scratch2/claude/s81-b3-clk/ev/B3z2s.json` (bound as 61b772e20b3a). The diff against B3z2 is 96 numbers, each exactly -544.32: the 8 north domains' `rect_um`, `bumps.rect_um`, `phy_macro_um`, `core_strip_um`, `esd_um`, `bumps.exclude_um`, and 8 `die.io` rects.
- Recomputed for all 14 `lk_*` partitions: every domain lies inside its partition, PHY macro and bumps inside the domain, and the oriented `u_phy` content equals `phy_macro_um` on the 8 north and 4 west-south links. North partitions end at y 25876.8.
- Generator probe intel2 `~/s92/probe3b.log`: B3z2 6 ok / 5 bad, B3z2s 11 ok / 0 bad. This fixes the measured cause.
- **Missed (re-checked):** `die.io[io_lk_WN2_u_phy].bump_exclude_um` and `io_lk_EN3_u_phy.bump_exclude_um` still read y 25924.8-26421.12, above the die outline y 25980.48. No other field carries an old value.
- Inference from `die_io.py` lines 427-429 and 656-659: G0 will raise 4 new errors on these two rects. `run_bind_b3.sh` only echoes `G0_RC`, so the bind is not stopped. Fix with -544.32 in the next event.
- Not touched and older: for `phy_lk_ES0`/`ES1`, `phy_macro_um` does not equal the `u_phy` content; the probe passes them.
- Bind on epyc8 `log/B3zs.log`: sidecar RC 0, G0 running, no BIND_RC at review time.

### SERDES-TXPIPE
- The lane started about 18:45 (epyc10 `/srv/opentallas-scratch2/claude/serdes-txpipe`); there is a base equivalence bench and no RTL delta yet. Keeping TX +1 out of the B3zs bind is correct, since LATCHECK compares plan with bound RTL.
- Measured miss (TL-SERDEST14, t14 `4_cts_final.rpt`): slack -718.9 ps = 1199.9 ps of net through 27 repeaters (about 44 ps per 100 um) plus 159 ps clock skew (launch 465.9, capture 306.7). The budget for clk-to-Q plus net is 583.7 ps.
- Plan geometry of t14: `u_ptx` spans x 244.5-2490.9; the `coll_i0` source band is on the E face at x 2845-2868. The farthest d pin is about 3080 um away.
- Inference: at 0.44 ps/um that is about 1355 ps of wire, which needs 3 segments, so +2 stages. One stage, ideally placed, lands near 0 ps on the far bits. +1 is enough only with the register rows pitch-matched along the 2246 um macro and the 159 ps skew removed.
- HARD-S81-SERDES-1's `LANE_TXA`/`LANE_RXI` parameters (bench16 PASS, branch `claude/hard-s81-serdes-1-1113`) already give this; the plan defines for t14 carry only `OT_KP4_DEC_HARD`.
- RX side (inference): a new face register on the deep `io_pma_rck` tree stays in the hold class already measured (-223.6 ps at `u_dec.u_face_p_d` on t14).

## 3. QC S3R3 and the S3R2 pin move

Owner lane: DIE-QC-103 (cc TL-QCSTAV2). Verdict: **S3R3 PASS; S3R2 pin move AMEND, non-blocking.** Paths on epyc9 `/srv/opentallas-scratch/claude/die-qc-103/`.

### S3R3
- The S3R2 -> S3R3 diff is 80 fields: 16 hard-core rows (4 types x `u_r0..3`), changing only module, physical_master, HI_PAD, SKEW_N, SKEW_S.
- The bound RTL (`bind_s29q103S3R2/rtl/<type>.sv`) carries HI_PAD/SKEW_N/SKEW_S of 18/6/8 (both slw types), 18/6/7 and 17/6/7 (the two sle types). The S3R3 rows match exactly, so the cause is fixed.
- Sweep of all 188 `param_wrap` rows against bound RTL: 160 match, 0 mismatch, 28 not checkable (no RTL under the `__v1` names).
- The three masters are distinct: SKEW_S sets an SRAM delay depth and two ring delays, HI_PAD sets three pad pipelines; they differ by one stage each.
- No lane or latency rows change. S3R2 LATCHECK was 1921/1921; S3R3 bind was at 334 of about 404 RTL files at review time.
- Risk: the values come from transport latency at bind time (`qc_fabric_transport.py:175`, `HI_PAD = sh - nh`). A later st_a N/S lane-cycle change makes the masters stale; `wrap_bound` catches it, at the cost of core rebuilds.
- Open: the old signed `sta_region_nb0` (0/14/14) has no plan reference left; the 3 new masters are unsigned, so 4 parent types (6 partitions) wait on them; no S3R3 G0 process was found.

### S3R2 pin move
- 5 fields: `cland_tstart_in` y 174.95 -> 167.392 at x 158.176 on M7 in the 5 su_l0 types (12 partitions). It is an interior pin with no die-side copy, and the new site is clear by 2 um of cores and bands.
- It does not remove the mechanism. The DRC report (epyc8 `.../s29q103S/items/slw_su_l0__cl76fb247e/attempt_4/.../5_route_drc.rpt`) shows a 0.032 wide wire running lengthwise past the top of a 0.08 wide pin; that trips Rect Only at any y.
- The support for the new site is that 13 other types use it and route clean, but those are st_a/st_b floorplans, not su_l0.
- Amend: if the first rebuilt su_l0 route shows Rect Only again, make the pin wire-width (0.032) or add a via-only access blockage for this pin class.
- Still open: 2 face-density G0 errors (7.2 pins/um against 6) carry into S3P.

## 4. HEAD hd_ctl macro move (rp21z17)

Owner lane: HEAD-99. Verdict: **AMEND before the private route** (the prep may continue). Plans epyc7 `/srv/opentallas-scratch/claude/head-99/rp21z16.json`, `rp21z17d.json`; a6 dump under `.../head_rp21z4_1113/items/hd_ctl/attempt_6/geom/`.

- Congestion is not the failure: a6 GRT overflow is 0 after 2 iterations, M2/M3 use 13-14 %, fill 9.9 %. The failures are reach (r2r 907.6 um, 413 captures over 405 um) and clock (clk_t13 3327 sinks).
- The long pairs, from `geom.tsv`: 733 source FFs have a capture beyond 405 um. 356 are `wd2[]` -> SRAM (250 to xb0, 106 to xb1). About 280 run between fixed faces (`u_ht.u_txo` -> `u_bout_h_tx_o` 136 at 606 um, `u_hr.u_rxi` 48, `ro[]` -> `u_bout_lepk_o0` 47, `u_bin_n_rx_i` 35, 16 landing monitor flops at 584-908 um). The macro move does not change those; they need a register stage.
- SRAM topology: write data is shared by {xa0, xb0} and {xa1, xb1} (512 and 511 common `wd2` registers, 0 across). z17 stacks the macros S to N as xa0, xb1, xa1, xb0, so the xa0/xb0 write pair is 350 um apart in y (259 in z16). All 1585 macro pins are on the W edge.
- Macro positions (re-checked): xa0 (345.6, 38.88), xb1 (311.04, 138.24), xa1 (345.6, 285.12), xb0 (345.6, 388.8), each 171.29 x 77.78. Gaps: xa0-xb1 21.6 um, xa1-xb0 25.9 um; R-STREET-1 asks for abutment or 43.2 um.
- xa0 sits 38.88 um above 591 S-face pins (3.45 pins/um), under the 43.2 um of R-STREET-2.
- Landing bands were not re-sited: xa0 covers 49 % of the `h_rx_i` band and cuts the `a_rx_i` band into three pieces (free 1003 um2 against a reserve of 1189.9). Inference: `a_rx_i` fails at placement. `cland_band_fit.py` is not called by prepare.
- `rst_start_raw_3` `xy_um` (513.0, 102.6) is now inside xa0; 4 of 5 export coordinates are stale. `prep21z17x/republish.log` ended with `ValueError: raw reset source is not the recorded registered relay: u_rrl_61.rst_rl_61`; rp21z17d came after it.
- Confirmed good: taps 34 -> 68, none over a macro; reset relays 82 -> 145, depth 3 unchanged, export depths kept.
- Amend: place the SRAMs as a 2x2 block or in the order xa0, xb0, xa1, xb1 with streets of 43.2 um or more and 43.2 um off the S face; run `cland_band_fit` on hd_ctl; add one register on the face-to-face classes above.

## 5. KV next event

Owner lane: KV-102 (cc TYPE-KVIOFT, KIT-OPS-5). Verdict: **AMEND; do not bind before the CTS canary reports.**

### kv3_pc `core_taps` and `-no_insertion_delay`
- Measured (epyc2 `.../kvgeom4/items/kv3_pc__cl254f2e73/attempt_2/.../4_1_cts.log`): 99 delay buffers, tap means 209-574 ps (spread 365 against a 250 target); cl4ea58a5c has 75 buffers, 193-565 ps. FF reg-to-reg hold is below the -320/-400 stop, which contradicts KV-102's "tree skew nets to about 0". The root cause is right.
- The plan already has `core_taps: "internal"` with 8 core taps at 250 ps on all 6 pc types (epyc10 `kv-102/cg3/plan_band.json`); the change is internal to early.
- Miss: `pair.py add_core_taps` re-adds only pins above 210 ps. The 4 pcf cores (193-196 ps) fall back to grid taps, whose pin legs measure 82-157 ps, so 278-353 ps effective. Inference: reg-to-pcf hold stays 28-100 ps short.
- Cost: about 128 new early taps (32 partitions x 4) on top of 1568.
- Die skew is not hidden: the type insertion stays 250 ps and the flag makes the kit meet it.
- Not checked: 12-13 non-core macro sinks on clk_t11; `CTS_ARGS` is also exported by `OT_CTS_NO_NDR`, so one export can override the other.
- The canary (epyc8 `kv-102/ctscan`) was still in CTS. Pass should need all 8 OT_TAP_CORE lines within 20 ps, not spread alone.

### `sender_ps_types`
- Keyed by receiver type, so unlisted types keep -385 ps. It removes only the 1515 / 2211 advisory port paths; it is not the gate fix. The value is a receiver-side assertion left to die STA; measure it after the CTS fix.

### Same-tap rule for kv3_io_ft_v1
- Confirmed: 137 of 164 failing endpoints are `u_dsel/y -> u_ft_ftN_o_0/q`, worst -30.64 ps (`typekvioft/out/hold_dump.tsv`).
- Correction to FABLE-HARD-KV: the 156.8 ps pair in `pair_skew.tsv` is `cland_reader_start_ft1_i_1 -> _2`, not this family.
- Do not add a new rule to `clock_taps.tcl`: `clock.tap_pair_affinity` (with `ring_depth`, `ring_pair_um`) already exists in the KV tree and R-CLOCK-2a prescribes it. Add `tap_post_merge_min_sinks` (QC ring bonding left a tap with 1 sink).
- Capacity is fine (largest tap 1092 sinks, cap 3000); clock pins only, so no LATCHECK or ft effect.
- Extend it to the pc types: the cl4ea58a5c -563 ps path is a ring `dsel` pair split across clk_t32 and clk_t14.
