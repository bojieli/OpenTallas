# FABLE-DIE-QC: whole-die review of N3 and the N4 scope, QC die (qwen_compute)

2026-11-17 23:2x PST, FABLE-DIE-QC. V = I read the file or ran the check myself. R = reported by another lane, not re-checked.
The 11-16 report follows below, unchanged.

## A. Decisions for N4 (QC-PLAN-R3: apply these rows)

| # | item | decision | number behind it |
|---|---|---|---|
| 1 | partition split of six st_a_v1 + one st_b_v1 | **WITHDRAWN. No split in N4.** | (V) The 385-394k cell counts are from old events (hcut1111, efdb36e864, S4Q6D). On the current event the st_a_v1 rows have 54,031-54,942 cells (`kit_wave_state` items, event s29q103S4Q9N1B): u_r0..u_r3 are hard cores now. The wave does not refuse any of the seven. |
| 2 | the 8 rows the wave does refuse (SPLIT-NEEDED) | **Waive, do not split.** COORD: ruling id for `lanes/CELL-WAIVER.tsv`. | (V) Refused on N1B: sle_hc0__cl929603c0__cl38badc56 (351,252 cells, estimate 456,627), sle_hc0__cl929603c0__cl4baa7c9c (350,980), slw_hc0__cl1bc59e1c (350,582), slw_hc2__cla3497502__cl16607c7a (348,679), sle_st_b_v2__cl14c98df5__pvcd986c42 (367,452), sle_st_b_v2__clfde1249e (366,956), slw_st_b_v2__pvc2ec5bfb (357,415), slw_st_b_v1__cl6357f1cc__pv6ace3e48 (374,415). Three hc types of the same size are SIGNED R-MINIMAL (R, QC-N-OPUS 20:13): sle_hc2__cl9c4c4509__cl3edce1b8 348,842 cells, slw_hc3__clccfc3e6b 351,355, slw_hc3__cld86a7ad4 350,388. The limit counts about 105k tap/endcap cells. |
| 3 | st_b at 357-374k | Waive with the others. Split st_b (cut between u_r5 and u_r6) only if a waived st_b kit stops in GPL or CTS for a size cause, with its log line. | No st_b of this size has a sign-off yet. |
| 4 | coll_core taps | **43 taps, cap 4800, radius 230 (QC-PLAN-R3 rows) accepted.** | (V) Radius 200 is infeasible: `sink (5.4, 1323.0) has no legal clock tap within 200.0 um`. Max load 3,529 (clk_t6, far 118.8 um). 5 taps have far > 200 um; only clk_t27 is loaded (1,735 sinks, 226.8 um). Accept on the first kit: OT_TAP_BALANCE it0 every tap mean <= 290 and max <= 300. Fallback rows ready: cap 3300 / radius 230 = 51 taps, max load 2,935 (epyc8 `/srv/opentallas-scratch2/claude/fable-die-qc-clk/cc/taps_sweep_fdq.json`, key `3300_230`). |
| 5 | cbn_q00 clk_t115 | Split into two taps at (604.80, 2393.28) and (820.80, 2471.04), replacing (652.8, 2449.4). 8.64 grid; FABLE-FIX-QC-N checks the sites in the gen_phys tap table. | (V) `4_1_cts.log` of cbn_q00__cl622f65d2 N1B a2, last OT_TAP_BALANCE: clk_t115 mean 330 (316-402), 1,200 sinks. |
| 6 | the seven other cbn_q00 taps over the 1,200 cap | **No split. Closed.** | (V) Same log line: clk_t101 262 (249-292, 2,556 sinks), t19 261 (252-268, 1,487), t38 245 (231-272, 3,265), t42 244 (225-280, 1,856), t43 237 (219-270, 2,651), t95 253 (236-279, 1,785), t97 267 (254-288, 1,552). All inside 250 +- 40. Load up to 3,265 sinks is fine when the extent is <= 200 um; extent is what made t115 late. |
| 7 | clk_t50 | No split (R, one hop latch). | |
| 8 | group A rows (`n4a_plan.json` 1b7519eb) | fw_v1 `bus:x_st_a_o` 3 stations: PASS, 4 hops of 292 um. su_l1 lane7 +1 point: PASS on hop length (<= 304 um). | (V) One check for QC-PLAN-R3: in slw_su_l1__clcc9d0155 and __cla2a78701 three regs_um points sit at x 622.08, which is the type outline width. Move them to x 613.44 unless the generator already snaps them inside. |
| 9 | st_a flt_bank r2 -> r0 | 2 stations at about (425, 560) and (425, 300): accepted (R: hops 310 / 260 / 330 um). | Not checked by me: whether r1->r0 (482 um) and r2->r1 / r3->r2 (516 um) are live nets. Each live one needs 1 station. |
| 10 | tail copies | Carry `land_pad_tail_split` with the keep module and sited copies. Without a split this is the only fix for the -901 ps net. | (R) TAIL-REPL: unsited split -901 -> -912. |

