# FABLE-PD-S81-2040: S81 physical-design review, open failure families (11-19 20:40-21:30 PST)

Reviewer: FABLE-PD-S81-2040 (Fable). Read-only. Gate used: DRC 0 route, TT setup >= -42 ps, FF hold >= 0, bind + LATCHECK; CBC hop 405 um.
Every number below was read from the named file during this review unless it is marked (lane post).

## 0. What changes the plan for tonight

1. **No col build on the new plans has reached place yet, so there is no GRT or TT number to compare.** At 21:27, 87 of the 114 D8i kits were generated and 65 routes had started, all on epyc8 (load 348 on 96 cores, 1,473 threads) and none past synthesis and floorplan. The cc3 and cc3s binds failed at 20:32; the re-bind is queued on the same host behind 53 waiters. Section 1 gives the cause and the fix for each.
2. **The S81 die hold numbers -438 and -242 are mostly measurement artefacts.** About 377 ps of the -438 comes from 8 outlier flops in one signed type record. About 200 ps of the -242 comes from the die STA pricing every plain tap at 250 ps while 344 of 395 S81 types run at 450 ps. The real problem is smaller and wider: tap-to-tap spread inside a partition, median range 50-74 ps, on regular taps as much as on core taps. **cw7 does not fix it; it makes it worse** (partitions within 40 ps: 28 of 393 on cw6, 8 on cw7), because the per-tap error is build noise that does not repeat. Taps that share a node within 5 stages are within 16 ps at p95: the fix is matched clusters.
3. **A new col class, found statically:** 36 types have a first face-bus hop of 508-512 um for the worst bit although the plan shows 388-392 um. The plan measures from the centre of a 240-um pin window. col_h10_r0_p4 (the known 528 um) is one of four families.
4. **serdes H23 works:** GRT TT -73.5 against -179 (H22) and -192 (H18); rck span 89 ps PASS.
5. **lepe proof5 is stuck in repair** at -270 ps on 715 endpoints for 1,200 iterations. It has given its result: the stuck endpoints are the RX `ri` register that RIP1 pipelines.

## 1. col types

### State of the builds (read 20:40-21:27)

| Build | State | Evidence |
|---|---|---|
| D8i, 114 types (S81-GEOM-OPUS) | Bind green 19:39. Kit gen: 8 of 114 done at 20:57, 87 at 21:27. Routes: 87 launched, 65 admitted, every one on epyc8. No CTS report yet. | intel2 `~/s81-geom-opus-d8ig-*.log`, `~/s81-geom-opus-d8ik-*.log`, `~/s81-geom-opus-d8i-launch2.log` |
| cc3, 192 types (COL-CENSUS-1119) | Bind FAILED 20:32. No kit. Re-bind (build3b) waiting for 128 GB on epyc8 at 21:27. | intel2 `~/col-census-1119-build3.log` line 10, `~/col-census-1119-chain3.log` |
| cc3s, 1 type | Bind FAILED, same error. No kit. | intel2 `~/col-census-1119-build3s.log` line 10 |
| h10_r1 + h10_r2, 24 types (COL-H10-1119) | Still in strict bind (ELAB_RC=0 only). | intel2 `~/col-h10-1119-build.log` |

So the comparison against the old-plan numbers (h9_r1 -181, h10_r1 -208/-411, h10_r2 -172, h10_r0_p1 -481) cannot be made yet. Two of those old numbers are already explained and should not be carried forward as targets: h10_r1 -208 is the pre-tap-balance report (after the hook t19 is 436 ps and t12 is 437 ps), and h10_r2 -172 is the pre-join form (lane posts COL-H10-1119 18:55, S81-GEOM-OPUS 18:45).

### Root causes

