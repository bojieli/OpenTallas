# FABLE-DIE-KV: whole-die verdict and die event for KV (qwen_kvsys), 2026-11-16 PST

MEASURED = run or computed by me today. REPORTED = from a lane post. All runs use the v2 tools (main eb1e73448bd0) on
plan kvgeom7yhr 723fd5b4b006. Work dirs: epyc9 / epyc7 / epyc2 `/srv/opentallas-scratch2/claude/fable-die-kv`
(runs/<tag>/CHAIN.log); logs intel2 `~/tmp/fdkv`; row files intel2 `~/tmp/fdkv/event/`. Branch
claude/fable-die-kv-1116 @272407d9f41 (remote gate GREEN 1/1).

## 0. Verdict

The KV die floorplan and die routing are sound. The die clock is the weak structure: it was last built as a cohort on
11-02 (tree_kv58: 2,114 taps, 15,938 cells) and the plan now has 10,832 taps and 32,858 cells, so the islands, the tap
windows and the clock form in the plan are all stale against the die they describe. No floorplan move, outline change
or cycle is needed. One die delta (section 3) brings the clock, its sites, its windows and the START reach back in
line with the plan.

| item | number (7yhr, record clock form) | verdict |
|---|---|---|
| die GRT0, TT and FF, 50 it | 0 overflow, use 2.47 %, 286.6 m wire, 7.5 GB | PASS |
| die STA setup, related pairs | intra +447.1 ps, seam +487.2 ps (TT) | PASS |
| count-aligned landed gate | 3,915 / 3,915 TT and FF; worst lo +162.8 / +203.7 ps | PASS |
| lane latency (FABLE-FIX-KV-PVHUB gate) | LATCHECK 2404 / 2404 | PASS (REPORTED) |
| die hold on real views | 0 measured of 1,260,450 pairs | UNMEASURED (section 4) |
| kit clock-arrival contract | 961 intra pairs in 9 regions + 19 seam pairs over the plan windows | BAD |
| die clock cell sites | 570 of 32,858 cells in a declared island | BAD |
| tap slew | 21 taps over 150 ps, max 224.7 (all pv_N_7) | BAD |
| cross-face hops | 39 ports / 7,128 bits over 405 um, max 530.2 | BAD (hg / hgi rows) |
| START reader hop | 13 types over 405 um (405.4 to 573.0) | BAD |

Render viewed: whole-die floorplan + feed tree, clock tree + cells, tap insertion map
(intel2 ~/tmp/fdkv/die_b7.png).

## 1. What the render and the numbers show

- Floorplan: 9 mirrored columns (phy | pc | hg | hgi | pv | hgi | hg | pc | phy), 8 rows N and 8 rows S of the hub
  band at y 12.2 to 13.8 mm, io / sys row on top. Data flows along rows into the pv spine and along the spine to the
  hub. All 3,915 ports abut (602,002 bits, pin gap 0). Partition placement matches the data flow; I found no region
  or channel mismatch. Worst cut 0.1613, worst segment 0.5027 (G0, REPORTED).
- Clock tree shape: root at hub_C, one N-S spine through the pv column, E-W branches per row, 128 region trees.
  Insertion is 720 to 7,149 ps TT over up to 176 stages. That depth is common to related pairs (CPPR), and the
  count-aligned gate passes on it, so it is not a failure. The local skew is what matters: per-partition tap spread
  median 99.6 ps, p90 152.8, max 246.5 (pv_S_6).
- The region DME list of record (pv_S_6, pv_S_7, sys_SW, sys_SE) is wrong for this plan: pv_S_6 is the worst region
  because of its DME tree (246.5 ps; 223.1 as an H-tree), and pv_N_7, an H-tree, has the 21 slow taps.
- All 32,858 die clock inverters sit on partition area: 30,264 on soft type area with no reservation, 2,024 on the
  signed hard types kv3_phy / kv3_phy_v1, 570 in a declared island. On the PHY types 0 of the 2,024 cells are within
  1 um of one of the 45 / 55 declared islands (median distance 165 um). The die clock kit recipe runs without
  island sites, so it ignores them.
- Kit windows: the plan gives every tap port of a type one flat window (mean 136 ps over all ports). The measured
  need per port is 65 ps on average, and 17 types have a port above their flat window. So most ports are padded
  for twice the damage they see, and 17 types are under-covered.
- Sidebands (COORD lever C): no cross-face port of width <= 4 and no reset / fault / ready / start named port is over
  405 um (1,616 narrow ports, max 401.9 um). The over-reach is on wide ft buses only (section 3 row D). Inside types,
  the one-cycle START reader hop is over reach on 13 types (row A).

## 2. Clock forms measured (each: die kit, GRT0 TT + FF, die STA)