## B. Whole-die review of N3 (plan 25f880974553, 377 partitions, 133 types, 2,993 ports, 1,921 lanes)

- (V) Strict bind 0 errors; LATCHECK 1,921 / 1,921; hard-core params 22 wraps, 0 mismatches; G0 0 errors, 491 warnings.
- (V) Channels: worst die cut 0.237 of capacity (horizontal @ 13,750); worst partition segment 0.534 (sl_W3_su_l1). No channel is a blocker.
- (V) Clock of record (M4 tree, comb feed): 313 regions, feed depth 12, fan-out 3, 42,253 taps; die GRT overflow 0 / 0 / 0; count-aligned crossings 2,993, fail 0, worst margins 105.1 / 112.5 ps; insertion max 10.57 ns TT. N3 keeps all 377 partition names, so the region map is unchanged.
- Not measured on N3: the tap-offset gate (section C). cbn_q00__cldbcda913 stays held until it reports.

## C. Clock-chain inputs: restored and proven

The deleted inputs are rebuilt. Durable copy: `lanes/handoff/FABLE-DIE-QC-clockchain/` (coord). Also on epyc2 at the old path `/srv/opentallas-scratch2/claude/fable-die-qc/{maps,m}` (QC-PLAN-R3's `chain_n3clk.sh` finds them unchanged) and on epyc9 `/srv/opentallas-scratch2/claude/fable-die-qc-clk/in`.

| file | source | proof |
|---|---|---|
| `maps/regions_s3d.json` | rebuilt from the M4 kit `tree.json` (tap -> region root) | 377 partitions, 313 regions, 0 conflicts; equal to the surviving `regions_plain.json` on all 377 |
| `m/feed_comb_fw_3.json` | rebuilt from the `feed_edge` nodes of the same tree | root sl_E0_fw, 312 edges, depth 12, fan-out 3; all 312 edges use the midpoint tap, so `tap` is empty |
| `maps/c_regions.txt`, `su_regions.txt`, `early_other_regions.txt` | epyc8 `die-qc-103/clk` | 192 + 12 + 36 = the 240 `dme_regions` of the M4 tree, exactly |
| `maps/inv2_stage_cal_s28dme.json`, `edge_readout_patch.py`, `mk_combo_kv.py` | epyc8 `die-qc-103/clk` | replay on the M4 kit gives `combo.tcl` and `combo.v` byte-identical to the M4 run |

The file hashes differ from the old ones (key order); content is proven as above. Not proven: a full kit re-run on the M4 plan reproducing its `tree.json`.

Recipe (in the same folder):
1. `clockchain_inputs.py PLAN BASE OUT`: checks a plan against the map, the feed and the lists. A new partition name is mapped to the region whose box holds its centre. N3: 377 mapped, 0 new.
2. `chain_clk.sh NAME` with `R`, `E` (event tree), `P` (plan): the same steps as `chain_n.sh`, with no host paths. It runs in the tree of the plan, not in treeJ.
3. Read `CHAIN.log`, `reg/sta.log` (TAP-OFFSET-GATE), `reg/kitoffs.json`. Rewrite a row only where the gate fails.

N3 proof: **queued, not running.** Client intel2 pid 3992632, log `~/fable-die-qc/n3clk.client2.log`, output epyc9 `/srv/opentallas-scratch2/claude/fable-die-qc-clk/chain/qc/s4q9n3`. ot-run holds it: epyc9 scratch has 72 GB free and falls 102 GB/h (floor 50 GB). It starts by itself when the fall stops; the run takes about 2.5 h.

N4: run the chain again on the N4 plan after rows 4 and 5 are in. The 43 coll_core taps and the two t115 taps start at offset 0, and coll_core is `clock.source`.

## D. Die-level blockers

1. **Tap-offset gate on N3 is unmeasured** until the queued chain runs. Blocks: release of hold `qc-cldbcda913-tapoff-n3-1117`, and the N4 coll_core offsets.
2. **epyc9 scratch: 72 GB free, falling 102 GB/h.** It is a QC gen host. The N3 kits and my chain both need it. FLEET-OPS-R.
3. **8 QC types cannot launch** (row 2) until the waiver ruling exists. The N4 split list would not have unblocked any of them.
4. No floorplan, region or channel blocker found on N3.

## E. Not checked

- The st_b_v1 type on the split list (sle_st_b_v1__pvc5a85fd4__pv7b7fafb4): its current cell count (its N1B row failed at place with no count).
- Group B landing-contract stations and the coll_core contract re-solve: no draft exists yet.
- clk_c0..c3 of cbn_q00 read 398-493 ps in the same log line (core clock pins, 1 sink each); I did not compare them with the declared core insertion.
- clk_t130 max 316 ps (1,108 sinks) and clk_t47 mean 196 ps (173-275) in cbn_q00: advisory, one kit only.
- The tt_ctlm pipe stage (FABLE-FIX-QC-N).

---

# FABLE-DIE-QC: whole-die verdict and plan event, QC die (qwen_compute)

2026-11-16, FABLE-DIE-QC. MEASURED = computed by me from the files named. Work dir epyc9
`/srv/opentallas-scratch2/claude/fable-die-qc` (bin/ scripts, an/ outputs, delta/ plans); epyc2 same path for the S4q9c chain.
Render (place + clock + GRT, 4 panels): intel2 `~/fable-die-qc/qc_die_s4k.png` (+ `_zoom.png`, `render.py`).

## 0. Verdict

**The floorplan and die routing are sound. The die clock is the weak structure, and one reset class was unowned.**

- Die GRT0 passes: overflow 0 / 0 / 0, use M4 3.0 %, M5 5.8 %, M6 5.4 %, M7 4.1 %, M8 0.6 %, M9 1.1 % (S4k, 50 it, TT = FF).
- Die STA had never produced a result on QC: `die_sta_related` crashed on every plan since S3R. Fixed (section 3).
  First result (S4k routed clock): setup passes (+362 intra, +540 seam), **hold contract fails** (-115 intra, -59 seam)
  and 5,014 of 84,302 taps are outside their plan offset band.
- Plan of record at die level is S4q9c (S4q9b + 3 PHY outline rows; FABLE-FIX-QC-KNEE-HC). S4q9b itself never bound.

## 1. Data read

| item | source |
|---|---|
| floorplan, lanes, clock rows | treeA `zz_s29_qc103_s4k.json` sha 146326183743; treeE `zz_s29_qc103_s4q9c.json` sha dd47490db390 |
| die kit, GRT0, routed tap arrivals | epyc9 `die-grt0-qc/qc/s4k` (DIE-QC-103, 11-15 17:01): the latest complete die run |
| die STA | epyc9 `fable-die-qc/an/sta_s4k/sta.log` (mine, on that proof) |
| reset audit | epyc9 `fable-fix-qc-knee-hc/bind/bind_s29q103S4Q9CBR` bound RTL, `fable-die-qc/an/raw/audit_s4q9.json` |

## 2. Whole-die numbers (S4k die run)

Die 31,216 x 25,644 um (800.5 mm2), 377 partitions of 130 types, abutted, 97.7 % covered, 3 channels in the west strip.
12 slice columns (E0..E5, W0..W5); slice row in the band y 10.2..15.4 mm; cb fabric above and below (192 partitions,
604 mm2); coll / glue / native59 / tt_ctlm / PHY in the west strip (x < 1.56 mm).

| structure | number | judgement |
|---|---|---|
| die GRT0 | 613,429 nets, 649.6 m, overflow 0 | PASS |
| M4-M7 demand | concentrated in the slice row; hottest gcells on the slice-row seams y = 11,556 and 13,414 um (M4 409, M7 430 tracks of demand in one 10.8-um gcell, no overflow) | watch: the 12 st_a / st_b ft bands (b_hw_ctl_hc, 37,788 ft bits over 405 um) all cross these two seams |
| M8/M9 demand | clock feeds; hottest at (1,890, 2,538): M8 515, at the corner serdes PHY / c_W5_bf_00 | watch |
| clock network | 127,530 inverters, 9.45 m wire, 42,256 taps, 313 regions, link_htree feed rooted at sl_E0_fw | see below |
| clock insertion (TT routed) | 0.67 ns at the root to **14.12 ns** at c_W5_tn_10; up to 306 stages; feed chain depth 21 regions | BAD shape |
| late - early at one tap | up to **1,828 ps** (c_W5_tn_10) | BAD: OCV of the serial feed |
| clock phase across plan ports | 2,993 ports: 1,583 over T/2, 689 over one cycle, worst 7,509 ps (sl_W3_hc2 cws2) | absorbed by count-aligned rings (S3R: depth 8 on 113 crossings, worst margin 104 ps) |
| adjacent partitions, 7.3 ns apart | sl_W3_su_c -> c_W3_bn_10 landed pair, clock damage 7,277 ps | BAD: feed order does not follow this data edge |
| related-pair skew inside a region | intra 356 ps, seam 183 ps (after declared early taps) | over the 87 / 110 ps kit windows |
| same type, different instance | cb types: per-port offset differs by up to +-129 ps between instances (cbn_q01 cld9ff4c40, 10 instances) | BAD: each instance gets its own region tree (entry face and site slides differ) |
| clock cells | 5 of 127,530 outside a partition; 0 illegal after slide (4,084 nodes moved) | PASS |
| lanes | 1,921 lanes, 18,010 cycles (stations 4,546, clock landing 6,766), longest 49 (rsf, 12 lanes) | OK |
| reset | wavefront from glue (west strip); die stand-in net only | reset timing is per type, section 4 |

## 3. Die STA: tool fix and first result

`die_sta_related.kit_windows` built a two-field shim for `gen_phys.tap_window_ps`; with a `tap_offset` row on a type with
early core taps it raised AttributeError, so chains s3r_b and s4k ended `REG_STA 1`. Branch `claude/fable-die-qc-1116`
@f7cee816db7, gate GREEN 37/37 (main e671bdd4a26), READY posted.

| class (S4k) | pairs | TT setup | FF hold, kit contract | window / need |
|---|---|---|---|---|
| intra region | 5,965,594 | +362.0 | **-114.9** (64,762 pairs) | 87 / 201.9 |
| plain seam | 2,015,980 | +540.4 | **-59.2** (2,797 pairs) | 110 / 169.2 |
| landed (no count-align) | 12,913,089 | info | info | damage 7,887 ps |

Hold on real views: BLOCKED(kits), 0 measured (no signed view of most types yet). Early core taps: 1,461, all declared.

## 4. Reset reach: raw reset -> FSTART face flop (COORD lever C audit)

All 130 types, bound RTL of S4Q9CBR: 1,142 FSTART face flops. 1,014 (110 types) take a local same-cycle copy
(`clock.landing_local_resets`). 128 in 9 types share one START raw reset:

| type | flops | over 405 um | worst um | fix |
|---|---|---|---|---|
| glue | 32 | 32 | 2,108 | S4q9d (FABLE-FIX-QC-CBGLUE); r199 review ADOPT-OK posted |
| cbf_q01, cbf_q01_s2 | 5 + 5 | 2 + 5 | 2,339 | S4q9d |
| **coll_core** | 14 | 4 | 1,745 | **my rows**: 6 leaves / 15 consumers |
| **native59** | 37 | 28 | 1,228 | **my rows**: 7 / 38 |
| **tt_ctlm** | 26 | 23 | 957 | **my rows**: 4 / 27 |
| coll_n, slw_hc3 x2 | 3 + 3 + 3 | 0 | < 300 | none |

So this is not a die reset-tree problem: the die tree and per-type relays exist; six types lacked the leaf rows.
0 added cycles (leaf depth = old reset depth), hops in <= 366 um, out <= 148 um.

Not checked: writer_start / reader_start chain members (no site in the bound RTL; needs a placed dump per type).
QC-CBGLUE's 06:43 raw-branch delta must not be applied to the 14 cb types that already have local resets.

## 5. Plan event

| # | rows | types | cycles | state |
|---|---|---|---|---|
| 1 | `landing_local_resets` + `reset_tree_anchor` on coll_core, native59, tt_ctlm | 3 | 0 | rows handed to FABLE-FIX-QC-KNEE-HC (lanes/handoff/FABLE-DIE-QC-rows.json), which composes the one S4q9e; my own copy is withdrawn |
| 2 | clock rows from the S4q9c routed proof: `clock.tap_offset.per_port_ps`, `seam_hold.seam_ps`, `tap_window.per_type_ps` | all | 0 | method PROVEN on S4k (section 6); rows for the current plan wait for the S4q9c chain |
| 3 | region trees built once per type and reused in every instance (tool change in die_trial region DME), so the +-129 ps instance spread goes to the +-10 ps floor | 14 cb types, 192 partitions | 0 | not started; next step |
| 4 | feed: cb regions fed from their own slice column instead of the 21-deep chain | clock only, K re-plan | lane cycles re-derived | not started; do only if count-align on S4q9c shows margin under 50 ps |

## 6. Proof

RUNNING: die chain on S4q9c, epyc2 `fable-die-qc/chain/qc/s4q9c` (kit, GRT0 TT / FF 50 it, tap arrivals, die STA,
count-align C / D, STA with count-align). Client log intel2 `~/fable-die-qc/chain_s4q9c.client.log`. The S4k kit stage took
3 h 35 min.

### 6.1 Clock rows delta proven on S4k (epyc2 `fable-die-qc/s4k/out`, a = plan rows, b = rows re-derived by `bin/clock_rows_delta.py`)

Second tool cause found: the offset rows were mean +- half range over the instances of a type, which cannot cover a skewed
set of 3 or more instances. Branch head @dd7250845f3 writes the mid-range (gate GREEN 37/37).

| check (FF, same routed clock) | a: S4k rows | b: re-derived rows |
|---|---|---|
| TAP-OFFSET-GATE | FAIL, 5,014 of 84,302 outside | **PASS, 0 of 84,512** |
| intra kit-contract hold | -114.9 (W 87, need 201.9, 64,762 pairs) | **0.00** (W 79, need 79.0, 0 pairs) |
| seam kit-contract hold | -59.2 (W 110, need 169.2, 2,797 pairs) | **+10.8** (W 180, 0 pairs) |
| TT setup intra / seam | +362.0 / +540.4 | unchanged |

Delta b = `clock.tap_offset.per_port_ps` (52 of 130 types change), `clock.tap_window.per_port_ps`, `seam_hold.seam_ps` 110 -> 180.
Cost: the 52 changed types get a new kit SDC; seam hold repair covers 180 ps instead of 110. Hold on real views stays
BLOCKED(kits) until types are signed.

## 7. Proof on the plan of record S4q9c (die chain, epyc2 `fable-die-qc/chain/qc/s4q9c`, 11-16 08:36 - 11:56 PST)

| gate | result |
|---|---|
| die GRT0, TT and FF, 50 it | **PASS**: overflow 0 / 0 / 0, 649.6 m, usage 4.06 % |
| routed taps | 42,256 TT and FF, 0 missing, 313 regions |
| die STA, plan rows | TT setup +362.0 intra / +540.4 seam; FF contract hold -114.9 / -59.2; TAP-OFFSET-GATE FAIL 5,014 of 84,302 |
| die STA, re-derived clock rows (`ck/b`) | **TAP-OFFSET-GATE PASS 0 of 84,512; FF contract hold intra 0.00, seam +10.8**; TT setup unchanged |
| count-align plan C / D | 2,993 crossings, FAIL 0, depth 8 on 113 and 4 on 2,880, worst margin 104.4 ps, 300-chip MC 0 violations |
| die STA with the count-align bind | **3 of 2,993 crossings FAIL**: io_serdes_2 -> c_W5_bf_01 (rx_flit_serdes_rx, rx_v_serdes_rx_valid, tx_up_serdes_up), depth 4, margin lo -107.1 TT / -67.0 FF, hi +1,968 |
| hold on real views | BLOCKED(kits): 0 pairs measured |

Open finding: the 3 serdes-PHY crossings. The planner (ca_C) passes them and the STA with its bind does not, so either the PHY
tap is priced differently in the two tools or K on these 3 ports is one cycle short (hi margin +1,968 leaves room for +1).
Not resolved by me; it sits at the M8 hotspot corner (1,890, 2,538). Owner: the QC event lane, before a die clock freeze.

Clock rows for the event: `lanes/handoff/FABLE-DIE-QC-clock-rows.json.gz` (sha of the JSON bff5d72cc996; 52 of 130 types change,
seam_ps 180) + `FABLE-DIE-QC-clock_rows_apply.py` (refuses a plan whose clock ports differ from the proof).