**1a. The D8i builds are slow because of how they were launched, not because of the design.**
- All 114 `gen.py phys` jobs were started at once on epyc8, the only host that has tree6. epyc8 load was 330 on 96 cores and each generator got about 14 % of a core. The first kit took 67 minutes. (epyc8 `ps`: 114 x `gen.py phys ... plan_h2_2249.json`, 2,350 s elapsed, 14.3 % CPU each.)
- The route launch uses `ot-run --mem 96 --dir <kit gen dir>` with no `--stage`. The kit dir exists only on epyc8, so every other host is skipped (`~/s81-geom-opus-d8ik-col_h9_r1__t1__clf32cde8d__pv3b9ba75c.log`: "skipped: no ...kb_d8i/kits/.../gen" for 6 hosts). At 21:27 65 routes had been admitted there on measured memory, on top of the running work: load 348 on 96 cores, 152 jobs, 1,473 threads. Each route asks for 16 threads, so each gets a small fraction of a core, and when 65 to 114 routes reach global and detailed route together their memory will exceed the host. Every log carries `SPILL not possible: cannot scan [...s81-geom-opus-d8g] on epyc8`.
- A kit is 36 MB, but the spill works on the whole lane root and refuses it. The launch post said "no --hosts, spill allowed"; in effect the 114 routes are pinned to one full host. The COL-CENSUS re-bind and the COL-H10 bind sit on the same host for the same reason (their trees are hard-link copies that exist only there): the census re-bind is waiting behind 53 waiters / 3,128 GB (`~/col-census-1119-build3b.log`).
- COL-CENSUS already launches with `--stage $K`, which is the working form.

**1b. cc3 and cc3s binds failed on one row.** `ValueError: col_h9_r0_p4__t1__cl8ef405e8__pv70731479: added tap clk_t41 violates outline/halo/tap spacing`. A CC-BANK-2 bank move put a qbank_S core inside the clearance of an added clock tap. `cc_bank3_rows.py` checks that no tap lies inside the bank box, but not the tap-to-core clearance the bind enforces. Three whole-plan binds were started and replaced between 18:55 and 19:26 (cc1, cc2w, cc3), and the third failed at 20:32. Result: 0 col kits from this lane in 2.5 hours.

**1c. New class, WINDOW-HOP: the first hop of a wide face bus is measured from the window centre.**
Static check on `plan_h3_d8i.json` f2ec5ffc3bda (epyc8 `/srv/opentallas-scratch2/claude/s81-geom-opus-d8g/d8i/`): for every `internal_stations` row launched by a face bus, I took the pin window extent instead of its centre.

| Family | Bus | Plan hop (centre) | Worst-bit hop | Types |
|---|---|---|---|---|
| col_h10_r0_p4 | x_i0 | 392 um | 512 um | 6 |
| col_h9_r0_p4 | x_i0 | 388 um | 508 um | 6 |
| col_h9_r0_p5 | xo_i0 | 388 um | 508 um | 12 |
| col_h9_r0_p6 | xo_i0 | 388 um | 508 um | 12 |

Example, col_h10_r0_p4: x_i0 is 1,104 bits on the E face over y 980.7-1220.7. Its one station is at (1438.56, 712.8) and the sink u_cf.xl* is at y 518.4. From the window centre the hop is 392 um. From the top bit it is 512 um, plus the spread of the bank itself. That is the 528-531 um COL-CENSUS measured on placed cells. The other three families have the same geometry and no row. 144 station rows in 36 types exceed 405 um by this measure; 0 exceed it by the plan's measure.

**1d. Half-cycle bank hops (BANK-OUT, BANK-IN) and the read loop** are as COL-CENSUS describes (lanes/COL-CENSUS-1119.md). I have no new measurement because no kit exists. The old-plan evidence stands: p6 e0_u_w -> bn0 -30..-45 at GRT, h10_r2 e13_u_w -> bn13 -96 at GRT, h9_r0_p2 bs1 -78.7 at CTS, h9_r2 c12_6 -> s12 -44.75 routed on one end, with two col_h9_r2 variants signed at -39.22.

### Ranked fixes

