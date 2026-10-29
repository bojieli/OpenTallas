# DIE-QC-34 / A0 (sub-agent DIE-QC-34-A0), 2026-10-29

Base: `claude/die-qc-33-a0rst-1029@58ecae91a94` (ICG_RRST relay RTL on Codex 68204ac61). Results only; no RTL change here.
Scratch root: `intel2:/srv/opentallas-scratch2/claude/die-qc34-a0`. AUTO-GEOM = origin/main `tools/autopilot` geom tools (byte-identical copy, main c0c65228405).

## 1. NK place, ICG=2 + ICG_RRST=1 + DIE-QC-33 graph homes (kit `qfd_tile_nk_a0c_a0nk14icg2rr1`)
- Kit = copy of the r2 probe kit; RTL `qfd_tile_nk_a0c.sv` from 58ecae91a94 + `rtl/lib/ot_rst_relay.sv`; config `VERILOG_TOP_PARAMS ... ICG 2 ICG_RRST 1`. Fresh synth (unit oth-ubuntu-1658071), place (unit oth-ubuntu-1737626, exit 0, GPL `-overflow 0.21` 1020 s, DPL legal, no DPL-0033).
- Homes: the 12,811 DIE-QC-33 graph homes (all names present in the new netlist, 0 missing) + 3 relay FFs: `sync_q[0]` (449,663) E column at the rst_n pin, `sync_q[1]` (320,663) and relay `rst_n` (225,690) in the y~663 H-street / x 193-321 opening, toward the hop/dr cluster. `GRAPH_HOMES placed 12814 cells FIRM`.
- AUTO-GEOM on 3_place.odb (`nk/auto_geom.json`, PNG `nk/auto_geom.png` VIEWED) CHECKED:

| item | r2 probe (raw rst_n) | **rr1 (ICG_RRST=1)** |
|---|---|---|
| r2r captures > 405 / max | 0 / 402.95 | **0 / 401.65** |
| relay_collapse | 0 | **0** |
| pin_reg_max (p90) | 139.83 (8.17) | **13.77 (8.17)** |
| rst_n direct flop loads (`nk/rstn_census.json`) | 73, max 358.45, 72 > 150 | **4** (sync_q[0] 13.77, native entry 141.66, sync_q[1] 144.94, relay async clear 251.77) |
| ICG enable legs (`nk/icg_reach.json`, 36 ICG / 104 legs) | max 395.55 | **max 395.60, 0 > 405** |
| remaining FAIL | aspect 2.528, partial_face 2, channel_h 0.8 / v 1.72 / col_v 1.91, clock_reach 748.53 | aspect 2.528, partial_face 2, channel_h 0.8 / v 1.725 / col_v 1.908, clock_reach 748.37 |

- The raw-rst_n class is resolved: rst_n now drives only the relay (2 sync + relay async clear) + the native reset sample; the one leg > 150 is the relay's async clear (251.77 um, < 405, inherent to the ot_rst_relay form; release is synchronous).
- Remaining FAILs are the same floorplan/CTS classes GEOM-59 accepted for the r2 probe (aspect / partial_face / channel = V1L parent plan items; clock_reach = CTS item). The K=0 enable paths (go/n_b_q -> node/fa2/fa3/ck ICG, ~395 um) are geometry-legal; their ~590 ps enable timing is UNCHECKED until CTS/STA.

## 2. NL re-place, ICG=2 + ICG_RRST=1 + graph homes (final kit `qfd_tile_nl_a0c_a0nl14icg2rr2`)
- Kit = copy of Codex `qfd_tile_nl_a0c_a0nl14icg2r1` with RTL from 58ecae91a94 + `ot_rst_relay.sv`, `ICG 2 ICG_RRST 1`, and the post-GPL `apply_anchor_targets.tcl` (NL reset6) line **removed**; graph homes FIRM pre-GPL via `graph_homes.tcl` (`nl/nl_graph_homes.tsv`, same kit_istations pattern as NK), released to PLACED for DPL. Fresh synth (unit oth-ubuntu-1686654).
- Homes = DIE-QC-33 `solve.py` (iteration cap x10, `solve_big.py`), RT 395, reset entry 140, **without `nogap`** (with `nogap` the solve does not converge on NL: 25 legs > 405, max 431.29, s2_round -> TX relays).
- rr1 (homes solved on the failed r1 DPL geometry): DPL legal, but AUTO-GEOM r2r FAIL 44 > 405, max 528.07 (`nl/rr1_auto_geom_FAIL.*`): all `u_logic.t_out[*] -> u_g.t_out[*]` face flops. Cause: in the r1 geometry the t_out face flops sat at reset6 anchor positions (e.g. t_out[512] y 863), not at their pins (y 999); the solve held them fixed at the wrong place. Kept as a failed verdict.
- rr2 = homes re-solved on the rr1 placed geometry (true face positions + the real ICG_RRST netlist): converged in 2,159 iterations, analytic r2r 0 > 405 (max 395.00), 469 cells moved (max 158.7). Place unit oth-ubuntu-2493083 exit 0: GPL 817 s, **DPL legal, no DPL-0033** (max displacement 63.1, HPWL 1.829e6).
- AUTO-GEOM on rr2 3_place.odb (`nl/auto_geom.json`, PNG VIEWED) CHECKED:

| item | r1 (Codex unit 2306050, DPL-failed odb) | **rr2** |
|---|---|---|
| DPL | DPL-0033 (2 TX flops on PHY_EDGE taps, t_out[343] off-site) | **legal** |
| r2r captures > 405 / max | 8 / 410.02 (s2_x -> TX relay) | **0 / 400.03** (`nl/r2r_list.json`) |
| relay_collapse | 0 | **0** |
| pin_reg_max (p90) | 143.73 (8.95) | **15.07 (7.98)** |
| rst_n direct flop loads | 75 (ICG_RRST=0) | **4** (sync_q[0] 15.07, sync_q[1] 84.62, native entry, relay async clear 233.17) |
| ICG enable legs (34 ICG / 47 legs) | n/a | **max 365.69, 0 > 405** |
| channel_h / channel_v / col_v | 0.822 / 1.273 / 1.334 | **0.384 (ok)** / 1.637 / 1.897 |
| remaining FAIL | | aspect 2.528, partial_face 2, channel_v 1.637, col_v 1.897, clock_reach 763.38 |

## 3. A0 native proof: contract monitors (bench `proof/tb_a0_icg.sv`)
- Vehicle: the Codex native REGROOT3/ICG2 selected source (same pinned `files.txt` and ROM images as `codex/qc-proof-0831` native_{nl,nk}, ICG_RRST=0), rebuilt with this bench (verilator 5.050, units oth-ubuntu-1878900 NL / 1878897 NK).
- Why stimulus alone cannot catch them: Codex/QC-A0-KITS-13 show mutant 8 is output-identical to the design even bit-for-bit strict (NL strict 6865 = mut0, NK 6956 = mut0); the first ROM read after a wake comes later than the structural 3-stage path, so K_RP = 3 never misses a needed edge under any go-driven wake. The NL tile has no n_a/n_b faces (`nv_act = 1'b0`), so there is no NL n path to drive; NL mutant 3 survives functionally because the K = 2 relayed fa2/tx/lsl gates cover the NL tail. Both are equivalent mutants for this RTL + stimulus.
- Added (TB_CONTRACT, ICG=2): **LEAD** = every hop gate enable is open s_e - 1 cycles after each rise of the tile en (s_e from the measured entry depths: ck 1, rp 3, rq 4, tx 5, lsl 7, fa2 NL 5 / NK 1, fa3/node 1); **DRAIN** = tile en stays 1 for the ICG_DRAIN window after the last act. These are the bounds the B-hop safety argument rests on, checked every cycle on the gated twin.
- v1 results (`proof/controls_v1_{nl,nk}.tsv`, CHECKED from the run logs):

| mutant | NL functional | NL contract (lead/drain) | NK functional | NK contract (lead/drain) |
|---|---|---|---|---|
| 0 design | PASS | 0 / **2*** | PASS | 0 / **2*** |
| 9 en=1 control | (no verdict, gating 0) | 0 / 0 | (no verdict) | 0 / 0 |
| 7 every hop +1 | CAUGHT 4164 | 99 / 2* | CAUGHT 4165 | 154 / 2* |
| **8 ROM-pair hop +1** | PASS (equivalent) | **CAUGHT lead 90** | PASS (equivalent) | **CAUGHT lead 100** |
| **3 drain dropped** | PASS (equivalent) | **CAUGHT drain 640**, lead 8 | CAUGHT 5342 | lead 1058 / drain 1171 |
| 1 no lead | CAUGHT 4164 | 0 / 2* | CAUGHT 4164 | 0 / 2* |
| 2 ~me_idle | CAUGHT 10462 | 0 / 2* | CAUGHT 9834 | 0 / 2* |
| 5 reset term | PASS | drain 64 | CAUGHT 4999 | drain 64 |
| 6 go hold | PASS (equivalent) | 0 / 2* | PASS (equivalent) | 0 / 2* |

