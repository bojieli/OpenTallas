# FABLE-PD-S81-1045: S81 stacked event B6gE (pre 6ceebbfa723b, composed b767a19db5ea): row interactions, M8 re-screen, families still failing, next deltas (2026-11-15 11:2x PST)

Read-only review, in parallel with the B6gE bind. Nothing launched, stopped or changed on the event.
MEASURED = rows, plans, logs and tools on epyc7 `s81-b3-clk` (`rows/`, `ev/B6gE_pre.json`, `ev/B6gE.json`, `log/B6gE.log`, `tools_B6gE`); my scripts epyc7 `/tmp/fable1045_a1.py` .. `a7.py`. INFERENCE is marked.
State at 11:10: compose OK (0 band failures of 1,255, landing contract 0 errors, start tree 233 uses / 0 open, boot 761). Lane sums: clock_landing 2,522, cycles 13,671 (= B6gslsw 13,551 + 120, the E2 price). G0 running. No G0, bind or LATCHECK result exists yet, so everything below is plan-level.

## 0. Verdict

1. The row stack is clean at key level: 0 unattributed changes against `B6gsl_or13_rp`, 0 rows without effect, 7 shared keys, all declared overrides. Bind and LATCHECK are not put at risk by anything I found.
2. It is **not consistent at geometry level for the clock taps**. The PHYT1 density taps were derived before the E2 stations and before the form J bands existed. In B6gE 7,658 E2 station flops and 46 band rects of the svc types, and 3,592 station flops of 2 grown slice_station types, sit 150-470 um from the nearest tap (tap radius 100 / 150). The svc tap problem that PHYT1 closed at 99 um is open again on B6gE.
3. Three things the launch post lists as in are not in: the `phy__t1` tap row (0 taps in the plan), the R2 strap depth (the CA table is the unchanged 07:37 `ca_swm`), and form R for t14 (ft5 S2 is still at (440, 400), the p1 form).
4. M8 clears none of the 13 screened leaf types by itself. 12 of them fail on a y-slot, which needs vertical tracks over a core (M7 only); M8 is horizontal.
5. After B6gE about 245 of 395 types still have a named structural cause: col 216 (reset), bk_sel__t2, svc 9, slice_station 4, phy__t1, leaf 14. They need two family-disjoint deltas, not six serial ones.

## 1. Row interactions (question 1)

Key level (MEASURED, `a1.py`, `a2.py`): tr4 217 types / 221 keys; PHYT1 44 / 210; keep_outs 76 die rows; E2 83 types / 123 keys + 61 die rows; core_tap_rebind 47; M8 restore 2 die rows. Shared keys, all `clock.taps`: bk_sel__t2 (tr4 then PHYT1, declared), leaf t21 / t37 / t25 cl431c660f (PHYT1 then rebind), leaf t33 / t58 / t68 (E2 then rebind). The rebind was generated on the stacked plan, so it kept the earlier values. keep_outs share no key with tr4 or E2 (76 of 76 are tr4 types, 10 are E2 types).

