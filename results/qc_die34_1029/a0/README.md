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