- \* v1 bench bug: the DRAIN bound was 1 cycle too strict at the two reset releases (cyc 7068/8766, both exactly 64 cycles after the last act; proof/verdict_lines_v1_nl.txt, _nk.txt): the async reset term is seen one posedge before a registered act, so dr reaches 0 at last_act + 64. So v1 mut0 is not clean. **v2 bench** (bound 63; mutant 3 still fails at +1) is building: units oth-ubuntu-3572039 (NL) / 3571939 (NK) -> `intel2:/srv/opentallas-scratch2/claude/die-qc34-a0/proof/native_{nl,nk}_v2/controls.tsv`. Expected: mut0 contract 0/0. UNCHECKED until collected.
- Verdict wording: mutant 8 (both tiles) and NL mutant 3 are caught by the **contract** monitors, not functionally; that is a structural proof of the bounds on this stimulus, not a demonstration that the bench reaches a failing data path.

## 4. DIE-QC-35 (A0): proof v2 collected -> contract-monitor proof gap CLOSED (COORD 11:19 ruling)
- v2 bench = committed `proof/tb_a0_icg.sv` (sha256 086d6548…, byte-identical to the intel2 build source); vehicle unchanged from v1 (Codex native REGROOT3/ICG2, same files/ROMs; only the bench line in `sources_v2_*.sha256` differs from v1). Verilator 5.050. Units oth-ubuntu-3572039 (NL) / 3571939 (NK), both exit 0. Evidence: `proof/controls_v2_{nl,nk}.tsv`, `proof/verdict_lines_v2_{nl,nk}.txt`, `proof/sources_v2_{nl,nk}.sha256` (all CHECKED, read from the run logs).

| mutant | NL functional | NL contract lead/drain | NK functional | NK contract lead/drain |
|---|---|---|---|---|
| 0 design | PASS | **0 / 0** | PASS | **0 / 0** |
| 9 en=1 control | no verdict (gating 0, ACTIVITY_MISSING) | 0 / 0 | no verdict | 0 / 0 |
| 7 every hop +1 | CAUGHT 4164 | 99 / 0 | CAUGHT 4165 | 154 / 0 |
| **8 ROM-pair hop +1** | PASS (equivalent) | **CAUGHT lead 90** | PASS (equivalent) | **CAUGHT lead 100** |
| **3 drain dropped** | PASS (equivalent) | **CAUGHT lead 8 / drain 630** | CAUGHT 5342 | 1058 / 1160 |
| 1 no lead | CAUGHT 4164 | 0 / 0 | CAUGHT 4164 | 0 / 0 |
| 2 ~me_idle | CAUGHT 10462 | 0 / 0 | CAUGHT 9834 | 0 / 0 |
| 5 reset term | PASS | drain 63 | CAUGHT 4999 | drain 63 |
| 6 go hold | PASS (equivalent) | 0 / 0 | PASS (equivalent) | 0 / 0 |

- mut0 clean on both tiles (the v1 2 false drain hits at the reset releases are gone); mut8 (NL+NK) and NL mut3 caught by the contract monitors; every mutant caught in v1 is still caught. mut6 (go hold) stays an equivalent mutant (functional and contract PASS, as in v1/QC-A0-KITS-13); it is not part of the ruled gap.
- **Monitor bounds (recorded per the COORD ruling):**
  - LEAD bound per entry = s_e - 1, with s_e = the measured minimum gated depth from `results/qc_a0_kits_13_1029/bhop/entry_depth.py` (README_bhop "Bound s", CHECKED): ck 1 -> 0, rp0..9 3 -> 2, rsw/rnw/dw/de/rs/rn 4 -> 3, tx0..7 5 -> 4, lsl0..7 7 -> 6, fa2 NL 5 -> 4 / NK 1 -> 0, NK fa3/node 1 -> 0. These are the measured bounds, not the RTL K values (K = 2/0), so a K that is legal but < s-1 passes and K = s fails.
  - DRAIN = en stays 1 for ICG_DRAIN - 1 = 63 cycles after the last act. ICG_DRAIN = 64 is the RTL parameter (`qfd_tile_n{k,l}_a0c.sv`); the -1 is the documented async-reset-term timing (seen one posedge before a registered act), not a fit to mut0: mut3 still fails (630/1160 hits) and mut5 is caught at exactly 63.