| run | form | intra contract pairs (need ps) | seam pairs (need ps) | slew max / over 150 | TT setup intra |
|---|---|---|---|---|---|
| b7 | record: H-tree + DME on pv_S_6, pv_S_7, sys_SW, sys_SE | 961 (207.3) | 19 (201.0) | 224.7 / 21 | +447.1 |
| b7h | H-tree everywhere | 218 (191.7) | 19 (201.0) | 224.7 / 21 | +468.0 |
| b7d | DME everywhere, old stage model | 13,884 (232.6) | 0 (163.7) | 49.2 / 0 | +444.7 |
| b7e | DME everywhere, refit stage model | 13,061 (212.9) | 0 (145.5) | 53.6 / 0 | +450.9 |
| b7f | b7e + early core taps (1.0 / 0.87, merge) | 14,045 (356.7) | 84 (212.1) | 49.1 / 0 | +338.1 |
| b7g | H-tree + DME on pv_N_7 and phy_EN_7 / ES_7 / WN_7 / WS_7 | 127 (178.0) | 8 (188.5) | 138.9 / 0 | +482.2 |

All six: GRT0 0 overflow. b7g is the form of the event (tools/clk/configs/kv_7yhr.yaml). DME everywhere fixes slew and
seam but makes every hg / hgi / pv region worse inside; early core taps make it worse again. Stage model refit on
21,536 routed legs: rms 5.52 TT / 5.04 FF (entry inv_ndr_kv_7yhr_b7d; the 10-29 entry reads 8.93 / 8.03 on this tree).

## 3. The die delta (rows for the ONE next KV event, KV-HG1; nothing here competes with 7yhr)

Row files: intel2 `~/tmp/fdkv/event/` (also epyc7 and epyc2 fable-die-kv/event). Apply with
`tools/die_plan/die_rows.py apply PLAN ROWS... -o OUT`. No outline, core, pin, port, station or lane cycle changes.

| row | file (sha256) | types | content | check |
|---|---|---|---|---|
| A START reach | rows_reach.json (4d7888ceb91d) | 13: kv3_pv_v2 .. v6, v2n .. v6n, kv3_hg_v1p5, v1p6, kv3_io_cor_v1 | `clock.landing_reader_start` from `reach_rules.py fix --rules 1` (shared relay trunk per hub, depth uniform per type, 0 data cycles) | reach_rules check 13 errors -> 0; lanes changed 0 of 2404 |
| B clock sites | rows_sites.json (efbb1095ee48) | 51 unsigned | `clock.reserved_sites_um`, 9,228 rects (placement blockage + M1-M7 window), from the b7g tree by `clksite_reserve.py --tree` | area 0.28 mm2 of 302 mm2 |
| B2 clock sites, signed | rows_sites_signed5.json (bef1b3fd4588) | kv3_phy, kv3_phy_v1, kv3_io_ft_v1, kv3_sys_SD, kv3_sys_SD_v1 | same rule, 469 rects | NOT in the event: needs a rebuild + re-sign of the 5 types |
| C windows | rows_windows.json (1205d42c8ff4) | 51 unsigned | `clock.tap_window.per_port_ps` = measured per-port damage of the b7g tree; `clock.seam_hold.seam_ps` 180 -> 200 | 1 port clamped at 208.25 (kv3_pc_v1__cl4ea58a5c clk_t25, need 211) |
| D ft hops | list in section 5 | hg / hgi / hub_Wi | 39 ports with last station -> out pin 412 to 530 um | not built: belongs in the hg compose (KV-PVHG-O) |
| E clock form | kv_7yhr.yaml on the branch | die | b7g | section 2 |

Order inside KV-HG1: compose types (v25hv, k2) -> row A -> die clock kit with kv_7yhr.yaml on the composed plan ->
regenerate rows B and C from THAT tree (v25hv adds 106 core taps, so B and C cut today are stale after the compose:
the files above are the proof of the method, the script is the delta) -> G0 / bind / LATCHECK -> die proof.

## 4. Open, with owner

| item | number | next step | owner |
|---|---|---|---|
| die hold on real views | 0 measured / 1,260,450 pairs; 72 view keys missing | die kit with `--views` of the signed records (5 types, 16 ring masters, ectlk q0-q3, head eighths) -> first measured hold | FABLE-DIE-KV |
| signed PHY under the clock | 2,024 cells on kv3_phy / kv3_phy_v1, 0 on their islands | row B2 + rebuild of the PHY model types, or a stamped tree on the 45 / 55 islands | FABLE-DIE-KV with FABLE-FIX-KV-PVHUB |
| kv3_sys_SD window | need 81 ps against flat 80 (signed type) | covered when B2 lands; 1 ps | FABLE-DIE-KV |
| 39 ports over reach | max 530.2 um (hg_EN_0 ft2_o -> hgi_EN_0 ft27_i, 513 bits) | station re-site in the hg compose | KV-PVHG-O |
| reserved rect count | max 366 rects on one type (cap target 100) | coarser merge after the compose | FABLE-DIE-KV |

