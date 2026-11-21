# CORE-LIB-LIMITS-1330 handoff (lever 1 of FABLE-CLOSURE-1315)

State (2026-11-20 ~14:30 PST):
- t60 trial: inputs copied to epyc10 /srv/opentallas-scratch2/claude/core-lib-limits-1330/t60kit (from epyc2 D8i 465cb9fe2d3 attempt_14);
  scripts /srv/opentallas-scratch2/claude/core-lib-limits-1330/tr/{run.sh,trial.tcl}; outputs tr/t60_base, tr/t60_slew (trial.log, TRIAL lines).
  run.sh KITGEN OUT MODE(base|slew) SLEW DP: reload 3_place.odb, repair_design -cap_margin 20 -slew_margin 50 (+set_max_transition), DPL, report.
- Flow fix (PLACE-SLEW) staged in lane clone epyc2 /srv/opentallas-scratch2/claude/core-lib-limits-1330/repo branch core-lib-limits-1330:
  gen_phys.place_max_transition (OT_PLACE_MAX_TRANSITION, RFLOW default 320 ps), gp_noconverge_gate.tcl set_max_transition on design
  before place repair_design, tools/die_plan/test_place_max_transition.py. 49 tests pass. Push only if the trial shows a gain.
- QC cbf_q01_s2 cause (V): OT_DLY_SPREAD (face_flops_release.tcl, pre-DPL, after place repair) moved the t_out stage, 3 wire bufs and
  INV 100-760 um onto the halo edges of core u_t12; last hop 902 um, 4.0 ns, no repair after. Probe: epyc10 tr/cbf/loc.txt.
  Proposed: route fallback must not cross a core, and repair_design on moved nets after DLY_SPREAD (owner dly_spread / KV-PLAN-R1).

## Final 2026-11-20 (lane done)
- t60 measured (no DPL): with limit, clk WNS -963.94 -> -288.05, TNS -47,016 -> -7,015, core pins >320 ps 950 -> 0; control unchanged. Logs epyc10 tr/t60_base2, tr/t60_slew2.
- PLACE-SLEW pushed main e7ebced0c4e (gen_phys.place_max_transition + gp_noconverge_gate.tcl + test_place_max_transition.py). Applies to new gens; running/bound kits unchanged.
- Open: (1) a legalized A/B through CTS on one regenerated kit (t60 or t57); (2) the dly_spread post-repair move class (cbf; 5,051 residual slew violations on t60 3_place) needs its owner; (3) optional: emit default_max_transition in ETM lib writers.

## Next steps (COORD, 11-20 ~14:50)
- DONE (1) DLY-REPAIR-1 pushed main f2e64e5d3b2 (dly_spread.tcl + test_dly_spread.py).
- (2) proofs on epyc10 /srv/opentallas-scratch2/claude/core-lib-limits-1330/proof/{t60,cbf}/gen: kit_fork of D8i t60 attempt_14 and QC R3 cbf attempt_3, main gp_noconverge_gate.tcl + dly_spread.tcl copied in, config line OT_PLACE_MAX_TRANSITION = 320. Launched from localhost: ot-run ... run_kit.sh KIT cts 32|48 8 (clients write scratchpad proof_*.out). Read run/reports/asap7/*/base/3_detailed_place.rpt and 4_cts reports; compare with the original kits (place WNS t60 -1123, cbf -1532).
- (3) When green: post to S81-DIE-R4 / QC-PLAN-R5 to relaunch held placed kits from place (leaf t57/t60/t72/t1/t56, kv_leaf t1/t4, QC cbf_q01_s2) on the new runtime; existing kits need the config line OT_PLACE_MAX_TRANSITION = 320 (or a regen) since kit_flow_refresh only swaps scripts.

## Status 11-20 late (after COORD/FABLE-CLOSURE-1515)
- main: e7ebced0c4e PLACE-SLEW; f2e64e5d3b2 DLY-REPAIR-1; 3098d89a951 hook on when unset; 25fc65d0cb1 gen default 320 on every die.
- The proofs moved to epyc7 (epyc10 admitted 0 GB): /srv/opentallas-scratch2/claude/core-lib-limits-1330/proof/{t60,cbf}/gen.
  t60: place WNS -1123 -> -393, CTS WNS -492.58 / TNS -23,006 (exit 0); worst = reset relay lpad_leafdn -> crr_vsw (class C).
  cbf: place WNS -1532 -> -299, clk -296, MACRO_CROSS 535 -> 0; CTS was running at handoff; worst = reset rrl_500 (RESET-RELAY-GEN-1530).
- Relaunch request posted to S81-DIE-R4 (leaf t57/t60/t72/t1/t56, kv_leaf t1/t4, from place). Per FABLE-CLOSURE-1515, QC cb kits are NOT relaunched for this lever.
- Open: read the cbf 4_cts_final.rpt when it lands; confirm the relaunched kits show the PLACE-SLEW line in 3_4.

- cbf CTS: WNS -212.61 (cland serdes_tx ring), clk -71.33, TNS -1,316, async +569. Lane done; open items: relaunches by S81-DIE-R4; lever 4 (class C reset/cland relay) for t60/t72/t56/t1.