- With the COORD 11:19 ruling these close the mutant-8 / NL-mutant-3 proof gap for ICG=2 sign-off: catches are on the documented gate-timing contract (structural), not a demonstration that this stimulus reaches a failing data path.

## 5. DIE-QC-35 (A0): CTS on the GEOM-59 PASS-COND places (NO re-place) -> FAIL at the CTS hold gate, both tiles
- Places unchanged: NL rr2 3_place (unit oth-ubuntu-2493083, GEOM-59 11:19 PASS-COND), NK rr1 3_place (unit oth-ubuntu-1737626, GEOM-59 10:47 PASS-COND). `make -n cts` = do-4_1_cts + do-4_cts only (checked before launch). Launch scripts `cts35/{nl,nk}/*_cts.sh` = the place-script docker pattern + the run_kit.sh orfs_hold_mm patch step, ot-run --mem 16 on intel2.
- **FAIL 1 (flow, fixed):** ODB-0370 "disconnect term CLK of dont_touch instance ot_fconst_00001_ff" (cts35/*/cts_FAIL1_odb0370.tail.log). These kits have `insertion_balance` off, so gen_core_kit_qc.py never emitted its standard pre-CTS lift of dont_touch on the POST_SYNTH `ot_fcap_*/ot_fconst_*` flops (it lives only in hold_budget.tcl). Added that lift alone as PRE_CTS_TCL `fc_dt_lift_cts.tcl` (240 flops each; no repair/tap/clock change). Generator gap to fix in gen_core_kit_qc.py (emit the lift whenever core_face_post_synth runs).
- **FAIL 2 (design, retained):** units oth-ubuntu-3933575 (NL) / 3933580 (NK), exit 2, at the existing OT_HOLD_STRUCTURAL guard (no repair attempted, no 4_1_cts.odb). CHECKED from cts.log:

| | NL rr2 | NK rr1 |
|---|---|---|
| TT setup ws before / after CTS setup repair | -418.95 / **-223.55** (u_hop_ck/u_icg/ENA) | -621.97 / **-181.77** (u_hop_node/u_icg/ENA) |
| FF hold ws / failing endpoints | **-172.53 / 2370** | **-571.84 / 3082** |
| of which input port (vclk) -> pin/face register | 528, worst -172.53 (tap->ot_fcap) | 1556, worst -571.84 (tap->ot_fcap; n_a/n_b_q 514+514) |
| of which internal clk->clk | 1842, worst -102.96 (2 < -100) | 1526, worst -129.31 (37 < -100) |
| kit FF vclk frame (vclk_ff.sdc) | 601.9 (declared 692.6/601.9) | 202.5 (12.3 common 250/202.5) |
| FF clock latency min .. max (report_clock_latency, diag) | 300.01 (romleaf clk pin) .. 808.55 | 416.74 (node clk pin) .. 801.16 |
| fcap root-sink clock arrival (FF) | 749.91 | 750.96 |

- Diagnosis (diag only on copies, `cts35/run_diag.sh` + `diag_append.tcl`, docker 12 GB cap; kit evidence untouched; full dumps hashed in `hold_fail_full.sha256`, worst 60 + classes committed):
  1. TritonCTS (`-delay_buffer_derate 1.0`) put a serial chain of BUFx24 `delaybuf_*` (16.7 ps each FF; NL 31 stages ~520 ps ahead of the hop ICGs, ICG GCLK at 531-560 ps; NK 21 stages to 367 ps on the fcap path, fcap CLK 750.96) on the root to balance the ungated root sinks and hop ICGs against the deepest branch. Root/face sinks then sit at ~750 ps FF, so the input-port hold (frame 601.9 NL / 202.5 NK) fails by -172 / -572. The kit frame and the realized insertion disagree in both tiles (NK by the whole 12.3 early-tap amount).
  2. Internal hold = zero-logic register pairs across SIBLING hop trees, each built separately: NL worst `g_tx.g_r[0].di[244]` (dw-hop tree, CLK 688.84) -> `u_tx/q[244]` (tx1-hop tree, CLK 801.14) through one INV = 112 ps skew, slack -102.96 (`cts35/nl/paths_hold_internal_latency.rpt`). Same class in NK (tap_q -> ib_i, -129.31).
  3. TT setup at the root/node hop ICG enable (-223.55 / -181.77) = early ICG clock pin vs late-clocked enable logic, the same depth imbalance (GEOM-59 asked for this number at 4_cts: it is this).
- No GRT (clock-incl GRT >= 50 needs 4_cts); the col_v (260,267) hotspot check is still open. Nothing was padded, trimmed or edited on the clock.