1. **Get the 114 D8i routes onto the fleet (S81-GEOM-OPUS; COORD to decide on the ones already running).** Launch the 27 kits not yet generated, and any route not yet started, with `--stage <kit dir>` as COL-CENSUS does. The 65 running routes are all still in synthesis or floorplan (epyc8 kit logs at 21:28: 49 in yosys/synth, 16 in floorplan), so moving most of them to other hosts with the same staged launch costs minutes and avoids an out-of-memory wave on epyc8 later; that is a re-placement of the same kit, not a cancel for a newer plan. Run future kit gens at no more than about one per core. Evidence: 8 of 114 kits in 78 minutes; 65 routes on one 96-core host at load 348; spill refused in all 65 logs.
2. **Unblock cc3 with a one-row change (COL-CENSUS-1119).** Drop or re-site the bank that collides with clk_t41 in col_h9_r0_p4 pv70731479, add the bind's tap clearance to `cc_bank3_rows.py`, and re-bind once. A re-bind (build3b) is already queued; I did not check whether its plan carries that correction. It should not wait behind the D8i routes on epyc8: a bind is one job that gates 192 builds. Run the same generator check on the 84 rows COL-H10 adopted before that bind finishes, since they come from the same script.
3. **WINDOW-HOP row, 0 cycles (COL-CENSUS-1119, with PRECHECK-1119 for the estimator).** Move the single station to the middle of the worst-bit span. For col_h10_r0_p4 x_i0: y 712.8 -> about 869 gives two hops of about 355 um. Same form on col_h9_r0_p4 x_i0 and col_h9_r0_p5/p6 xo_i0 (36 types, 144 rows). If the site is taken by a core halo, use two stations (+1 cycle, pre-approved). PRECHECK should measure face-bus hops from the window extent; today the plan check passes all 144.
4. **p5 reset relay, -196 at CTS (COL-CENSUS-1119).** The path is one reset register (xo0_0 g_rsreg.rq) fanning out to the relay flops of xo2_1 and xo3_1. The type's `reset_replicate` rule matches only `u_cf_rs` drivers, so relay reset registers get no copies. Fix: extend the rule (or add a row) so each far relay group gets its own local reset register copy; reset release may slip a cycle (rst_n is held 64 clocks). p5 also has the 508-um xo_i0 hop above, so read the reset end again after fix 3; part of the -196 may be the same geometry.
5. **Bank hops: keep CC-BANK-1/1b/2 (0 cycles) as the first form and CC-BANK-2S (+1 stage) as the fallback, but measure before stacking more.** One caution on 2S: the added stage is a full-cycle register in front of a half-cycle capture, so the half-cycle leg still exists from the stage to the ROM pin. Site the stage at the ROM pin, not at the midpoint, or the gain is only half the wire.
6. **h9_r2 c12_6 -> s12 (-2.75 ps short on one end).** Two variants are signed at -39.22 on the same loop, so this is placement variance on a fixed-latency loop. Apply the 0-cycle c12_6 move (CC-RDLOOP-1) in the next row set; do not open a separate build for it.

### Stop list

- Stop launching a build wave from a tree that exists on one host without `--stage`.
- Stop starting more than about one kit generator per core on one host.
- Stop restarting whole-plan binds to add one more unmeasured row set. Three restarts produced no kit. Bind once, measure at CTS, then add.
- Stop citing h10_r1 -208 and h10_r2 -172 as old-plan baselines.
- Stop measuring face-bus hops from the window centre.
- Read `4_cts_post_hook.rpt` or GRT for col clock numbers, never `4_cts_final.rpt`.

## 2. Die hold

### What the three numbers are

| Number | What it is | Evidence |
|---|---|---|
| FF -438.25, TT -527.31 "measured" | A bound, not a path. Worst pair is the signed kit col_h9_r2__t1__cl774acf45__pv11b6518d against itself (taps t20/t12 -> t22, real tap skew 62.55 ps). The kit model uses one type-wide insertion range: lat_min 39.35, lat_max 416.53 ps FF. 416.53 - 39.35 + 62.55 - 1.5 = 438.2. | epyc10 `die-level-1119/runs/s81/rv2/sta_ca/die_sta_related.json`, `rv2/real_views/kits/col_h9_r2__t1__cl774acf45__pv11b6518d.json` |
| FF -218.8, TT -242.4 "contract" | Worst 200 pairs all capture at an unsigned core tap. The plain-tap side is priced at the die latency 250 ps. | epyc10 `s81-clock-window/die/runs/s81/cw6/holdpairs.json` |
| Kit-contract -99.99 (W 10, need 110) | The real tap-to-tap skew against the kit window. | same `die_sta_related.json`, `kit_contract_hold` |

