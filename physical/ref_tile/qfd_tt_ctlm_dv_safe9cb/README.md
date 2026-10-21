# qfd_tt_ctlm_dv_safe9cb -- QW-TTC9 10-21: CALR successor (Q.STA.TTC.4) + structural fixes of the safe8u/8bu gate FAIL

Outline 777.6 x 604.8 (safe8bu). CTS: route.cts_sink sink_clustering false + -no_obstruction_aware. Parallel set: safe9c / safe9co / safe9cb (bind first to close, cancel the rest). Not critical.

## Netlist (CALR=1, F16WTN=1, TABLE_REL producer)
rtl/qwen_dv/lp9d_npl = QW-TLPROD lp9d_np (8349f4a11; native32 PASS, depth 718.5 ps / 24 lv, V5.050 tok_rel PASS,
norel/abs1/drop17 FAIL) with ONLY the landing-ring instance names restored (plus: sim-only ROM266 INSTANCE strings dropped -- ORFS reads the liberty macro; 1-bit ports declared scalar as in lp8_np) (results/rtl/qw_ttc9_1021/landing_names.py:
19,827 instances u_<idx> -> \u_lpl_<n>_<w|r>.u<idx>, 30 landings; exact construct replay namemap_lp9d.json.gz, replay RTL
byte-identical sha 5a54cf48). Connections, modules, parameters and order unchanged (sed back-substitution diff = 0 lines).
Macros: 6 p192 SRAM + 3 OPROM (unchanged) + 2 calendar ROM266 u_gi.u_cal.g_calrom.u_rom.m0/m1 at (475.2,388.8) /
(475.2,475.2) on ck_core (die ROM_BIND: results/rtl/qw_tlprod_1020/images/calr10/calendar_m0/m1.viamap.hex). Children:
h16c u_hr (closed, ck_pm0/ck_pm1 port list -- h16u 1r is submitted, not closed) + closed wtn u_gi.g_wtn.u_wtn at (648,388.8).
Region boxes: the NE ROM column x 453.6-615.6 joins core; hr keeps the u_hr box + NE strip x 615.6-775.44.

## safe8u/8bu FAIL -> fixes (gate logs /home/ubuntu/scratch/qw-ttc8/gate_safe8{u,bu}.log; results 7c879fa80)
1 cross_clock 8+38 (bu 17+55) failing ring->read endpoints, all u_lpl_<n>_w -> u_lpl_<n>_r (e.g. u_64254 = u_lpl_7_w,
  u_63564 = u_lpl_7_r): the ctlm7 record copy had no_data_multicycle because the bound netlist lost the names. Now the
  record copy (results/rtl/qw_ttc9_1021) drops it, the L5 contract binds: -setup 2 / -hold 3 ring->read (sample age
  1.25..2.75 T, priced +3 edges per landing since CTLM5). Reset hop core->hr stays single-cycle.
2 clock_rule pin-flop spread ck_core 217 / ck_hr 263 ps TT. Per-register dump of the safe8u CTS odb
  (results/rtl/qw_ttc9_1021/safe8u_ck_grid_tt.txt): ck_hr flops 500-530 ps everywhere except the S pin-band strip under
  u_hr (x 605: 640-752); ck_core S strip under the SRAM rows 935-1043 vs NE 810-850. Same signature as qkd_d2d_static
  (clustered pin-band leaves on long return wires) / s81 gather (obstruction-aware detours) -> unclustered H-tree
  (+ no obstruction-aware detour in 9co/9cb). If the spread stays > 80: ck_hr own entry / regional split (next).

## SAFE checklist (vs safe8u)
1 Pins PASS (landed record unchanged) | 2 Reach: ROM266 <= ~380 um from calendar glue, gate decides | 3 Fanout PASS
(lp9d native32 max 32) | 4 Depth 718.5 ps / 24 lv WARN (guidance, rule freeze) | 5 Storage PASS (+2 ROM macros) |
6 Floorplan: macro origins on the 43.2 lattice, ROM266 channels >= 23 um, fill ~51 % (9cb ~55 %) | 7 Clock: regional
ck_core / ck_hr with landed crossings (L5 now bound); CTS strip fix above | 8 Schedule static; CALR +76 edges/layer priced
(ledger claude/qw-tlprod-ledger-1020). GEN: table_req lane latency must equal the cmd lane.
Submit needs: spec benches (bench10 tok_rel PASS + norel/abs1/drop17 mutants, witnesses results/rtl/qw_tlprod_1020/witness).
