# FABLE-PD-KV-0945: kvgeom7t / 7u content, pv_v1n reset tap, kv3_hroot size, die clock sites (2026-11-15 10:15 PST)

Read-only review. Technical PD only. MEASURED = read or computed by me today from a plan, log or kit. REPORTED = from a
lane post. INFERENCE = my reasoning. I ran no build, no STA and no bind; only plan reads and `reset_tree.blockages()` on
plan copies (epyc7). Nothing launched, stopped or changed.

State at 18:11 UTC (epyc7 `kv-102/kvgeom7/`, MEASURED):

| variant | plan sha | G0 | bind | LATCHECK | note |
|---|---|---|---|---|---|
| 7j (adopted) | 6928f8db88c2 | PASS | 0 errors (pinned) | 2404/2404 | plan of record |
| 7q hub_C taps/views | eec05af44e52 | PASS 0 err | phase 1 R8_STALE (expected), pinned rebind running since 17:31 | phase 1 2404/2404 | no result yet |
| 7r pv_v1n stations | tree 01a0bbba5d84 | FAIL 1 error | ResetError | none | file on disk is a NEWER plan 2917c8322ddf, not gated |
| 7s raw-branch rows | f46698d6625c | PASS 0 err | running | none | |
| 7t hg/hgi bands | 3cfe2373007b | PASS 0 err | running since 17:34 | none | |
| 7tb all-type bands | c6b392413fbd | PASS 0 err (2363 warn) | not started | none | |

No variant of the 7u set has a bind or LATCHECK result yet. Every statement below is conditional on them.

## 1. Is the 7u content enough? Per family

| family | types | what 7u carries | enough to close? | what is missing |
|---|---|---|---|---|
| hg / hgi | 19 | 7j stations on kv3_hg only (40 stations, 13 buses), 7t bands, 7s raw rows | NO for timing; YES for the band place failure | (a) krsp +5 / rq +3 with the ectlk cores at 37/26 is not in 7u; (b) the 7 other hg frames and the hgi frames have no family listing yet, hgi_v2__cl2862d491 stopped today at GRT with hold ws -196 ps, 1780 endpoints (MEASURED, wave log 09:32); (c) `kvgeom7h_raw.log`: "raw kv3_hgi: no corridor with hops <= 405" on origin + fstart ft0_o/ft2_o/ft5_o (MEASURED) |
| pv | 16 | 7r: 91 station rows on kv3_pv_v1n only (vport 60, response 16, ctl_cmd 15; +6/+7 cycles; hops <= 376.7 um on legs up to 3013 um), 15 more local reset taps; 7tb bands | NO | (a) 7r does not bind; (b) the other 15 pv types have 6 local reset taps and 2-23 internal stations, unchanged (MEASURED); (c) KV-PVGEN stages (pair->join D3, join->relay D3, selrep32) are on a branch against kvgeom6, item 4 (out_v_lo -> pair) is open, and the PV ctl TRUNK_D/FLAG_D regen has not been run with the +3/+3 legs (REPORTED 18:0x); (d) 143 pv ring bands cannot be widened to 17.28 um (pv_v7 48, v12 47, v3/v3n 30, v6/v6n 14, v2/v2n 4, REPORTED) and pv_v2, v4, v6 failed place on exactly this class at 09:52-10:05 (MEASURED, wave log) |
| hub_C | 1 | 7q: one value 228.67/179.9 on ahub ck[0..6], signed views attached | YES for the kit inputs, if the pinned rebind passes | confirm kvs_ctl.ck = 283.5/233.96 is in 7q (0800 gap 1; I did not re-read the row) |
| hub_Wo | 1 | 7tb band floor on the literal-local-reset band | LIKELY for the place failure | occupant of the band was never named; the new BAND FAIL text names it on the first 7u kit |
| io (io_cor, io_cor_v1, io_ft, io_ft_v1) | 4 | 7tb bands; cursor fix is live | place: yes. Route: not shown | io_cor a3 ended in DRT-0255 "maze route cannot find path" on a cland ring net at (533.5,50.7) (MEASURED, 05:42). One pin-access failure, no owner, not a plan item |
| hroot | 1 | proposed 7h: outline 1900.8 -> 1036.8 and start origin move | origin move: yes. Outline shrink: not in 7u (section 3) | |

Verdict: 7u = 7q + 7s + 7t/7tb is a correct and sufficient delta for the place-stage classes (bands, hub_C views, raw
branches). It does not close hg/hgi or pv setup. Do not wait for 7r: post 7u without it, and let pv follow as its own delta.

## 2. The blocked pv_v1n reset tap

MEASURED (`reset_tree.consumer_taps` + `blockages` on the plan, obstacle_model lef_origin, CLEAR 4.32 um):
- The blocker is not a hard core and not a contents leaf (0 contents carry a LEF origin). It is a `clock.keepouts_um`
  box, grown by 8.64 um to (1026.0, 8.64)-(1116.18, 143.376). The tap [1080.0, 138.24] is 5.1 um inside its top edge.
  The same point is blocked on 7j: the keep-out predates 7r.