**Cause of the -438.** The signed record's `insertion_pinflops` has n 1504, min 39.35, max 416.53 (FF). The same kit's own insertion band has n 1496, min 338.81, max 427.06 (epyc9 `fable-fix-s81-col/p774/s2/so_out/signoff.json`, `corners.ff.insertion_pinflops` and `insertion_band`). So 8 flops out of 1,504 pull the minimum down by 300 ps. The kit has four clocks (clk, vclk, fclk_in_cland_dn_0, fclk_out_cland_up) and 14 early core-tap ports; the 8 are most likely flops on a forwarded clock or an early port (inferred from the counts; I did not run the STA to name them). Without them the range is 88 ps and the same pair reads about -149. And even that is still a type-wide bound applied to a pair whose internal hold was signed at 0 inside the kit under its window. For a pair inside one signed type, the die adds only tap skew minus the window: 62.55 against a 40 ps window is about -22 ps.

**Cause of the -242.** `die_sta_related.py` line 3114 calls `S_.common_latency_ps(S_.Plan(plan), c)` with no type, so every plain tap is priced at 250 ps (202.5 FF). `schema.common_latency_ps` already takes a type and returns its own budget. In the D8g plan 344 of 395 types carry `clock.insertion_ps` 450 (all col, leaf, svc_rs, gunit, bk_sel). A 450 ps type's core tap with declared insertion 364 is 86 ps early against its own registers, but the STA sees it 114 ps late. That is a 200 ps error in the hold direction on class A (attn_hcore in svc). With the right basis the worst class A pair is about -42 TT, which is the real 142 ps tap skew less the 86 ps the core is early. The same correction makes the setup side of those pairs 200 ps worse than the model shows now, so expect the intra setup number to move too; those are in-kit paths and belong to the kit contract.

**The real problem: tap spread in every region, on every kind of tap.** From `cw6/proof/tap_arrivals_{TT,FF}.json` (393 DME partitions; my script `cwcmp.py`, numbers TT):

| Family | Regular taps p5 / p95 vs partition median | Partition range, median / max | Partitions already <= 40 ps | Core taps (arrival + plan early) median / p95 |
|---|---|---|---|---|
| col_h9_r0 | -29 / +27 | 60 / 93 | 2 of 60 | +22 / +48 |
| col_h9_r1 | -28 / +30 | 58 / 100 | 2 of 60 | +20 / +54 |
| col_h9_r2 | -31 / +32 | 60 / 96 | 4 of 60 | +23 / +52 |
| col_h10_r0/r1/r2 | -30 / +30 | 58-70 / 79-111 | 1 of 36 | +19..22 / +46..55 |
| leaf | -25 / +27 | 61 / 114 | 5 of 80 | -2 / +26 |
| slice_station (no core taps) | -26 / +29 | 50 / 118 | 12 of 41 | none |
| serdes (no core taps) | -33 / +23 | 58 / 107 | 0 of 14 | none |
| svc_lo / svc_hi | -36 / +44 | 74 / 126 | 0 of 16 | +4 / +59, 0 / +35 |

And from `cw6/kwpairs.json`, ports whose worst pair needs more than 40 ps (TT): col_h9_r2 regular-to-regular 210 of 359, regular-to-core 568 of 1,201; slice_station 660 of 2,016; serdes 198 of 677; leaf regular-to-regular 1,115 of 2,636.

Reading:
- The "core taps land late" classes are not a core-tap problem in leaf and svc: their core medians are 0 to +4 ps and their tails equal the regular tails. Only the col core taps have a real bias, +20 ps TT and +40 ps FF late.
- Regular taps alone miss a 40 ps window in 365 of 393 partitions. Any fix that touches only core taps leaves this.

### Does cw7 fix it?

**No. cw7 as built makes the spread worse, and the measurement says why.** cw7 (epyc10 `s81-clock-window/die/runs/s81/cw7`) is cw6 plus one change: per-pin sink offsets for 20,968 taps, each equal to the tap's measured cw6 error (`runs/s81_cw7.yaml`, `runs/s81_cw7_sink_offsets.json`). It is not a matched-cluster form; there is no cluster or composite-sink step in the config. Its routed tap arrivals landed at 21:16 (`cw7/proof/tap_arrivals_{TT,FF}.json`). Its die STA then stopped with an error at 21:26 (`cw7/ca/sta_ca.log`: `dsdv_bksel_c_tt.lib: missing boundary arcs (out 0 ...)`; the cw7 tools copy 2f306028d5 predates the per-view check on main f22d0e5f72), so cw7 has no hold or kit-contract number. The numbers below are from the arrivals.