| # | interaction | number (MEASURED) | consequence | owner |
|---|---|---|---|---|
| a | E2 stations x PHYT1 taps, 6 svc types | station flops farther than 150 um from any tap: svc_hi t6 2,548, t1 2,268, svc_lo_w t1 1,028, svc_hi t5 770, svc_lo t6 713, svc_lo t7 331; worst 468 um. Log: svc_lo t6 `clk_t29` 2,216 sinks at 257 um; svc_lo_w t1 `clk_t19` 1,129 at 464 um; svc_hi t1 four taps 850-1,351 at 338-371 um | taps derived for a 100-um radius now carry 250-470 um leaves: clock spread and hold at CTS | S81-PHYT1 |
| b | form J / CA bands x PHYT1 taps, 8 svc types | PHYT1 saw the old bands of the base plan; compose re-placed them. 46 band rects have a corner more than 150 um from any tap (worst 427 um; hi t6 12, hi t3 8, lo t7 8) | ring flops are clock sinks with no tap in reach | S81-PHYT1 after compose |
| c | PHYT1 reserved tap sites x form J | the 8.64-um sites are obstacles of the multi-rect search, so the channels fragment: multi-rect pieces 68 -> 103 against B6gslswrp. svc_hi t6 `attnh_i0` 9 -> 16 rects (2.16-um side), t3 `attnh_i0` 5 -> 10, t3 `attn_i1` 4 -> 7, t4 `attn_i2` 3 -> 8. svc_hi t4 `hbm_i0` hop 287.8 -> 402.3. Bands with hop >= 401: 23 (was 22), >= 395: 41, none over 402.84 | the search stops at the reach limit, so these bands have used all free area in reach. One more obstacle (clock sites, added taps) gives "landing band absent" | S81-CA-BAND |
| d | reserved tap sites x single-rect bands | `_storage_band` does not read `tap_reserved_um` (only `_band_obstacles` and `cland_band_fit` do). 33 single-rect bands in 7 svc types overlap reserved sites, 2,395 um2 in total; largest svc_lo_w t1 `hbmrd_i0` 265 um2 of 13,269. Three of them are already at band use 1.63-1.67 (hi t6 `attn_i1`, lo t1 `ft0_i`, `idx_i0`) | 1-3 % of the band each: small, but it is the same code gap the clock site rows will hit | S81-CA-BAND (one line) |
| e | E2 outline growth x old taps, 4 slice_station types | t49 (1,226.88 -> 1,753.92): 2,566 station flops over 200 um from a tap, `clk_t49` 1,985 sinks at 586 um, 8 taps at 577-586 um, 3 empty taps. t24 cl64811a5d: `clk_t19` 2,407 at 598 um, `clk_t20` 2,055. t50 cl39451317: 5 taps at 473-495 um. t24 cl66b71008: 2 taps at 494 um | taps stayed on the old outline. Not blocked (LIMIT-BIND-1), so the kits generate and fail at CTS | S81-PHYT1 (taps), S81-LEAF-PLAN (says which outline) |
| f | tr4 hard_cores of bk_sel__t2 x idx overlay not in | the plan carries the signed idx view; the bound RTL is the old `dsdv_idx_l20s.sv` (RDL / WDL / WDC / SCS / RIL / RHP 0 against 1, FACE / PDC not declared) | `tools_B6gE/die_plan/bind.py` has no HARD_CORE_PARAM_ALL check, so the bind will not show it; the waiter check will | S81-TAPROWS |

Not interactions (checked, clean): bands on cores 0; ft station bit sites inside cores 0 (19 stages in B6gslswrp: E2 fixed t65, t14, t38, t32, t16); the 0850 item (d) bands of t68 / t24 are re-placed; core taps of the 6 E2 types with moved cores follow their cores.
Unchanged from B6gslswrp, not caused by B6gE: internal stations inside band rects on 35 leaf types (t8 4,598 flop bits, t72 3,661, t59 3,130, t46 2,120): `_band_obstacles` does not read `internal_stations`. 14 bands at use above 1.0. 5 early core taps 150-202 um from their own core box (t69, t17, t59, t51, t75; the rebind skips them because the nearest pin is their own).

Hidden omissions (MEASURED):
- `phy__t1`: `clock` holds only `tap_um` and `layer`. The 32-tap row (`s81-phyt1/ev/phyt1_row.json`, 19,922 sinks) is not in `s81_phyt1_d44_or13.json`, which has no phy type.
- R2 strap depth: no R2 row file in `rows/`; the chain ran on `die-clk-s81-b6/s81/B6gsh/ca_swm` (file time 07:37). Cost is build count only (col layout hashes stay at 29).
- t14: the E2 row is the p1 form that S81-LEAF-T14 measured at 12,804 -> 13,747. Form R of FABLE-PD-T14-0935 is not in.
- Source base: the chain copies `run/b/B6gsl/src`, the tree GENBUG-IMPL named as the cause of the GEN_LINT `defparam LOCAL` failures. INFERENCE: the 9 slice_station types and lepe_nh_mus_LP repeat it on B6gE unless kit-rtl runs with `--src-tree` (783923a5c8).

## 2. M8 re-screen (question 2)

`grant_config` on B6gE: enable true, types None, ndr 4w: every type below the M8 ceiling gets the grant (MEASURED). Screen re-run on `ev/B6gE.json`: same 20 types and same numbers as on E2rp, so E2 changed none of them. M8 is horizontal: it feeds x-slots (H over the core, 5.3 -> 14 per um) and does nothing for y-slots (V over the core is M7 only, 10.5 per um).

