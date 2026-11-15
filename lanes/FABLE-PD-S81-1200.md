# FABLE-PD-S81-1200: S81 Event F part 1 (B6gF1) + Event G rows, and the svc_rs synthesis stall (2026-11-15 12:5x PST)

Read-only review. Nothing launched, stopped or changed. MEASURED = plans, rows, logs, RTLIL and kit files read today
(epyc7 `s81-b3-clk`, wave tree `s81/7073a6b4a59` on intel1 / epyc2 / epyc7 / epyc8 / epyc9 / epyc10); scripts epyc7
`/tmp/fable1200_a1.py` .. `a3.py`. INFERENCE is marked. No STA, no route, no database read, no synthesis run.

## 0. Answers

A. Event F part 1 and Event G
1. B6gF1 is consistent with B6gE at row level and costs 0 cycles, but its G0 has **3 new errors** (71 against 68), all
   from the superset: `cland_mon_{clk,ready,fault}__fE4_p1_b0` endpoint hop 1,042-1,050 um against the 405 limit. One
   col r0_p1 instance got the canonical monitor pin position of its cohort on the wrong side. This fails the "new 0" gate.
2. B6gF1 does **not** contain the seam reset rows, the cols tap rows or the idx overlay. `B6gF1_pre` differs from
   `B6gE_pre` only in 25 `reset.keep_outs` die rows. So col stays held after F1 for the reset alone.
3. Event G rows are clean as rows (0 existing taps moved, renamed or dropped; 0 type overlap with Event F), but they
   **do conflict with the form J bands**: 120 of the 457 new taps sit inside a B6gE band rect and 322 have their 4.32-um
   clear box touching one. On the 8 svc types with `tap_reserved_um` this is a real conflict (63 taps inside band rects);
   once S81-BANDTAP-1115 makes `_storage_band` read the reserved sites, the re-compose moves those bands and the taps
   no longer match. On the other 89 types a tap inside a band is harmless.
4. Col abstract (FABLE-CLOSURE lever 2): yes, col stays held for route after Event F. Nothing in F1 touches the
   `ot_v41_bf_col3_c` view, so every col route still ends at 276 markers (552 on h10_r1). Run col only to CTS / GRT.

B. svc_rs synthesis stall
5. Same cause as FABLE-HARD-S81 section 4 (11-14 19:04), still live because the wave tree is the old plan. The kits are
   generated from tree `7073a6b4a59` (B3t), whose RTL has no `OT_SVC_ATT_MEM_MACRO`. The pass is `OPT_MEM_PRIORITY`
   (3.16.2), the module is the native `pbuf` wrapper `ot_bind_native_dc625d1efb80bd607f482ca9`: one 256 x 40 memory
   with **4,096 write ports** (8,386,560 priority pairs). The fix is already in the B6 plans and is not a new RTL change.
6. No svc kit of that tree has ever finished `1_2_yosys` (0 of 33 logs on six hosts). Retrying on that tree cannot work.

## 1. Measured

### 1.1 Event F part 1 (B6gF1, plan 61228a4b65cc, sidecar 2d8303e39ee3)

| item | B6gE | B6gF1 | source |
|---|---|---|---|
| pre-compose type rows changed | - | 0 of 395 | `a1.py` |
| `reset.keep_outs` types | 82 | 85; 25 changed (col_h9_r2 16, col_h9_r1 9) | `a1.py` |
| composed types changed | - | 90, all col (h9_r0 48, h10_r0 11, h9_r2 16, h9_r1 9, h10_r2 4, h10_r1 2) | `a1.py` |
| changed keys | - | `clock.landing_contract` 90, `clock.edge_clocks` 71, `count_straps` 29 | `a1.py` |
| latency lanes changed | - | 0 of 873 | `a1.py` |
| cycles sum / clock_landing sum | 13,671 / 2,522 | 13,671 / 2,522 | log + `a1.py` |
| compose | 0 failures | 0 placement failures, landing contract 0 errors, start tree 233 / 0 open, boot 761 | `log/B6gF1.log` |
| col identities (superset report) | 77 | 22 (21 without hard-core flips); `col_h9_r0_p6` skipped, "none landed" | superset.log |
| G0 errors | 68 | 71 (3 new, 0 gone) | `g0_report.json` |

