# Explicit Claude reset handoff, 2026-10-29 09:03 PDT

Stopped engineering immediately on ROOT's explicit reset relayed by S81 lead.
No processes were killed. No merge to main was performed by this lane.

Branch codex/s81-ce12-1029: source d2ba3ada8, proof1b43dd69c, estimatesf6d290b7e.
Includes parent-approved pin/sidecar source and narrow picks of reset staging
f30b48c15 + VSW full template42245eaec/36be60645. Main may already contain
these source candidates; use narrow picks, not the whole aggregate branch.

Six LIVE PLACE-only jobs on intel2, all 32GB/8threads, base
/srv/opentallas-scratch2/claude/codex-s81-ce12-1029/core_kits3:
- dsfd_su_t_rxsf_ce12c: client2878904, unitoth-ubuntu-2881333-1793289517
- ot_s81sl_ve_m_ce12c: client2878905, unitoth-ubuntu-2882436-1793289517
- ot_s81sl_ve_s_ce12c: client2878906, unitoth-ubuntu-2882972-1793289517
- ot_s81sl_vn_a_ce12c: client2878907, unitoth-ubuntu-2883087-1793289517
- ot_s81sl_vn_b_ce12c: client2878908, unitoth-ubuntu-2883074-1793289517
- ot_s81sl_vs_ce12c: client2878909, unitoth-ubuntu-2883068-1793289517
Check core_logs3/place_<kit>.otrun.log, kit/run_place.log, kit/lec/lec.json,
and kit/run/results. Do not duplicate; all were live at reset. Initial source
plan images personally viewed, ONE PLACE only; actual review before CTS.
Normal generator stages the proven 64-edge reset contract. All preflight PASS0.

Seven bound station kits generated and preflight PASS0 under gen_bound4/T/T,
T = slice_station__t8/23/31/43/44/49/52. The normal supported path is bind.py
kit-rtl with the actual strict bound source, then gen.py phys --kit-rtl (no
second --clock-landing). Original native sidecar attempt failed because the
S81 observer is nested, not a direct seqhost.contents leaf. The inherited
bind output had deleted source-worktree paths in bind.f/extra_lib; own
bind_relocated copy changes only those paths, original RTL unchanged.

Seven station PLACE attempts terminated FAIL RTL_LINT before P&R. Proper
runner is GEN_OUT/run_kit.sh (one level ABOVE the kit); it was copied into each
kit for self-contained ot-run staging after initial missing-runner exit127.
All failures preserved in logs_bound4/place*.otrun.log. Actual root cause now:
forwarded-clock insertion in inherited bound RTL emits a port declaration
`input wire clk_t4 // planned physical tap: forwarded-clock export only,`
with its comma inside the comment, then another output port. Example source
rtl/s81p_slice_station__t43_bound.sv lines51-52. Correct the binder emitter,
rebind/export/regenerate fresh kits; do not edit failed RTL in place. NOT FIXED
after reset.

Queue13 published before reset: coord/state0a842cd760ad, queue13.tsv retains
rows/paths. All REQ holds on unique actual-placed tags
CODEX-S81-CE12-PLACED-1029 / CODEX-S81-CE12-STATION-PLACED-1029; explicit guarded
run_grt_only.sh runners cannot do DRT. IDs recorded in queue13.tsv. No CTS/GRT
release from the initial source-placement reviews.

VSW fresh full template generates, but preflight FAILS macro_channels:
two SRAMs at (107.568,71.28) and (107.568,112.368), actual gap0.024um <10.8.
No VSW PLACE was launched. Next proposed same-outline physical alternatives
were moving lower SRAM down10.8 or upper SRAM up10.8 (gap10.824); neither was
implemented or launched before reset. Original pin/LEF correction is independent
and keeps actual M5 PG ports. Diagnose/review internal macro placement first.

Inherited BF reset64 LEC completed NOT EQUIVALENT 60876/60889 proved,13 differs,
0undecided,1706KEEP=1705retained+1constant,0missing. Receipt intel1
/srv/opentallas-scratch2/claude/ce10-lec/bf_col/lec_rc64/lec.json. Five c4.r[0]
(differenceLSB) alias the same-stage c4.r[28] (sumLSB); losing those five state
aliases creates ten failing downstream c5 points. Three remaining failures are
segtree y_pos driven by x_pos: gate netlist x_pos is combinational AO21, while
RTL declares it clocked; Yosys memory_dff folded the output register into the
memory-read state. A longer reset does not fix these correspondence failures.
Existing untrusted eq hints for the five arithmetic aliases and a default-off
explicit kept x_pos register were proposed but NOT implemented after reset.
ROM counterpart ce10-lecrb64-rom still LIVE on intel1, collect its lec.json.

BF tag distribution repair is independent: optional TAG_GROUPS0/4/16, zero
cycles, smallest lockstep+mutant PASS; full top lint PASS with baseline warning
classes unchanged; Yosys retains4/16 final copies (143/299bits,+39/+195).
Source preparation only. Existing actual V1 GRT overflow0 then boxednet15370
and TT setup-110.39 remain FAIL; tag source repair does not claim routed closure.

No new OWNER? decisions.
