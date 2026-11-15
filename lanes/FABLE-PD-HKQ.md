# FABLE-PD-HKQ 2026-11-14: technical physical-design review of HEAD, KV and QC

Scope: design causes only. Read-only review of kits, logs, plans and sign-off records, plus one small STA read of my own (ot-run, epyc2 `/srv/opentallas-scratch2/claude/fable-pd-hkq/`). No job was touched.

Status words: MEASURED = read from a log, record, database or my STA run. INFERENCE = fits the numbers, not proven.

## 0. Top levers, ranked by types unblocked

| # | die | lever | types | owner |
|---|---|---|---|---|
| Q1 | QC | PG-pair-row hook in the QC source, then regenerate (DRT-0255) | 13 | PG-AWARE-1 |
| Q2 | QC | ID-strap pins snapped to the M5 track in the generator, regenerate from floorplan (DRT-0206) | 11 | TYPE-QCCOLLN |
| Q3 | QC | pre-GRT hold repair: accept test on core-owned paths only (HOLD_STALL) | 8 | NEARMISS-FIX-1 / KIT-OPS-5 |
| K1 | KV | hard ring masters (kvgeom7) plus the band bridge, for the soft landing rings | 30 | KV-102, OVERSIZE-1, KIT-OPS-6 |
| K2 | KV | hgi/hg: M7 closed over the head cores in the generator, and no antenna-repair step on allow-congestion kits | 9 | TYPE-KVHGI2, KIT-OPS-5 |
| K3 | KV | kv3_pc early core taps (kvgeom6) | 6 | KV-102 |
| K4 | KV | tap pair affinity for io_cor / hroot / io_ft_v1 (kvgeom7) | 4 | KV-102 |
| H1 | HEAD | hd_host_e: plan points at the 11-10 `u_epc` timing model; point it at the signed one | 1 (last hard HEAD type) | HEAD-REMAP-1 |
| H2 | HEAD | hd_host_e: head SRAM stacks 5-8 are 480-560 um from their `in_data` pins; move them or add a register slice | same type | HEAD-99 |

## 1. HEAD hd_host_e

### 1.1 Verdict on the two earlier explanations

- TYPE-HDEPC is right on both points. The earlier Fable note (FABLE-HARD-QCHEAD section 3, clock part) is wrong and is withdrawn here.
- HEAD-REMAP-1's what-if ("no `u_epc` clock shift closes it") is right in its conclusion, but its numbers came from the old model, and its follow-up ("the fix is inside the core") is wrong. The core is fine. The failing path is in the parent.

### 1.2 What is measured

Routed database: epyc2 `/srv/opentallas-scratch2/claude/head-99/kits21z9/g_hd_host_e_ws/hd_host_e` (the only hd_host_e form that routed).

1. **The timing model is old.** The kit carries `ot_s81hd_he_epc_tt.lib` sha 8aad8716. The same file is in `kits20b` of 11-13 16:32 and in the source tree as `results/head_he_epc_h2_1110/` (dated 11-12). The signed core (`head-97/hepc_south/eco99_south_g2/i1`, signed 11-13 21:12) has sha f663e343.
2. **The LEF is current.** Three pins checked against the signed core's `6_final.def` (`in_data[441]`, `rr_lo[1]`, `ft[60]`): same layer and position. Only the timing model is old.
3. **Where the mismatch comes from.** In the plan, the hard-core entry of `ot_s81hd_he_epc` takes `lef` from `plan_of_record/l48hp1_h2/views/` and `lib` from `results/head_he_epc_h2_1110/`. It is the only one of 13 lef/lib pairs in the HEAD plan that mixes two directories.
4. **The two models differ by about 240 ps on the inputs.** `in_data[441]`: setup arc +1.9 ps old, -243.9 ps signed; hold arc about +117 old, +288 to +311 signed. Output arc `rr_lo[1]`: 580 ps signed.
5. **The core has no large internal skew.** Its 11,587 flops get the clock 399 to 488 ps after the pin (median 425); the signed record says `ck_spread_ps` 88. The input flops are not early.
6. **Re-time with the signed models** (TYPE-HDEPC, `type-hdepc/retime/`): TT setup -173.45 ps on 221 endpoints (was -395.27 on 564). FF hold unchanged at -10.24 on 179.
7. **My STA read on the same database with the signed models** (slack per `u_epc` pin, `epc_pins_tt.tsv`):