- R2 depth is in: `strap_ca_k_*` width 6 -> 7 on exactly 29 r0 types (h9_r0 21, h10_r0 8). This widens a strap port
  that the parent ties, so the strict bind and `bind_count_strap_audit` must show the 7-bit tie on all 29.
- The superset adds landing bands: 145 band ports changed, most of them new `monitor_N` bands (320 padded flops each,
  band use 0.49) on r1 / r2 / r0 types. No changed band is above use 1.0 (0 of 145). Their rects are marked
  "PROPOSED legal macro-free band; mapped anchoring pending".
- The 3 new G0 errors (`clock_landings`): `cland_mon_clk__fE4_p1_b0` 1,049.9 um, `cland_mon_ready__fE4_p1_b0` 1,045.5,
  `cland_mon_fault__fE4_p1_b0` 1,041.2. The superset log lists one outlier in that family:
  `col_h10_r0_p1__t1__cl911743eb` (main 5 of 6). INFERENCE: `fE4_p1` is that type or its seam partner.
- Bind and LATCHECK of B6gF1 had not ended when I read (`run/b/B6gF1` holds elab.log and out/, no bind.log).

### 1.2 Event G rows (`rows/s81_phyt1_eventG.json` 62 types, `_minor.json` 36 types)

| check | result |
|---|---|
| types in both files | 0 |
| types shared with Event F (90 changed types, seamrst 216, cols tap rows 217, tridx 1) | 0 |
| existing taps missing / moved / changed | 0 / 0 / 0 |
| taps added | `clock.taps` 387 + 55, `clock.added_taps` 45 + 13 (500 against the 457 posted) |
| existing list entries whose index shifts (new taps go in before the core taps) | 1,186 + 139 |
| pre-compose keys that name a `clk_tN` outside the tap lists | 0 types |
| new tap inside a hard core box | 0 (hard cores carry no box key I could read; see section 4) |
| new tap point inside a B6gE band rect | 120 taps: svc_hi rs 37, c1x_C 30, svc_lo rs 17, slice_station 6, svc_lo rs_w 5, pvso_entry 4, iqf 4, others 17 |
| new tap 4.32 box touching a band rect | 322 taps on 67 types; 7 hits on rects 2.16-4.32 um wide (svc_hi t6 `attnh_i0` 3, t2 `attnh_i0` 2, t5 `monitor_0`, pvso_entry t2 `rsv_i0`) |
| `tap_reserved_um` rects added | 113, on the 8 svc types only |
| new tap closer than 8.64 um to a core tap | 4: svc_lo rs t1 `clk_t52`, svc_hi rs t4 `clk_t41` and `clk_t43`, svc_hi rs t6 `clk_t89` (0.6-6.5 um in x, 4.6-6.2 in y) |

- The composed landing contract names taps by list index (`relays[].tap`, `collector_local_sources[].tap`). A new
  compose regenerates them. Any step that keeps a tree or a sidecar from B6gE (`--keep-tree`, a reused sidecar) on a
  G type would point at the wrong tap. INFERENCE; the F-side superset does not touch G types.
- The count posted (457) and my count (500) differ by 43. I count names new against `B6gE_pre`; the post counts
  against `B6gErr_pre` or excludes the phy__t1 row (32). Not resolved.

### 1.3 svc_rs synthesis (wave tree `s81/7073a6b4a59`)

- `svc_hi_dsdv_svc_rs__t3` attempt_10 (epyc2 run dir, intel1 kit copy): start 03:03, canonicalize done 03:49 (46 min),
  `1_2_yosys.log` last written 04:50 at `3.16.2 OPT_MEM_PRIORITY`, cancelled 11:45: 6.9 h in one pass, 300 log lines.
  `__t4` attempt_9 is identical (04:55).
- `1_1_yosys_canonicalize.rtlil` (40.6 MB, 459 modules, 19 memories, 5,562 `$memwr_v2`, 30 `$memrd`):