| type | slot | flops per um | M7-only | with M8 | verdict on B6gE |
|---|---|---|---|---|---|
| t65 | vsw / vs (y) | 21.6 | 206 % | 206 % | fails |
| t56 | vs / ve_m (y) | 21.2 | 202 % | 202 % | fails |
| t34 | ve_s / vsw (y) | 20.6 | 196 % | 196 % | fails |
| t32 | vn_a / vn_b (y) | 20.1 | 191 % | 191 % | fails |
| t61 | vsw / ve_s (y) | 15.5 | 148 % | 148 % | fails |
| t23, t62, t67 | ve_s / vsw or vs (y) | 13.9 | 132 % | 132 % | fail |
| t1 | ln7 / ln3 (y) | 11.5 | 110 % | 110 % | fails |
| t58 | ve_m / vsw (y) | 10.2 | 97 % | 97 % | fails with repeaters |
| t68, t24 cl2456157b | ve_s / vsw, ve_s / vq (y) | 10.0 | 95 % | 95 % | fail with repeaters |
| t38 | vs / ve_m, vsw / vs (y) | 9.2, 8.8 | 88 %, 84 % | same | at risk |
| t58 | ve_m / ve_s (x) | 7.6 | 142 % | 54 % | M8 helps; above t14 |
| t65 | ve_m / ve_s (x) | 6.3 | 119 % | 45 % | M8 helps |
| t14 | ve_s / ve_m (x) | 4.7 | 89 % | 34 % | r2 left 139 at this level; needs form R |

Calibration is t14 only: baseline 34 % became 83 % with repeaters and left 139 overflow. So a y-slot at 84 % or more is a fail, and t58 (54 % on its x-slot) is above the one measured case. Result: 9 types fail outright, 4 more with repeaters, 0 of the 13 are cleared by M8. What M8 does clear is the general over-core H starvation of the 56 M7-only kits.
Fix: station rows that spread each cross-slot band to at most 6 flops per um along the slot, or put the stage at the core corner (T14-0935 section 6 rule). Second lever, not same-day: the M9 leftover grant (`type_m9_grant`, in the tools). MEASURED on t65: M8 grant 14,444 of 16,956 tracks (85 %); M9 15,364 of 18,036 before the die clock route is subtracted, about 10.6 per um, which would double V over the cores (t61 148 -> 74 %, t23 / t62 / t67 66 %, t65 still 103 %). The kit refuses it without die clock route guides (`type_m9_grant.guide`), so it needs the B6gsh die clock guides exported first (DIE-S81-92).

## 3. Families that still fail on B6gE as built (question 3)

| family | types | mechanism | evidence |
|---|---|---|---|
| col (12 families) | 216 | async clear of seam and relay stations: one `rq` flop on one tap drives the whole partition through 28 buffer stages (about 1.3 ns); capture flops sit on taps 280 ps apart | REPORTED TL-COLH9R0P6 10:25 and S81-SEAM-RST 10:48 on fd `4_cts.odb`: recovery 4,369 of 8,380 pins fail, worst -745; removal 286 fail, worst -264. Not in B6gE |
| bk_sel__t2 | 1 | idx_tx_n32 parameter mismatch (row f); tap 790.1 has no signed bksel_q view yet | REPORTED DIE-S81-92 10:5x (1 mismatch of 5,848 rows), S81-TAPROWS audit |
| svc rs | 8 (+ svc_lo t6) | rows a, b, c: far sinks, bands at the reach limit in 2.16-um pieces; the tap in an 11-um channel leaves a 2.4-um legal strip, not yet checked against PG and track snap | MEASURED section 1; the t6 / t3 GPL + CTS pilot has not run |
| slice_station | 4 | row e | MEASURED |
| slice_station, lepe_nh_mus_LP | 10 | GEN_LINT `defparam LOCAL` from the stale source base | REPORTED GENBUG-IMPL; INFERENCE for B6gE |
| phy__t1 | 1 | one tap for 19,922 sinks: the row is missing | MEASURED |
| leaf y-slot | 9 + 4 | section 2 | MEASURED screen, t14 calibration |
| leaf t14 | 1 | ft5 S2 band in the mouth of the 34.56-um gap: 61 % with M8 plus the band itself | REPORTED T14-0935; INFERENCE with M8 |
| lepw_mus_LP t2, lepe_mu_LP t2 | 2 | DRT-0073 no access point on `u_u_ln0/ck[0]` (lane core clock pin) | REPORTED autopilot 09:56, 10:14; no row in B6gE touches it |
| all types under die clock cells | not counted | clock site rows not in: a type signed now is re-keyed by the site delta | REPORTED closure strategy lever 1; the S81 window list does not exist yet |

## 4. Ranked fix list and next deltas (question 4)

Six serial deltas at about 2 h each would re-key families several times. The open items fall into two sets of types that do not overlap, so two events, composed in parallel on B6gE_pre:

**Event F (col + bk_sel, 217 types).** Rank 1 by types.
1. `reset_replicate` rows on the 216 col types (S81-SEAM-RST-1115; pilot with TL-COLH9R0P6). Gate before the rows count: pilots pa / pb at CTS with recovery and removal >= 0 on one h9 and one h10 type. Derive on the tr4 taps (14 per type).
2. Superset `--collector-only --keep-tree --keep-taps` and the R2 depth on `ca_swm` (S81-TYPEMERGE-IMPL): col hashes 29 -> 19. Same event, so the col types regenerate once.
3. idx overlay with the full signed parameter set (S81-TAPROWS). TRIDX is BIND 0, LATCHECK 873 / 873; the event bind must show HARD_CORE_PARAM_ALL 0, so the bind tree needs 079bce7fcd.

**Event G (svc, slice_station, phy, leaf; about 30 types changed).**
4. Taps last (S81-PHYT1): re-derive the density taps for the 8 svc types, svc_lo t6 and the 4 grown slice_station types with the E2 stations and the B6gE band rects as sinks. Add-only: keep every existing tap name and site (the forwarded clock sources and the bands depend on them); new sites only outside band rects. Then one more compose and a check that the bands are unchanged. Pass: 0 sinks beyond the tap radius, max load 1,500. Add the `phy__t1` row.
5. Band obstacles (S81-CA-BAND): `tap_reserved_um` in `_storage_band`; die clock sites as obstacles in padded mode (today only in ring_ff mode). For the 8 svc_hi bands at 7 or more rects (t6 `attnh_i0` 16, t3 `attnh_i0` 10, t6 `attn_i0` 9, t5 `attn_i2` 9, t4 `attn_i2` 8, t3 `attn_i1` / `attn_i2` 7, t2 `attnh_i0` 7): if the t6 / t3 pilot fails GPL, take a priced landing relay stage (+1 cycle, pre-approved) so the ring sits in open rows. Run the pilot on the event-G kit, not on B6gE.
6. Leaf rows (S81-LEAF-PLAN): t14 form R (`ft_slots[ft5].regs_um[2]` = (470, 372), band x 450-490, y 300-388); band spread to at most 6 flops per um on t65, t56, t34, t32, t61, t23, t62, t67, t1, then t58, t68, t24 cl2456157b, t38; STRIP rows. Proof: one place + GRT per changed type, 0 overflow in pass 1.
7. Clock site rows (CLKSITE-RESERVE-1115) if the S81 window list exists before the compose; otherwise the next event. DIE-S81-92 composes both events.

Lower: `internal_stations` as band obstacles (S81-CA-BAND, next compose); the 5 far core taps (DIE-S81-92, check against the kit macro positions); the lane-core `ck[0]` access on the two LP t2 types (new lane, or S81-LEAF-PLAN).

Release on B6gE at adoption: every type not in section 3, about 140, including the M7-only regenerations outside these families.

## 5. Stop list

1. No col wave on B6gE (216 types, 29 builds): the reset fails by structure. Pilots pa / pb only.
2. No svc wave and no t6 / t3 pilot on the B6gE taps; no builds of slice_station t49, t50 cl39451317, t24 cl64811a5d, t24 cl66b71008 on B6gE.
3. No bk_sel__t2 release before the idx overlay; no `OT_HCPARAM_ALL=0`.
4. No unchanged builds of the 9 y-slot leaf types; no t14 p1, A or B kits; no second GRT pass on any of them.
5. No tap rows derived before the stations and bands they must serve; no rows on a composed plan; no tap re-derive that renames or moves an existing tap.
6. No six serial binds: two events, F and G.
7. Do not remove `OT_TAP_MAX_SINKS` for `phy__t1` with the 44: its row is not in.
8. No M9 grant without die clock guides; no M9 work before the band-spread rows are tried.

## Not verified

- G0, bind, LATCHECK and bind_reset of B6gE (running).
- Tap distances are Manhattan to the nearest tap; the log radius uses the tool's assignment and is larger (598 against my 392 on t24).
- The y-slot verdicts rest on one calibration (t14) and plan geometry; no placed database per type.
- That the kit turns `tap_reserved_um` into a placement blockage; the 4.32 clear against PG.
- The GEN_LINT repeat on B6gE; the M8 / M9 track supply beyond t65; the M9 number ignores the die clock route.
- Whether E2 meant the 4 slice_station outlines to keep their old taps.