| group | pins | worst TT setup | below -42 ps |
|---|---|---|---|
| `in_data` (from the nine head SRAM banks) | 552 | -173 | 97 |
| `in_valid` / `in_ready` | 2 | -77 / -62 | 2 |
| `out_data` | 552 | -85 | 2 |
| all other inputs (`f_rx`, `r_rx`, reset) | 651 | +341 | 0 |
| all other outputs | 682 | +90 | 0 |

   Hold at the core pins: inputs +89 TT / +45 FF, outputs +68 / +40.

8. **A clock shift cannot close it.** Moving the `u_epc` clock later by x gives the inputs x and takes x from the outputs and from input hold. At +130 ps: input setup -43, but output setup -215 on 55 pins and input hold -41 on 211 pins.
9. **The failing inputs are one bus, and the failure follows distance.**

| head bank | stack at y | `in_data` pins at die x | worst slack | below -42 |
|---|---|---|---|---|
| 0-2 | 104-138 | 539-574 | +11 / -33 / -28 | 0 |
| 3-4 | 207-242 | 574-597 | +4 / -24 | 0 |
| 5 | 242 | 597-608 | -74 | 4 |
| 6-8 | 311-363 | 609-639 | -173 / -126 / -165 | 93 |

   Worst path: SRAM clock at 442 ps, read delay 250 ps, three gates 123 ps, then nine buffers and 456 ps of wire to the pin. Bank 6 sits at (302-334, 311); its pins are on the south face of `u_epc` at (619, 60). That is 561 um with no detour, 0.81 ps per um.

### 1.3 Why the earlier Fable note was wrong

- It read a setup arc of -81 ps as "the input flops sit 100 ps behind the clock pin". A setup arc of a block model is input data delay plus flop setup minus clock delay. With the clock at 425-488 ps, -81 means 340 ps of input delay in the old build (hold buffers); the signed build has about 150 ps.
- So the "320 ps skew between input and output flops" does not exist, and the tap tool was right: pin 42 + internal 421 = 464 against a 450 target puts the core's flops level with the parent's.
- Its fix 1 ("set the tap to L = 330-400 ps") must not be used. With the signed model, L = 350 gives output setup -435 ps on 509 pins and input hold -261 ps on 824 pins (item 8).
- The DRC part of that note (64 violations where every twelfth M6 pin meets a parent PG stripe) stands. PG-AWARE-1's face cut answers it.

### 1.4 Root cause

Two causes, in this order:

1. The parent was placed, repaired and signed against a model 240 ps too hard on 1,209 inputs. The repair step saw -395 ps and could not work on the real paths.
2. With the right model the head-FIFO read path is still about a cycle long: 250 ps SRAM read + 123 ps logic + 456 ps wire + about 150 ps inside the core. The top SRAM stack feeds the pins farthest east on the south face.

### 1.5 Fix

1. **H1, now.** Point the plan entry at the signed views (TT f663e343, FF 1016d15f) and regenerate hd_host_e only. Add one prepare-time check: `lef` and `lib` of a hard core come from the same signed record. Expected: at worst -173 ps; better is likely, because the repair step sees real slack for the first time (INFERENCE).
2. **H2, same plan event.** Budget: wire delay must drop from 456 to at most 325 ps for -42, so every head bank within about 400 um of its pin group (350 um for 0). Banks 5-8 are at 480-560 um. Move the top stack (banks 6-8) and bank 5 at least 160 um nearer the south face. Core shape and pins do not change.
3. **If the move does not fit:** a register slice on `in_data` / `in_valid` / `in_ready` at the south face of `u_epc` (one cycle, with a skid for the ready path). It also clears the two `out_data` pins only if those share the handshake; check them after H1.

### 1.6 rp21z20N (HEAD-REMAP-1)

Plan: epyc7 `/srv/opentallas-scratch2/claude/head-remap-1/rp21z20N.json`.

