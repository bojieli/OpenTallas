# S81 cores handoff on explicit ROOT reset, 2026-10-29 14:02 PDT

Prior park was revoked at 13:55. This takeover collected inherited results and
created a new own worktree from current main fb1fc79593. No new heavy jobs,
physical runs, RTL edits, tool fixes or merges were launched by this lane.
Stopped engineering immediately on explicit ROOT reset relayed by S81 lead.

Own branch: codex/s81-cores-1355-1029, worktree
/srv/opentallas-scratch/claude/wt/codex-s81-cores-1355. The results commit holds
this collection packet, the original H0 failure receipt and a read-only copy of
paused DIE-S81-29 core_family_slice.py for continuity. That inherited partial
VSW tool candidate is NOT qualified/READY and was never installed as a tool.
No OWNER? decisions were added.

## Results collected

H0 actual hold ECO finished on intel2:
/srv/opentallas-scratch2/claude/die-s81-28-h0/h0_holdeco_b10
(original unit oth-ubuntu-2830300-1793304171). rc.txt route_finish_rc=0,
clk_freeze_check_rc=0. Final signoff/signoff.json is NOT SIGNED:
- TT setup +8.97 ps, FF hold +1.75 ps, no timing violators.
- DRC0, antenna0, DRV0, PG open0. Clock geometry unchanged on1064 nets.
- Actual related-pair skew 62.65 TT / 62.69 FF ps, below80.
- Blocking measurement defect: TT min pair path/arrival check14.899 ps,
  FF7.917 ps (fall-edge launch measured as rise); plus required real-parent
  io_hold receipt missing. No other sign-off failures.
FLOW supplied merged/merging fix12e5221e2 (nine tests PASS, old H0 probe
14.746/7.792 ->0/0). No corrected probe was started on this new ECO geometry.

BF hints+KEEP_XPOS LEC terminal EQUIVALENT,61663/61663 proved,0diff/0undecided,
1709KEEP=1708retained+1provenconstant,0missing. intel1:
/srv/opentallas-scratch2/claude/die-s81-25/lecx/lec_x64/lec.json
chain.status synth rc0,lec rc0 (finished11:35). This is current exactness
progress; it is not physical closure.

ve_s centre-entry PLACE completed, full source LEC EQUIVALENT45122/45122:
intel2:/srv/opentallas-scratch2/claude/die-s81-27/ce/kits/ot_s81sl_ve_s_ce27m
(original unit1225179). Actual 3_place.odb exists; design area20995um2,
40% utilization. No actual geometry review was run by this takeover.
Existing ready geometry check input:
intel2:/srv/opentallas-scratch2/claude/die-s81-27/ce/geom/ve_s/check.json

## Inherited live job

ROM64 corrected LEC still LIVE on intel1 as docker ds81-26-rom64 (over3h at
collection), untouched:
/srv/opentallas-scratch2/claude/die-s81-26/rom64
run.status only start11:16; no lec_x64/lec.json yet. Collect that receipt and
counts; do not duplicate. Earlier277-difference failure is preserved in the
prior vehicle. The newer run uses33 induction-proved hints for constant
w_cgt[0] and q0_wf merge correspondence.

## Failures diagnosed / concrete next steps

BF TAG16 chains BOTH stopped before physical build:
epyc2:/srv/opentallas-scratch2/claude/die-s81-26/bf
chain_t16a.status and chain_t16b.status end FAIL kit_apply. Exact error in
plan_t16{a,b}/kit_apply.log: slice outline[450.144,198.72] differs from actual
kit[450.168,198.72]. Restore exact nominal source outline in conversion;
never relax the interface comparison. Both model plans also failed their
window target: t16a TT46.37/FF37.58, mean433.69/323.32; t16b TT43.42/FF36.26,
mean325.64/242.97. New-sink clock replanning remains needed. No new t16 build
was launched.

VSW DIE-S81-29 candidate terminal model FAIL, no new P&R:
intel2:/srv/opentallas-scratch2/claude/die-s81-29/vsw/work2/ot_s81sl_vsw
checks.json TTmean256.26/window22.05, FFmean191.77/window19.38;13199/13199
sinks,0missing/dup/extra, two macro leaves. Two legs still exceed1.10x
Manhattan, worst1.922. plan.json keepout_hub_slid={} despite opt-in true;
converter refuses unequal-count model TT FAIL. run2.log/d1.log retained.
Paused candidate source at wt/die-s81-29/tools/die_plan/core_family_slice.py
adds family macro_d1 opt-in and keepout_hub leaf-only movement. Own read-only
copy exists under results/codex_s81_cores_1355_1029/inherited/. Investigate why
the two bad legs are not moved and finish opt-in d1/default-unchanged tests,
then review before a new VSW build. Do not count this as a qualified patch.

rxsf accepted setup-repair margin25 successor is NOT STARTED by this takeover.
Actual baseline kit is nested under the path in prior notes:
epyc2:/srv/opentallas-scratch2/claude/die-s81-25-cores/rxsf_lh1/dsfd_su_t_rxsf_ce12c
(its parent directory has no run_kit.sh). Baseline routed TT-17.44/52 endpoints
was diagnosed by DIE-S81-28: undersized BUFx2/OA22 broadcast drivers, real
RC loss after GRT margin0, not arithmetic depth. Next is the approved fresh
route with setup repair margin25, preserving source/hints/reset64; image
reference epyc2 die-s81-26/geom/rxsf/auto_geom.png plus GEOM-59. No blind ECO
or changed clock.

H0 clock-only correction procedure from FLOW /root/flow_clock:
copy intel2:/srv/opentallas-scratch2/claude/flow-clock-r4-pairskew/run.sh into
an OWN probe dir; set K to actual h0_holdeco_b10 above, D=own dir, stage merged
pair_skew.tcl in D/ps_fix. Source prefix from actual signoff/{tt,ff}/session.tcl
through PAIR_DONE, retaining the exact libs/SDC/6_final ODB/SPEF. Update all
base mounts to this actual ECO kit. Run via ot-run16GB1thread after original
STA ends; original STA ended during this takeover. Require fresh fix/rc.txt0
and H*_verify0/0. Preserve original signoff JSON. Full parent receipt remains
needed even after the measurement correction; do not claim SIGNED.

Station status FACE_GUARD/shared collector work belongs to parent S81 lead,
not this child. No station source/job was touched by this takeover.