| module | instance | memory | `$memwr_v2` cells | priority pairs |
|---|---|---|---|---|
| `ot_bind_native_dc625d1efb80bd607f482ca9` | `g_u_rsv_07_u_pbuf` | 256 x 40 | 4,096 | 8,386,560 |
| `ot_bind_native_ca056ec368b56f7d8e12952d` | `u_att_qmem` | 512 x 16 | 512 | 130,816 |
| `ot_bind_native_bfac540d36e9ad5c410d0d97` | `u_att_sw` | 512 x 32 | 512 | 130,816 |
| `ot_bind_native_0345256bc94e41a6442d128f` | `u_att_fq` | 416 x 2 | 416 | 86,320 |

- The pbuf wrapper source (8,212 lines) is one always block with 4,096 statements
  `if (WR_EN[i]) mem[WR_ADDR[5:0]][b] <= WR_DATA[i]`: 16 write ports x 256 bits, all on one address and one clock, each
  with `PRIORITY_MASK` over every earlier port. INFERENCE: `opt_mem_priority` runs a SAT query per pair that can hit the
  same bit (256 bits x 120 port pairs = 30,720 solves on the flattened cone, after scanning all 8.4 M pairs).
- Kit `config.mk`: `VERILOG_DEFINES = -DSYNTHESIS -DOT_SVC_ALLQ -DSU_SMU_T -DOT_ATTN_HCORE -DOT_S81C_HCORE_CTLA
  -DOT_S81C_HCORE_RST_TIMED`: no `OT_SVC_ATT_MEM_MACRO`. `SYNTH_ARGS = -noshare` is set on hi t3 / t4 / t1.
- Second stall in the same tree, kits without `-noshare`: `3.15 SHARE` is the last line on svc_lo rs t3 a7, t4 a8
  (intel1, since 04:40 / 04:33), t7 a10 (epyc7), t6 a6 (epyc8), and earlier svc_lo t6 a4 (ended after 5 h 32 min in
  SHARE) and t5 a6 (6 h 19 min in SHARE).
- All 33 svc `1_2_yosys.log` files on the six hosts end in OPT (3.8), SHARE (3.15) or OPT_MEM_PRIORITY (3.16.2). None
  reaches ABC. The 26-36 min "elapsed" logs of 11-14 12:4x and 11-15 09:0x end inside OPT 3.8: stopped, not passed.
- Same pass, same tree, last log write today: pvso_entry t1 a15 (epyc7, 11:47), pvso_entry t2 a16 (epyc8, 09:30),
  svc_hi rs t1 a11 (epyc8, 09:13), t2 a6 (epyc8, 09:28), t5 a7 (epyc10, 11:39). I did not check whether they still run.
- The plan of record has the fix: `ev/B6gE.json` and `ev/B6gF1.json` carry `verilog_defines: [OT_SVC_ATT_MEM_MACRO]`
  on the svc types, and the B6gE bound file `run/b/B6gE/out/rtl/s81p_svc_hi_dsdv_svc_rs__t3.sv` has 9
  `dsdv_svc_mem_*` instances (8 `_ar`, 1 `_la`) and 0 native pbuf.

## 2. Fixes and levers