Sound:
- (a) hd_mesh SRAM pair moves and (b) hd_lep0N rows are translations; the delta script checks overlap and outline; prepare passes its procedure check; landing re-map rewrote 5 relay names.
- No `u_epc` tap change: correct (item 8).
- Reset pins are off the M6 PG pairs: hd_host_e `rst_start_raw_0` y 552.96 and `raw_2` y 17.28 are 2.16 um from a pair centre; hd_spn_end `raw_5` y 886.056 is 1.70 um away.
- `OT_PG_FACE_CUT=1` for hd_host_e.

Not sound:
- The generated kit `kits21z20N/g_hd_host_e` still carries the old model (TT 8aad8716, FF 708050bc). A build from it repeats the false -395 ps.
- Nothing in z20N shortens the head SRAM path. hd_host_e will not close on z20N as it stands.
- G0 was run on z19 only (628 errors baseline); I found no G0 result for z20N.

## 2. KV: why 5 of 56 types sign with 34 of 34 cores signed

The cores are not the problem. The types fail in how they hold the cores and the rings. Signed: kv3_io_ft, kv3_phy, kv3_phy_v1, kv3_sys_SD, kv3_sys_SD_v1. The "timing after route" (kv3_phy_v1) and "re-sign" rows in the failure breakdown are old wave rows on types already signed.

| class | types | which | where it stops |
|---|---|---|---|
| A. soft landing rings: band does not fit, then oversize placement | 30 | pv x16; hg_v1, hg_v1p2..p6, hg_v3; hgi_v6/v7/v8; hub_Wo/Ei/Eo/C | placement (OT_CLAND band, GPL-1010) |
| B. GRT overflow in zero-capacity gcells over the head cores | 9 | hgi, hgi_v1 x2, hgi_v2 x2, hgi_v3/v4/v5, hg | GRT-0116, or GRT-0115 then EST-0005 |
| C. core tap / cross-tap hold | 10 | pc x2, pc_v1 x3, pc_v3; io_ft_v1, io_cor, io_cor_v1, hroot | hold gate, DRT-0255 |
| D. macro clock pin on the wrong tap | 1 | sys_c | GRT hold |
| E. kit RTL error on an old event | 1 | hub_Wi | kit RTL |

MEASURED: of 42 kvgeom5 items on the run hosts, 36 have no flow log yet. "Running 44" is mostly kits waiting for memory.

### K1. Soft landing rings (30 types)

- Not re-measured here. The wave failure signatures match causes 1 and 2 of FABLE-TYPES-KV.
- Fix: hard ring masters in kvgeom7, plus the KIT-OPS-6 band bridge and STB-EDGE-1.

### K2. hgi / hg overflow (9 types): router accounting plus a flow fault, not channel capacity

MEASURED on intel1 `/srv/opentallas-scratch2/claude/kv-hgi-refloor/fh/{A,C}/kit` (type kv3_hgi_v2__cl2862d491):
- Control C: overflow 1/4/624 at 6.65 % use. 43 congested gcells, 42 of them inside core boxes, each with capacity 0 and usage 1, 0.9 to 34 um inside a core edge.
- Form A (M7 closed over the 16 cores): 43 gcells drop to 1, at (193.8, 127.1).
- `kv3_head_eighth_e0.lef` has 16 clock and reset M5 pins within 2.7 um of the core centre, under full M1-M5 blockage. INFERENCE: the last gcell is that pin cluster.
- Both forms then stopped on `EST-0005 Run global_route before estimating parasitics`. The first parasitics estimate after global route worked; the one after "Repair antennas" failed. INFERENCE: the antenna-repair step drops the allow-congestion route state.

Fix:
1. Put the M7-over-core adjustment in the generator for hgi and hg.
2. Do not count a capacity-0 gcell that holds a macro pin as overflow.
3. Skip antenna repair on allow-congestion kits. ASAP7 has no diode cell and the step reported 0 violations.

Open: neither form has reached detail route.

### K3. kv3_pc (6 types): kvgeom6 is sound