- The file `kvgeom7r.json` on disk (17:02 UTC, sha 2917c8322ddf) already has the tap at [1080.0, 146.88], the next 8.64
  lattice row above the box. All 21 local taps pass `_free` under both obstacle models (lef_origin and the canonical
  `placement_boxes`). `kvgeom7r.py` l.70-72 now picks the nearest free lattice site within 200 um with the same `_free`.
- The gate tree `kw45/kv102t18_kvgeom7r` still holds 01a0bbba5d84 (the third try). The 17:01 pingate re-read that tree.
  At 17:47 and 18:11 UTC no 7r gate process was running. So the "4th try" was never gated; the reported error is stale.

Right fix:
1. Keep the generator form (nearest free lattice site, same `_free` and boxes as the bind). It is correct; an 8.64 um
   shift of a relay site has no timing meaning. Do not shrink the keep-out, do not waive the check, do not hand-edit.
2. Copy 2917c8322ddf into the tree and rerun G0 + bind + pinned rebind + LATCHECK. That is the only step missing.
3. Coverage, not legality, is the open point: 75 of the 670 station registers of 7r are more than 405 um (max 607.6 um)
   from the nearest LOCAL reset tap. The 20 clock taps also carry reset; I could not evaluate the combined set (not
   verified). KV-PVGEN: check the reset-to-register distance on the first placed 7r kit before adding more taps.
4. Apply the same tap grid to the other 15 pv types only after pv_v1n shows recovery >= 0 at CTS.

## 3. kv3_hroot

MEASURED (7j plan type block; kit kvgeom6 a13 on epyc8, `geom/auto_geom.json`, stage placed):
- 107,048 cells, 24,780 flops, fill 0.0105, GRT 0 overflow in 10 iterations.
- Local x < 864 um holds: 0 of 59 ft station registers, 0 of 4,293 relay sites, 0 of 23 edge clocks, 2 of 11 internal
  station registers; plus 140 count-strap sites (x 21.6-324, y 4.32), 6 of 12 reset local taps, and the landing start
  origin (rect 181.9-199.2, 6.5-19.4). So 45 % of the outline is unused.
- The 2509 um is not a data hop and not the start chain (its stages are registered, 87-233 um apart). It is a clock leg:
  metric `clock_leaf_reach` = root port `clk` at (190.56, 21.6) to sink `u_cland_fstart_ft13_o/q` at (1894.9, 826.3).
  14 sinks stay on the root port `clk` (`tap_sinks.clk` = 14); the tap pass never empties the root port
  (`clock_taps.tcl` l.397). 40 grid taps carry 2 to 1,811 sinks (clk_t11 1,811, clk_t2 1,434, clk_t35 1,406), limit 1,500.
- col_v 1.546 at (910, 172.5) is a pre-route estimate; GRT overflow is 0 with M2 at 5.75 % use. Advisory only.
- r2r 943 um, 972 captures over 405 um, worst `u_cland_i_fch_pc_Q_N_q/u_ring...dsel` -> `u_bin_i_fch_pc_Q_N_q/eq`:
  ring read to bin register, a real single-cycle class on this type (not measured in ps).
- Last real stop (03:32): GRT hold repair over 3 h, ws -19.7 ps, 580 endpoints.
- Die: 4 instances (WS R0, WN MX, ES MY, EN R180). South neighbours of hroot_WS: phy_WS_7 (kv3_phy_v1, x 0-864) and
  pc_WS_7 (x 864-1900.8). The internal station `o_host_hbm_rst_n` leaves the S face at x 431.96, into phy_WS_7.

Answer: the outline is over-sized by 864 um, but the size is not what fails. Rank:
1. In 7u, rows only: move the root clock port `clk` and the landing start origin from x 190 to the band centroid
   (about x 1380, y 420), and re-derive the taps so no tap exceeds 1,500 sinks (split clk_t11, t2, t35). This removes
   the 2.5 mm leg and the 2,438 um entry-to-sink span. No die change. Relaunch hroot on it.
2. The shrink to 1036.8 x 838.08 is a die topology change, not a type row: it breaks the abutment with kv3_phy_v1
   (REPORTED signed and archived) for `o_host_hbm_rst_n`, moves the die clock tap (950.4, 414.72), the 140 strap sites
   and 6 reset taps, and leaves four 864 x 838 um holes for die PG, clock and reset. Keep it out of 7u. Gate it alone
   as 7h and adopt only if G0, bind and LATCHECK pass with phy_v1 untouched (reset pin on pc or a declared die wire).
   Gain: about 18 taps and half the tap/endcap cells of one type; it unblocks nothing.
3. Family listing on the a13 placed database for the ring-read -> bin class (972 captures) before the next relaunch.

## 4. Die clock-site class (M1-M3 under abstracts): into 7u?

