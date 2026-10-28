# QC activity continuation 2026-10-28

Production counters are building. No physical PG adoption or release gate is claimed.

Actual signed SU8 rst3_k0/hold_b on intel1 supplies 6_final.odb, 6_final.sdc and extracted 6_final.spef.
OpenSTA uses the retained 833 ps clock, propagated clock and RVT TT libraries.

| activity | power W | scope |
|---|---:|---|
| current routed vectorless | 0.03024517 | assumed activity |
| existing 12,001-cycle randomized unit stress | 0.02238182 | measured toggles, incomplete mapping |
| free-running clock, zero data transitions | 0.01226238 | clock-floor sensitivity |

Stress simulation passes SU8_EQ; 4359/4655 FFs and 488/488 data inputs match activity names. Other 296 FFs retain
activity 0.5, an assumption rather than proven upper bound. Every annotated signal uses duty 0.5. Combinational
activity propagates. OT_REG_MATCHED_MEAN 0.5 in the inherited-style log is mislabeled: this field prints the unmatched
default, not the actual mean of matched FF rates. The randomized control/fault bench is not production activity.

su8_superpose.py reuses qc-pg-map-1027 class CSV responses, scaling SU8 alone and retaining all other signed powers
and the old 6.602 mV below-M7 allowance. Old 50.426 mV total is reproduced. At background 0.5823 W/mm2, current
vectorless gives47.454 mV, stress40.690 mV, clock-floor31.984 mV. All are INFO uniform-current-per-core estimates.
Total power cannot reproduce activity-dependent in-core current placement; below-M7 was not scaled.
Existing75-um/37.5-pad case remains23.972 mV on its old assumptions. Production data are needed to choose150 um.
A0 and flattened-logic background remain unresolved.

Production QCLM source is epyc2:tok-qk-qclm-r2 (259/259 inherited cases, source262d07038). Its .o/.a were pruned,
so an own C++ rebuild reuses immutable generated sources through read-only links and adds a counter driver.
No original source/build file is edited. v2 captures402 retained SU8 state/alias signals (6809bits) in W5 slice0.
Signed-core source differs from this production source: delivered synchronous reset, removed constant lane0 FFs,
and same-edge shared input capture instead of duplicate per-lane pin FFs. Only matching signal activity will map;
unmatched physical cells remain explicit sensitivities. No full-parent equivalence is inferred.

Original power script failed literal-newline Tcl syntax before annotation; retained intel1 su8_power. Corrected
su8_power_v2 is archived here. First compile launch raced preparation and exited127 (qclm_build.otrun.log);
corrected qclm_build_ready.otrun.log records the actual admitted job.