| Family (TT) | cw6 regular p5 / p95 | cw7 regular p5 / p95 | cw6 partition range, median | cw7 partition range, median | Partitions <= 40 ps, cw6 -> cw7 |
|---|---|---|---|---|---|
| col_h9_r0 | -29 / +27 | -37 / +38 | 60 | 85 | 2 -> 0 of 60 |
| col_h9_r1 | -28 / +30 | -36 / +35 | 58 | 78 | 2 -> 0 of 60 |
| col_h9_r2 | -31 / +32 | -45 / +43 | 60 | 92 | 4 -> 0 of 60 |
| col_h10 (r0, r1, r2) | -30 / +30 | -41 / +41 | 58-70 | 87-99 | 1 -> 0 of 36 |
| leaf | -25 / +27 | -37 / +38 | 61 | 84 | 5 -> 1 of 80 |
| slice_station | -26 / +29 | -31 / +35 | 50 | 64 | 12 -> 7 of 41 |
| serdes | -33 / +23 | -37 / +44 | 58 | 82 | 0 -> 0 of 14 |
| svc_lo / svc_hi | -36 / +44 | -54 / +58 | 74 / 69 | 116 / 98 | 0 -> 0 of 16 |

All 393 partitions: 28 within 40 ps on cw6, 8 on cw7. With core taps counted at their cw7 targets the col partition range is 86-115 ps median and no col partition is within 40.

Why (14,767 regular taps, TT, my script `corr.py`):
- The offsets are exactly the cw6 errors (correlation 1.00, standard deviation 16.6 ps).
- The cw7 errors correlate -0.63 with the cw6 errors, and their standard deviation is 23.1 ps. Taps that were late are now early by about as much.
- If the offset is added back, the cw7 error has standard deviation 18.1 ps, the same size as cw6 and unrelated to it. 10,057 of the 14,767 taps changed stage count between the two builds.
- So the tree applied the offsets (gain about 0.87), but the error they were meant to cancel did not come back. The per-tap error of a region DME build is build noise, about 17 ps standard deviation, new on every build. Subtracting the last build's noise from the next build adds the two: 16.6 x sqrt(1 + 0.87^2) = 22 ps, which is what cw7 shows.

**This rules out the whole class, not only cw7:** any tree that is rebuilt with offsets taken from an earlier build will do this.

**What does work, measured on the same data.** Skew between two regular taps of one partition against how many stages they do not share (cw6 TT, 310k pairs, my script `depth.py`):

| Unshared stages below the common node | Pairs | Median skew | p95 | Share over 40 ps |
|---|---|---|---|---|
| 0-2 | 5,027 | 2.2 ps | 6.9 | 0 % |
| 3-5 | 8,560 | 5.2 ps | 15.9 | 0 % |
| 6-8 | 36,064 | 9.4 ps | 29.1 | 1 % |
| 9-11 | 35,194 | 13.0 ps | 38.6 | 4 % |
| 12-14 | 120,154 | 16.0 ps | 47.0 | 10 % |
| 15-20 | 104,937 | 17.8-19.5 ps | 52-59 | 13-18 % |

The noise builds up stage by stage on the unshared part. Taps that share a node within 5 stages are inside 16 ps at p95 and never above 43 ps. Most pairs in a partition sit 12 or more stages apart. S81-CLOCK-WINDOW proposed sharing at 19:13 and withdrew it at 19:24 because the cause is not derate. The lever was right; the cause is unshared build noise.

So the form that meets a 40 ps window is the matched cluster: taps that have data paths between them (a ROM or bank core tap and the regular taps it talks to, the station taps of one lane) are merged first, under one node within about 5 stages, and that sub-tree enters the region DME as one sink. This is the HEAD e5b/e5c "composite sink" form S81-CLOCK-WINDOW already asked for. The kits already carry the relation (`tap_pair_affinity`).