- REPORTED (DIE-ROUTE-ABS-1 handoff): KV has 32,280 of 32,280 die clock cells under a partition; 437 of 32,856 in a
  declared island. That count is on the kvgeom5 die clock kit. No KV window list exists; CLKSITE-RESERVE-1115 has posted
  nothing for KV (MEASURED, queue to line 14115). HEAD NF7 has the rows but no kit that honours them yet.
- Answer: NO, do not hold 7u for it. Reasons: (a) no measured KV site list; (b) 7u, 7r and the hroot change move type
  contents and one die clock tap, so a window list cut from the kvgeom5 tree is stale on arrival; (c) only 5 of 56 KV
  types are signed, so reserving later re-keys few signed types, unlike HEAD; (d) the HEAD proof that a kit honours
  the sites is still open.
- What must happen now, in parallel: CLKSITE-RESERVE-1115 runs the `abstract_cutout.py` dry run on the KV die clock
  kit rebuilt on 7j, posts windows per type (R0 template + MY/MX/R180), and KV-102 takes them as the delta after 7u,
  together with the first HEAD kit that proves the form. The 5 signed KV types get the empty-at-sites check first.

## 5. Ranked fix list

| # | fix | numbers | owner |
|---|---|---|---|
| 1 | Post 7u = 7q + 7s + 7t/7tb as soon as their binds and LATCHECK pass; do not wait for 7r, 7h or clock sites | 31 changed + band types released; 21 held types | KV-102 |
| 2 | Gate the real 7r: plan 2917c8322ddf into the tree, G0 + bind + pinned rebind + LATCHECK | idle since 17:02 UTC; tap 146.88 is free | KV-102 |
| 3 | hroot rows in 7u: root `clk` + start origin to the band centroid, taps <= 1,500 sinks | leg 2509 -> under 600 um; 3 taps over 1,500 | KV-102 |
| 4 | pv delta after 7u: 7r stations + KV-PVGEN stages + ctl TRUNK_D/FLAG_D regen in ONE event; out_v_lo output pipe first; private synth+place+CTS before/after per family | setup -1,573 ps, 17,239 endpoints today | KV-PVGEN (stages, proof), KV-102 (event) |
| 5 | pv ring bands that cannot reach 17.28 um: place the band occupants as stations (PLACED-SCAN table), all 16 pv types | 143 bands; 3 place fails 09:52-10:05 | PLACED-SCAN-1115 (table), KV-102 |
| 6 | krsp +5 / rq +3 event with ectlk q0..q3 at QK 37 / RT 26, on all 8 hg frames, one time | krsp -568 ps; cores rebuilding | KV-ECTLK-RL, KV-102 |
| 7 | Family listing (after CTS) on held placed hg_v1 / v1p3 / v1p4, on hgi_v2__cl2862d491 (hold -196 ps, 1780) and on hroot a13 (972 captures) | no post yet for hg_v1 | TYPES-KV-FAIL, PLACED-SCAN-1115 |
| 8 | raw corridor for kv3_hgi: "no corridor <= 405" on origin + 3 fstart branches | 1 type | KV-102 with the 7s rule owner |
| 9 | KV clock-site windows from a 7j die clock kit; empty-at-sites check on the 5 signed types | 32,280 cells, 437 in islands | CLKSITE-RESERVE-1115 |
| 10 | io_cor DRT-0255 pin access on the cland ring net; read after the first 7u io_cor route | 1 net | TYPES-KV-FAIL |
| 11 | hroot outline 1036.8 as 7h, alone, phy_v1 untouched | 864 um, 4 instances | KV-102, after 1-3 |

## 6. Stop list

1. No 7u hold for 7r, 7h, PVGEN or clock-site rows.
2. No hroot outline change inside 7u; no hroot relaunch on kvgeom6 or plain 7j (the clock leg is in the plan rows).
3. No keep-out shrink, obstacle-model switch or check waiver for the pv reset tap; no hand-placed tap.
4. No pv relaunch on kvgeom6 or 7j (pv_v2/v4/v6 were relaunched 10:05 on a band class that 7u changes), and no copy
   of the pv_v1n tap grid or stations to the other 15 pv types before one pv_v1n CTS result.
5. No clock-site windows cut from the kvgeom5 clock kit.
6. No wider band for the 143 pv bands; no tuning of kvgeom6 bands.
7. Still in force: FABLE-PD-KV-0800 stop list 1-5 and FABLE-CLOSURE 0930 items 7-9, 12.

## 7. Not verified

- Bind, pinned rebind and LATCHECK of 7q, 7s, 7t, 7tb (running or not started); nothing of 7r's newer plan.
- Reset reach on pv_v1n against clock taps + local taps together; any reset or setup slack in ps on 7r.
- Why 14 sinks stay on the hroot root `clk` (I read the rule text, not the trace); the proposed centroid is read from
  the band/relay x range, not from a placed fit.
- kvs_ctl.ck in 7q; the occupant of the hub_Wo band; the io_cor pin-access cause.
- The keep-out's purpose on pv_v1n (I read only its box).
- Side effect: I ran `tools/failure_breakdown.py` at 10:0x; it rewrites the failure section of the release tree as designed.
