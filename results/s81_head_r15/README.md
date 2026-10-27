# HEAD-CORE-R15 (+ INFRA-FIRST-HEAD-5 duties) 2026-10-27: elemA SIGNED view, one HEAD infra delta, R15 mesh

Lane HEAD-CORE-R15 succeeds HEAD-CORE-R14 and INFRA-FIRST-HEAD-4 (both died). Branch claude/head-r15-1027 =
claude/infra-head4-1027@4b36bdd452 + merge claude/head-bind4-1027@be46fc3c20 + provider delta + merge
claude/head-core-r14-1027@61cf174279. Worktree intel2:/srv/opentallas-scratch2/claude/wt/head-r15-1027, scratch
intel2:/srv/opentallas-scratch2/claude/head-r15-1027. CHECKED = recomputed by me from raw files.

## 1. elemA_eco SIGNED view (results/physical/head_core_r15/elemA_eco_signed/)
Routed LEC (elemA_eco.lec_final) finished 05:50:45: EQUIVALENT 30203/30203, differ 0, kept 269/269 missing 0 (CHECKED lec.json).
Independent gate check (PROVENANCE.json): sign-off log newer than the run (CHECKED mtimes); DRC 0 / antenna 0 (CHECKED
5_2_route.json); slew/cap 0 TT+FF (CHECKED signoff.json + 6_report); own RCX insertion ft_mstrap_i -> 28723 register
CLK pins: TT 228.56 mean (211.07..242.31), FF 184.80 (169.36..201.19) (CHECKED, my OpenSTA run). TT is 1.44 ps under
the 12.3 design band (target, not gate, 12.3a); FF in band. Setup/hold/pair numbers are signoff.py values (UNCHECKED rerun).
flow_tag is null: this run is the R14 flow canary; the tag comes with its ROOT-MERGE.

## 2. One HEAD infra delta (physical/die_plan/s81_head/die_plan.json sha256 c218aebc530b...)
= R4 delta 5dbd7bdc (declared clock slots, C3 PG grid, VSS-lane straps, spine M9 columns)
+ HEAD-BIND-4 delta (ID straps strap_row0/strap_ten per hd_tile instance, hd_serdes bound via ot_s81hd_serdes_link + PMA pads)
  - the textual merge equals head_bind4_plan_delta.py re-applied to the R4 plan (CHECKED, dict equality)
+ provider delta (head_provider_plan_delta.py, COORD 10-26 22:21 HEAD-RTL-3 ASK1: "into the next single HEAD PLAN-DELTA"):
  hd_ctl -> ot_s81hd_ctl_core, hd_host -> ot_s81hd_host_ep_core, hd_mesh -> ot_s81hd_mesh_ep_core, hd_lep0N ->
  ot_s81hd_lep0N_noidx_core; h_tx/hd 276 -> 277; H4 tl/ca/cb lanes removed; 11-b head_lep_landing lane added.
Results: G0C PASS 0 errors / 6 warnings (g0c/); HEAD_DIE_PORTBIND PASS: module_missing 0 (was 4), DIE_PORT_BIND PASS
(326 inst, unbound/stub/undriven/multi 0, strap_ports 2), tie audit PASS 528, nested PASS 2217 instances (portbind.log).
Still open from HEAD-RTL-3 ASK2: mesh_ep_core copy-B overflow under a CRC replay burst (burst FIFO fix, separate lane).

## 3. Strap-variant LEC (strap_lec/summary.json)
The monolithic 264-instance run (intel2 hb4_lec/all, pid 3013060, 1,682,472 $equiv cells) proved ~8%/h; equiv_simple
cost grows with design size. Split into 33 chunks x 8 instances (tools/s81_head/head_strap_lec_chunks.py, same
modules and lec.ys): all 33 EQUIVALENT, 264/264 instances, 1,682,472 cells (= the monolithic count), 2.5 min wall.
Negative control mut_strap (strap_row0 of tE0o0 + 1): NOT EQUIVALENT, 4 unproven. CHECKED.
The monolithic run is now redundant (still running, not killed: COORD may stop it).

## 4. Mesh m5 (mesh_m5/) + master plan (master_plan_mp5/)
head_mesh_r3 --pg-lanes --spine-columns on the composed plan with the ACTUAL core clock entries of the real views
(ft_mstrap_i: elemA signed eco (162.00,163.44)/319.68, elemB hold2 (144.72,146.16)/285.12; CHECKED LEFs) instead of
the R3/R4 "edge pins" (293.58,317.576 / 0.042,257.58; those came from the old closed-element LEF clk pin, which the
real views no longer have). Stubs: elemA 1.92-2.16 um (was 43.38), elemB 2.54-4.66 um (was 34.6-38.7).
Unchanged: 1 mesh component, 147 straps (52 M8 + 95 M9 incl. 9 spine columns), 300/300 drivers on straps,
tree_on_islands PASS 1387 sites, nominal skew TT 2.58 / FF 6.41 ps (plan model, UNCHECKED). Renders viewed.
master_plan --declared-slots: same PASS/FAIL set as R4 (clock_sites, island_lattice, footless_stubs, lot_fit, reach PASS;
FAIL clock_shield (model gap, COORD: not blocking), clock_entry 5/5 (plan cores/*_pins.json still carry the old closed LEF
"clk" pin; the plan entry is (159.84,159.84) = R14 rebuild target), core_reach, core_insertion_model, tree_balance,
tree_commensurate, tree_on_islands (master_plan form), island_ft_inputs 5280 in-core). Not changed by this delta.

## Collect (not mine to duplicate)
- R14 symmetric rebuilds intel1 head-core-r14/elemA_rb_{m2,m12}: GRT hold repair (not setup): 15194 hold endpoints,
  WNS stuck -97.7 / -99.9 ps at u_m.g_pin.x_q[137] for >1 h while ~1 buffer/iteration is added (~6200 at 05:21),
  setup has 0 violations. Same pattern on elemB rebuild epyc2 head-core-r14/elemB_rb (-67.5 at x_q[240], 2690 bufs at 05:21).
  The stuck worst endpoint is an input pin register (input min delay -40 vs vclk 250 source latency); the signed
  eco flow fixes hold post-route with HB4 under the bound-ff contract instead.
- PG: NUMBER-CHECK-HEADPG lane (COORD 05:25); not rerun here.