For what is left after clustering, correct the measured error on the same tree: keep topology and routes, change only the last leg of a tap, and measure again. That is a closed loop on one build. cw7 was an open loop across two builds.

### Ranked fixes

1. **Fix the two measurement errors first, because they hide the real number (DIE-LEVEL-CHECK-1119 for both; both are in tools it merged).**
   - `real_views.py` kit digest: take insertion per clock and per tap port, not one min/max over all pin flops; for a pair inside one signed type report tap skew minus that type's window. Expected: S81 measured hold moves from -438 to the kit-contract figure (-100 at W 10 today).
   - `die_sta_related.py`: pass the partition type to `common_latency_ps` for plain taps. Expected: class A from -242 to about -42 TT.
2. **Tree form cw8: matched clusters, then a same-tree trim (S81-CLOCK-WINDOW-1119; HEAD-CROSSING-1119 has the composite-sink patch).** Merge related taps under a common node within about 5 stages and feed each cluster to the region DME as one sink. Evidence: pairs within 5 unshared stages have p95 16 ps and maximum 43 ps on cw6; pairs 12+ stages apart have p95 47-59 ps. Then trim the last leg per tap from routed arrivals of that same tree, without rebuilding it.
3. **Col core taps: remove the +20 TT / +40 FF bias with the per-pin targets** inside the cluster, and set them for the FF corner, since hold is the FF gate and TT intra setup has +55 ps. A fixed bias repeats from build to build, so an offset does cancel it; only the random part does not.
4. **Whatever spread is left after cw8:** col and slice_station windows stay at 40 (COORD ruling; the col read loops cannot absorb more). For the other families use the measured per-port window, which costs hold cells only.

### Stop list

- Stop rebuilding the tree with offsets measured on the previous tree (cw7 form). Do not hand cw7 rows or its offsets file to S81-DIE-R3.
- Stop quoting -438 or -527 as the S81 hold. It is 8 flops in one record.
- Stop quoting -242 as a core-tap lateness. 200 ps of it is the 250 basis.
- Stop core-tap-only balance work for leaf and svc. Their core taps are centred; the spread is the same on regular taps.
- Do not apply CORE-EARLY or sink offsets to a tree without the matching insertion rows in the plan the STA reads (this is what produced -508 on the sink tree, DIE-LEVEL-1119 line 65-69). cw7 runs on the unchanged D8g plan 154b8c6d, so read its declared hold with that in mind.
- Do not widen col windows.

## 3. leaf: HI-group buses over the lane cores

**Root cause (confirmed on the render).** `epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-leaf/proof/t28wide/ot_s81sl_leaf__t28/run/layout_review/place/{layout,density}.png`: the 16 lane cores stand in two columns on the west side with gaps of a few um, next to vn_a/vn_b, and the station flops crowd into the rings around them. The east half and the north band of the partition are nearly empty (0-20 % density). The congestion is local demand over hard cores, with free area beside it.
- t28 hot gcells: 604 of 700 inside a hard-core box, capacity 5-8 per gcell (epyc10 `fable-fix-s81-leaf/hot/t28.map`).
- t28 buses: g_hig_0 s1 has 537 of 1,026 pins crossing a core, cst_vni s0 595 of 1,056 (`hot/t28.hig`).
- GRT: t27stb overflow 679 at 5.41 % total use, t27relay 344 at 6.32 %, t27keep at extra iteration 30/30, t28wide at 14/30 (epyc10 `fable-fix-s81-leaf/proof/*/run_grt.log`). l8_t74 routes at 0 overflow with 8.32 % use, so total use is not the limit.
- t31: the WREG stage removed the sw path, but the type is still at -912 ps setup estimate; the new worst path is again a HI station to a lane (lane post 19:30; `proof/t31wreg/.../run_route.log` shows -912.71 before repair, -979.37 after).

