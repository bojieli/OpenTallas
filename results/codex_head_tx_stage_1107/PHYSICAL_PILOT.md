# First actual PLACE result and continuation
The changed RTL is cafcf5a50ce. No source change followed its proof.
Actual placed images were viewed by the lane and parent:
actual_place_review.png; native driver/capture coordinates in actual_targets.json.
Area18,565um2,35% utilization;117,755 physical instances,17,042FF,0macros.
Approximately15um-bin density max0.477,zero bins above0.7.
All seven new state anchors survived legalization. Native data legs43.8–90.2um;
control legs69.8–106.3um, replacing the old approximately170um shared control line.
First control reach exceeds the100um target by6.3um; this is an explicit residual.
Verdict PASS-COND for a CTS screen only, not timing/DRV/signoff closure.
Clock tree and GRT congestion are not measured at PLACE; PDN continuity is not
established by this cell view. Pins/outline are unchanged, no macro wall or dense
hotspot. Added PMA/fault output cycle remains private/unbound, DO_NOT_COUNT.

Use the real HARD-CORE recipe:
93c061c396c physical/die_plan/hbm_arch_cores/gen_core_kit_hbm.py stages
physical/die_plan/hbm_arch_cores/run_kit_hbm.sh and its matching core helpers.
Do not use generic gen_phys.RUN_KIT here: it is the partition/type recipe and
requires type budget.json. No fake budget was created and no checker bypassed.
Current runtime kit:
intel2:/srv/opentallas-scratch2/claude/codex-head-tx-stage-1107/kit/ot_s81hd_sc_tx_vC_stage_a5
The a5 controller (unit411970-1794065826) is waiting for its existing LEC,
independent guarded8GB unit459342-1794065900. No second physical phase launched.
If LEC is EQUIVALENT and PLACE exits cleanly before explicit takeover reset,
the parent authorized:
ot-run --mem8 --threads4 --dir KIT --stage KIT -- bash KIT/run_kit_hbm.sh KIT cts 8 4
Then view actual CTS clock/insertion/hold before GRT or detailed route.

Preserved pre-PLACE recoveries, all under kit/:
a1 missing current kit_contract helper (beforeYosys).
a2 staging filter omitted .sh runner (beforeYosys).
a3 synthesis stopped on four banned HAxp5 cells: restored existing current
ADDER_MAP_FILE=/work/adder_map_dontuse.v default; no new mapping code.
a4 clean synth/DONT_USE/SELRANGE PASS, then generic type port-bind demanded
budget.json. Corrected recipe selection, preserved all failures.
a5 independently copied clean a4 synth/results/objects, real current core
runner/helpers, reused synthesis, passed core guards and completed first PLACE.
No seed/density/clock retry, old routed ECO or deletion.
METHODOLOGY6.1 setup0/hold25ps at833ps applies; no clock relaxation.