| # | fix | number / pass criterion | owner |
|---|---|---|---|
| 1 | Superset: keep the type's own monitor pin position when the canonical one gives a seam hop over 405 um (the `fE4_p1` type leaves the cohort; identities 22 -> 23). Re-run superset + G0 only; compose is unchanged | G0 71 -> 68, new 0 | S81-TYPEMERGE-IMPL, DIE-S81-92 |
| 2 | Event F part 2 carries what F1 lacks: seam reset rows (form pg / ph, after the CTS gate), `s81_taprows_cols_eventF.json`, tridx, and the new col3_c view. One more col event, not two | recovery and removal >= 0 at CTS on one h9 and one h10 type; HARD_CORE_PARAM_ALL 0 | DIE-S81-92, S81-SEAM-RST-1115, S81-COLABS-1115 |
| 3 | After F: build the 22 col identities to CTS / GRT only; route waits for the col3_c view. The view changes pin shapes only, so placement and GRT results stay useful | 0 `Lef58EolKeepOut` at about iteration 15 on one r2 kit with the new LEF | KIT-OPS-5, S81-COLABS-1115 |
| 4 | Event G, svc types (16): legalise the new taps with the B6gE band rects (+4.32) as obstacles, so no reserved site lands in a band; the tap serves the band by radius, it does not need to be inside. Then freeze those band rects for the G compose (rows or band-fixed option) so compose cannot move them | svc taps inside band rects 63 -> 0; bands identical before and after compose; 0 sinks beyond 100 um | S81-PHYT1 (taps), S81-BANDTAP-1115 (band read + fixed bands) |
| 5 | Event G, the 4 taps within 8.64 um of a core tap: move or drop them (the core tap already serves that spot) | 0 reserved boxes overlapping | S81-PHYT1 |
| 6 | Event G compose: fresh compose, no `--keep-tree` and no sidecar reuse on G types; add a check that every `relays[].tap` index resolves to the same xy as before for unchanged relays | 0 mismatches | DIE-S81-92 |
| 7 | svc synthesis: stop launching svc types from tree `7073a6b4a59`. svc kits come only from a B6 plan (define set). Keep `-noshare` on all 16 svc types, hi and lo | kit `VERILOG_DEFINES` holds `OT_SVC_ATT_MEM_MACRO`; bound file has `dsdv_svc_mem_*`, no native pbuf | KIT-OPS-5 |
| 8 | Synthesis-only pilot now, independent of the Event G taps: svc_hi rs t3 and svc_lo rs t6 kits from B6gE, stop after `1_2_yosys`. Taps do not enter synthesis, so this does not wait for G | past 3.16 MEMORY in under 15 min; whole `1_2_yosys` under 2 h; record cell count | NEW LANE S81-SVC-SYNTH (Sonnet) |
| 9 | If the pilot still stalls in 3.16.2 on the remaining native memories (fq 416 writes; sw / qmem 512 if they stay native): generator change in `tools/die_plan/bind_native_glue.py`: when all write ports of a `$mem_v2` share clock and address, emit one port per source port with a word mask, not one statement per bit (pbuf 4,096 -> 16 ports, 120 pairs) | `$memwr_v2` per memory <= ports; LEC of the wrapper against the per-bit form | GENBUG-IMPL |
| 10 | NOPROG-WATCHDOG: treat "last line = SHARE or OPT_MEM_PRIORITY for 60 min" on a kit with a memory of more than 256 write statements as a design failure at once, not after 6.5 h | cancel at 1 h, class `SYNTH-MEMWR` | WAVE-PREPNR-1115 |

## 3. Stop list

1. No relaunch of any svc type (rs, rs_w, pvso_entry) from wave tree `7073a6b4a59`: 33 of 33 synthesis logs never
   finish. Stop the ones still in SHARE / OPT_MEM_PRIORITY (list in 1.3) after a liveness check.
2. No mem2reg form and no single wide masked write port for pbuf (both measured dead or not equivalent on 11-14).
3. No svc kit without `-noshare`.
4. No adoption of B6gF1 with G0 at 71; no col wave on B6gF1 (reset rows not in; col3_c view not in).
5. No extra route iterations on col types and no col route before the new view.
6. No Event G compose with svc taps inside band rects; no second tap pass after the compose that "only adds".
7. No `--keep-tree` or old sidecar on Event G types.
8. No further S81 event that carries only one of the open col items; F part 2 takes all four.

## 4. Not checked

- B6gF1 bind, LATCHECK and bind_reset (running); the 7-bit strap tie at the parents.
- Which type owns `fE4_p1_b0`; the superset code path that set its pin.
- The new `monitor_N` band rects against taps, internal stations and cores (plan marks them PROPOSED).
- Event G taps against hard core boxes (no box key read), PG and track snap; the 457 against 500 count.
- Whether a tap inside a band is blocked area in the kits of non-svc types (I assumed it is an ordinary tap cell).
- yosys `opt_mem_priority` source and a profile of the stalled process; the pair and solve counts are arithmetic.
- That a B6 svc kit passes synthesis: no such kit exists yet (svc types are held). Lever 8 is that proof.
- Liveness of the 9 other svc kits; why SHARE stalls (only that `-noshare` skips it).