**Ranked fixes (FABLE-FIX-S81-LEAF and its Opus successor; rows to S81-DIE-R3).**
1. **Form A, corridor plus explicit bank sites.** Over a core only M6/M8 horizontal is left, about 10 tracks/um. A 1,025-bit group needs about 30 um of clear channel at 35 tracks/um; the gaps today are 6.5-15.1 um. Sites alone (form C) put the bank in a channel that still cannot carry the bus. The render shows the area is free, so widen further than the minimum: 45 um where one group passes and 60 um where a HI group and cst_vni (1,056 bits) share. The first A build failed only on a tool error (KITFIT-OVERLAP, lanes g_ln[12] and g_ln[6] overlap 2.16 x 97.2 um on t31; intel2 `~/lanes-opus-s81leaf/hic_build_A.log`). A2 is binding.
2. **Form C as the control,** to show how much comes from siting alone. It is already binding.
3. **Form B, lane remap, only if A leaves overflow.** It breaks reach on 103 rows (max hop 622 um) and the core_place gate refuses it on both types. It is the cleaner topology but the most expensive to prove.

**Stop list.** No leaf tap pre-pass (it dies in its own GRT, t27stb). No PG-setting experiments (69 logs show PG does not split pass from fail). No further t27/t28 GRT relaunch on the unchanged plan. Do not judge t31 on the WREG kit; its timing follows the corridor.

## 4. lepe: proof5 and the RIP1 rows

**State.** `epyc9 /srv/opentallas-scratch2/claude/fable-lepe/proof5/dsdv_slice_lepe_mu_LP__t2/gen/dsdv_slice_lepe_mu_LP__t2/run_grt.log`:
- GRT overflow 0 on every layer (first LP kit through global route; the lane-core LEF fix is proven).
- TT setup after CTS -530.49 (`tt_setup_measure.log`).
- GRT timing repair: WNS -283 at iteration 100, -270.3 at iteration 1,100, still -270.3 at 1,320. 715 violating endpoints throughout. Worst endpoint `u_bound.u_u_lep.u.rid[834]`.

**Root cause.** The repair has nothing left to do: 1,200 iterations moved the worst slack by 13 ps and the endpoint count by 0. The worst endpoints are the `rid` register, which is the 1,103-bit RX data register `ri` in `ot_s81sl_slice_lep.sv` (line 971-995: 8:1 RX row mux, then a 1,103-bit select fanout into rid). That is exactly the path RIP1 pipelines (ri +1, plan_rip1 534b57dc7886, benches PASS per S81-DIE-R3 18:12). proof5 is the form without RIP1, so it could not close, and the rid class hides the other long hops the lane listed from the CTS report (li -> k_li_r -496 ps / 762 um; lpc_i0 reset 1,117 um; k_lo credit loop with 3 legs >= 467 um; rop -> roq 1,581 um; now_status 1,184 um). I did not read the startpoints at GRT, because the repair holds the database.

**Ranked fixes (FABLE-FIX-S81-LEPE; S81-DIE-R3 applies RIP1).**
1. Take the per-group worst paths from proof5's GRT database and end the run. More iterations will not change it.
2. Build proof6 = proof5 + the RIP1 lep source (ri +1) + rows 1-3 as a private kit now, on the tree6 bind, to GRT TT. Do not wait for D8i to apply; RIP1 should arrive with a measured kit. Rows 4 and 5 stay provisional until proof6 shows them without the rid class on top.
3. Row 2 (reset branch copies) needs a bind form. Until it exists, realise the existing 3-station row, which is already in the plan and is not placed in these kits.
4. Flow note: the pre-GRT hold build was thrown away because TT setup would go from -530.49 to -552.56 against the -42 gate. On a kit that is already 500 ps short, that test discards the hold build for nothing and leaves 14,779 hold endpoints to the slow GRT repair. Compare against the kit's own setup before the build when it is already below the gate.

**Stop list.** No further repair iterations on proof5. No LP relaunch without RIP1 and rows 1-3. Do not raise the credit-loop CRP to 3 (breaks the rate cap, lane post 17:52).

## 5. serdes: H23 and T15P