## 5. Ports over 405 um (die_hop_scan, byte-equal on 7uh and 7yhr)

L2075_1 hg_EN_0.ft2_o -> hgi_EN_0.ft27_i 530.2; L1449_1 / L1450_1 hub_Wi.ft5_o / ft6_o -> hub_Wo 468.4 / 434.4;
L2045_12 hgi_WN_7.ft27_o -> hub_Wi 449.6; L346_2..8 hgi_EN ft20_o / ft16_o chain 440.4 to 443.6 (59 bits each);
L663_1..8 host.fdi hgi_WN ft4 / ft8 chain 412.6 to 433.4; L350_9 hgi_WN_7.ft17_o -> hub_Wi 432.4;
L1524_2..8 hgi_WN ft11 / ft15 chain 418.8 to 427.4; L1427_2..9 hgi_EN ft2 / ft6 chain 417.1 to 425.3;
L2090_1 / L2129_1 / L2168_1 / L2207_1 hg_*_7.ft3_o -> hgi_*_7 414.5. In every case the long part is the last station
to the out pin inside the sending type.

## 6. Proof of the composed plan (7yhr + A + B + C = 5cfab111c977), MEASURED on epyc2 fable-die-kv/runs/p1 and gate/

| check | result |
|---|---|
| G0 (check.py --r8-strap-pads) | PASS, 0 errors, 2,351 warnings (7yhr: 2,364) |
| reach_rules check | 0 errors (7yhr: 13), 8 warnings |
| die clock kit, form b7g, with 48,865 reserved windows cut from the abstracts | rc 0; 32,861 inverters, 10,832 taps |
| die GRT0 TT and FF | 0 overflow, use 2.47 %, 286.6 m |
| die STA setup TT | intra +482.2 ps, seam +510.1 ps |
| kit clock-arrival contract, per-port windows | intra 0 pairs (worst residual 28.0 ps), seam 0 pairs; 1 advisory violation left = the port clamped at 208.25 |
| tap slew | max 138.9 ps, 0 over 150 |
| count-aligned gate | 3,915 / 3,915 TT and FF; worst lo +193.9 / +131.1 ps, hi +818.0 / +763.5; bind sim_window_violations 0, min margin +118.5 |
| die clock gate verdict | BLOCKED(kits): hold on real views unmeasured (section 4) |
| strict bind + LATCHECK | not obtained on this plan: first try REFUSED by plan_gate_pre INPUT-MISSING (my plan copy sat outside a tree), the rerun waited on epyc2 disk. The same rows pass both on HG1B (section 6b) |

## 6b. KV-HG1 as composed (13:40 PST; composed and gated by FABLE-FIX-KV-PVHUB / Codex with these rows and scripts)

- kvgeom7yhr is adopted (r322, 10:27). HG1A = 7yhr + v25hv + k2r + row A (13 START rows), plan 08d352df7ef0:
  pre 0, G0 0 errors, strict bind 0, LATCHECK 2404 / 2404 (REPORTED, epyc10 fable-fix-kv-pvhub/hg1/gate/gate.out).
- Die run on HG1A with kv_7yhr.yaml + the refit model (epyc10 hg1/runs/c1), MEASURED by me from its outputs:
  33,360 inverters, GRT0 0 overflow (use 2.48 %), setup TT +482.8 intra / +510.6 seam, slew max 128.4 ps (0 over 150),
  count-aligned 3,915 / 3,915 TT and FF (worst lo +177.7 / +210.0). Against the old flat windows it still shows
  376 intra + 8 seam contract pairs: that is the input of row C, as on 7yhr (127 + 8).
- HG1B = HG1A + rows B (9,286 rects, 51 types) + C (per-port windows, seam 200) regenerated from the c1 tree, plan
  b78d8aa38797: pre 0, G0 0, bind 0, LATCHECK 2404 / 2404 (REPORTED, hg1/gateB/gate.out). No die run on HG1B itself;
  the same step on 7yhr (section 6) gave 0 / 0 contract pairs and 0 overflow with the windows cut.
- My own strict bind + LATCHECK of 5cfab111c977 (epyc2 gate2) is redundant after HG1B and still running; not a gate.

## 7. Not checked

- Detailed route of the die top (GRT only). PG / IR (no PDNSim run). Reset relay hops (REPORTED max 326 um on hroot,
  under 405).
- Rows B and C on a real type kit: no type was rebuilt with them.
- The b7g tree under OCV: the SS information run of the record form fails 212 crossings (information only).