- MEASURED (epyc2 `/srv/opentallas-scratch3/claude/type-kvpcf/cl5a95b461/kv3_pc__cl5a95b461`): tap insertion spread 372 ps (215 to 587, target 250); all 8 core clock pins are outside the window. Early core taps answer exactly this.
- kvgeom6 aligns `qkd_kvs_pcc` on its largest internal clock delay (312 ps). That is the right reference: it puts the core's flops level with the parent's. HEAD section 1 measured the same rule on `u_epc` and found it correct.
- INFERENCE (arithmetic from the model, no STA): at FF the core tree is about 237 ps and the fastest output leaves 269 ps after the pin, so outputs reach a directly connected parent flop about 32 ps after its clock edge. FF hold on `u_kvpc*` outputs is thin but not negative by design. Read those endpoints in the canary.
- Do not move the pcc tap to an arc-derived value. That is the reasoning withdrawn in section 1.3.
- Not checked: that the kv3_pc kits carry the signed pcc/pcf timing models (the HEAD H1 fault). KV-102 should compare the hashes once.

### K4. io_ft_v1, io_cor x2, hroot (4 types) and sys_c (1)

- Cross-tap ring read pair; the tap pair affinity for io_cor and hroot arrives only in kvgeom7. Not re-measured.
- sys_c: macro clock pin 951 um from its tap; the KV-102 macro-pin guard is in progress. Not re-measured.

## 3. QC: classes that recur unchanged across attempts

Sources: 413 failed wave rows, 165 attempt directories with N >= 3 on the six run hosts, four kits opened by hand. cbn/cbx/cbf left out.

| # | class | types | evidence that it recurs | representative kit |
|---|---|---|---|---|
| Q1 | DRT-0255 maze route | 13: coll_n, coll_ucie, sle_fe_v3, sle_fw_v2 cl69, sle_hc0 cl4baa, sle_hc2 clf60c, sle_st_b_v2 x3, slw_st_b_v1, sle_stm_v2/v3, slw_hc0, slw_hc2 cldc, sle_su_l1 clc6 | same net and same route box on different hosts: coll_ucie a7/a8 `net309`; slw_hc2 a4/a5 `u_ist_cw_n2_0/net28212` | intel1 `s29q103S2/items/coll_ucie/attempt_8` |
| Q2 | DRT-0206 open net | 11: fw_v1/v2 x6, sc_v1/v2/v3 x4, slw_stm_v3, sle_fe_v1 | 15 kits; every open net is a `strap_ca_k_*` pin | epyc8 `s29q103S/items/sle_fw_v2__cl6740750e/attempt_9` |
| Q3 | hold stall at GRT (and RSZ-0060 buffer limit) | 8: sle_fw_v1 cl9d, sle_stm_v1 cl277, slw_fe_v1, slw_fe_v2, slw_hc3, slw_stm_v1 cl2086, slw_stm_v2, sle_st_b_v1 pv | identical numbers per attempt: fw_v1 a7/a8 -41.29 ps on 6,198 endpoints; fe_v2 a6/a7 -41.05 on 5,973 | epyc8 `s29q103S/items/sle_fw_v1__cl9d029624/attempt_8` |
| Q4 | su_l0 routed with 3 DRC | 5 | 3 violations on all 9 routed builds (a3-a7) | intel1 `s29q103S2/items/slw_su_l0__cl76fb247e/attempt_6` |
| Q5 | su_c | 3 | DRT-0073 no access on `u_va/ck` (qfd_dv_s8x_vmr) on two types; FF hold -397 ps on 5,349 endpoints on cl19bb | epyc10 `s29q102B0/items/sle_su_c/attempt_6` |
| Q6 | hc1 GRT-0116 | 3 | slw_hc1 cle683 a5 again | epyc10 `s29q103S/items/slw_hc1__cl68f9248e__cle683a076/attempt_5` |
| Q7 | cell count over 517k | 2 | slw_fw_v1 clc7 517,349; slw_sc_v1 cl459 519,572 | epyc10 |

Host noise, not design: exit 143, orphaned jobs, Error 241 (about 12 rows on 11-14).