**H23 (serdes__t13, hub at the pad, 200-um hops, 16 trunk stages instead of 31).** `epyc9 /srv/opentallas-scratch2/claude/fable-fix-s81-serdes3/H23/serdes__t13/gen/serdes__t13/`:
- TT setup on placement RC: -85.17 -> +1.49 after repair (`tt_setup_keep.log`, `tt_setup_measure.log`).
- TT setup on GRT RC: -119.23 -> -73.51 with 46 cells (`tt_setup_repair_grt.log`).
- rck span: 26,234 sinks, 1,705.3-1,794.3 ps, span 89.0 against a 110 limit, PASS (`run_route.log`, OT_STB_SPAN). The H18 form on t1 was 225.4.
- Now in GRT hold repair: 1,048 endpoints, worst -54.57.
- Against the earlier forms at the same point: H22 -179.1, H18 -191.7.

**Root cause of what is left.** The rck insertion is still 1.7-1.8 ns, and H22's worst paths were a 955 ps data path in the decoder (u_dec.u_syn am_ok -> xs, with a 12-buffer wire chain) plus about 7 ps of net skew. H23 cut the unshared clock depth in half and gained about 105 ps. The remaining -73.5 is mostly that data path, not the clock.

**Ranked fixes (FABLE-FIX-S81-SERDES).**
1. Let H23 finish route and sign-off; it is the first serdes form within reach of -42.
2. If routed TT stays below -42: one register on u_dec am_ok -> xs (R-RTL pipelining, +1 cycle pre-approved) before any more clock work. The clock span already passes.
3. H24 (M8 trunk) only if the routed worst path is a clock-skew path, which the H22 read says it is not.
4. T15P (serdes__t15, epyc8 `fable-fix-s81-serdes3/T15P/gen/serdes__t15__cla3d02796`) is in CTS tap balance. It carries the cohort fix and boot hook but, per the lane post, still the H18 rck form, so expect an H18-class TT (about -190). Move t15 and t1 to the H23 form once H23 routes; T15P's value is proving the cohort fix through route.
5. Cell count: T15P reports 443,168 movable cells, projected 501,905 with max-wire buffers, against the 400k tool limit (`run_route.log`, OT_CELL_CENSUS). That is advisory, but the largest design that ever closed was 517k; watch its CTS and GPL.

**Stop list.** No more two-level or feeder rck forms (H22 class). No rck tuning on t1/t15 before they are on the H23 form. Do not read the post-CTS band (mean 311.7 vs 250) as the serdes problem; it is the same in H21 and H22.

## 6. Owners

| Item | Owner |
|---|---|
| D8i route relaunch with staging; kit-gen concurrency | S81-GEOM-OPUS |
| cc3 bind row, generator clearance check, WINDOW-HOP rows, p5 reset row, c12_6 move | COL-CENSUS-1119 |
| Same generator check on the 84 adopted bank rows; h10_r1/r2 builds | COL-H10-1119 |
| Face-bus hop from window extent in the estimator | PRECHECK-1119 |
| real_views kit digest; plain-tap latency basis in die_sta_related | DIE-LEVEL-CHECK-1119 |
| cw8: matched clusters + same-tree trim; col core bias at FF | S81-CLOCK-WINDOW-1119 (composite-sink patch from HEAD-CROSSING-1119) |
| leaf corridor A2 / C / B | FABLE-FIX-S81-LEAF |
| lepe proof6 with RIP1 + rows 1-3; RIP1 apply | FABLE-FIX-S81-LEPE; S81-DIE-R3 |
| serdes H23 to sign-off; am_ok stage; t1/t15 onto H23 | FABLE-FIX-S81-SERDES |

## 7. Not checked

- No D8i, cc3 or h10 kit had a CTS or GRT report during this review, so every col fix above except 1a-1c rests on old-plan reports or plan geometry.
- I did not identify the 8 outlier flops by name.
- I did not read the startpoints of the lepe `rid` paths at GRT; the link to RIP1 is from the RTL.
- WINDOW-HOP was checked only on `internal_stations` rows launched by a face bus, col types only. Lane-level stations and the other type families were not checked.
- The 200 ps basis correction is derived from the code and the plan, not from a re-run of the STA.
- cw7's own die STA failed on a tool-version error, so there is no cw7 intra hold or kit-contract number; the cw7 verdict is from its routed tap arrivals. A re-run of the STA alone with tools at or after f22d0e5f72 would give it; I expect a kit-contract need above cw6's 110 ps.
- The depth table is for regular-to-regular pairs of one partition, all pairs, not only pairs with a data path.