**The three largest classes (32 types) are in no plan in flight.** S4a and S4b fix fw and stm setup distance (-236 to -446 ps at GRT). That is real, but the same types stop earlier on Q2 and Q3, so a regeneration on S4 without those two fixes ends the same way.

Root cause and fix:

- **Q1 (INFERENCE, mechanism taken from FABLE-HARD-QCHEAD section 5; only the determinism was re-confirmed).** Routes pushed into the row of an M6 PG pair. The QC kits of B0/S carry no `OT_PG_TRACK_TRUTH`. Fix: the PG-AWARE-1 hook in the QC source, then regenerate. Its slw_hc2 and coll_n proofs are still in GRT; those two decide whether the hook is enough.
- **Q2 (MEASURED).** Interior M5 ID-strap pins, 0.024 x 0.768, sit at x = 4.32k; M5 tracks are at 0.048k + 0.024. That is half a pitch off. Each kit prints 90 to 110 DRT-0421 warnings; the 1 to 6 straps that feed a real buffer end as open nets.
  - The snap already applied does not reach running kits. slw_fw_v3 a6: the epyc8 copy of `io.tcl` is snapped (311.064); the epyc7 copy that ran route is not (311.040). Kits past floorplan keep the old pins in the database.
  - Fix: snap in the generator and regenerate fw/sc/stm/fe from floorplan. No snapped kit has reached detail route; check the first for zero DRT-0421 on straps.
- **Q3 (MEASURED).** The pre-GRT hold repair result is thrown away by its own accept test ("no hold gain" / "TT setup loss" still printed in S2 kits). Fix: score the accept test on core-owned paths only, without the placement-estimate setup term.
- **Q4.** `cland_tstart_in` over a PG pair. S3R3b answers it (5 types).
- **Q5.** S4c fixes only the slw_su_c cl19bb tap. The `vmr` clock-pin access is a core-view fault on all three su_c types and is in no plan. Owner QC-CORES-HEAD.
- **Q6.** Real overflow, in no plan. Needs outline or channel growth in the next event. Owner DIE-QC-103.
- **Q7 (INFERENCE).** Old relay-bay inflation; clears on regeneration.

## 4. Stop list

HEAD
- Any `u_epc` tap shift (L = 330-400 or other). No shift closes it.
- A "fix inside the core" lane for HE-EPC. The core is fine.
- Building hd_host_e from `kits21z20N` before the model reference is corrected.
- More DRT-0255 forms of hd_host_e as a timing answer.

KV
- Unchanged relaunches of the 30 soft-ring types before the hard-ring bind or the band bridge.
- hgi column re-floor, M9, density forms, more congestion iterations: the overflow is zero-capacity gcells over cores.
- Allow-congestion forms that still run antenna repair: they stop on EST-0005.
- Moving the pcc tap off the internal-delay reference.
- Late ECO on port-start hold (kv3_phy_v1: FF -204 to -0.5 while TT went -34 to -248).

QC
- Unchanged retries of any kit in Q1-Q3; the result is the same on every host.
- In-place `io.tcl` snaps on kits past floorplan.
- Late ECO on su_l0 databases.
- Density or seed forms for DRT-0255.
- Waiting on S4 to cure fw/sc/stm kits.

## 5. Evidence and limits

- My STA read: epyc2 `/srv/opentallas-scratch2/claude/fable-pd-hkq/` (`epcbud.tcl`, `epc_pins_tt.tsv`, `epc_pins_ff.tsv`), log intel2 `~/tmp/fable_pd_hkq_epcbud.log`.
- TYPE-HDEPC: epyc2 `/srv/opentallas-scratch2/claude/type-hdepc/{diag,retime}`.
- Not done: a rebuild of hd_host_e with the signed model; a placement proof of the head SRAM move; an STA run for the kv3_pc tap; a detail-route verdict on hgi form A.
- Not re-measured, taken from earlier notes: KV classes A, C (io/hroot) and D; the QC Q1 mechanism.
- Side effect of this review: `tools/failure_breakdown.py` was run once on the hub (22:04) and regenerated the automatic FAILURES section of `RELEASE_TREE.md` and `lanes/STALE.tsv`. Both were left uncommitted.
