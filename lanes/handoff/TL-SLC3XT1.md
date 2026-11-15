# TL-SLC3XT1 s81/dsdv_slice_c3x_C__t1 (2026-11-14 04:5x PST)
Finding: the "route failure" is not a route result. Attempt 22 (event 7073a6b4a59) placed OK on epyc7 (place rc 0, 3_5_place_dp 21:21 PST 11-13). Route job 14a1abcee0e7 went to epyc4, restarted synth from scratch (no resume.json) and died exit 137 at 23:57 when epyc4 was drained (DRAIN-EPYC4); CLASSIFY CRASH infra-stopped. No GRT/DRT ever ran, so no routing evidence exists for this type.
State: dies/s81/retry already has dsdv_slice_c3x_C__t1@22 (retry_fix text DRAIN-EPYC4 relaunch on other hosts), but dies/s81/hold_items still has B2-HOLD-1113 (KIT-OPS-2, until S81 UPDATE B2), so it does not launch. Kit gen dir on epyc7 was pruned (only run/logs, reports left), so a private rerun needs a fresh gen anyway; the wave does that.
Advisory only: a22 AUTO-GEOM fill 0.053 / empty 0.75, preflight clock M7 vs M8 and macro channel 8.64<10.8; a21 visual BAD (WAIT-FORM) is for a21 form, a22 form fingerprint changed.
Action: asked KIT-OPS-3 to delete hold_items key; same src/plan (freeze-safe), runs gen+place+route on epyc7/epyc10/epyc2/intel1.

Update 06:4x: hold lifted; a23 launched 04:58 and failed 06:36 INFRA @gen_lint: yosys rc 143 (SIGTERM) on epyc8 (MemAvailable 58 GB, disk-tight host; kill from outside, not an RTL error). Needs retry key @23 and gen_lint off epyc8. Waiter re-armed.

Update 14:5x: a24 (06:39), a25 (12:17), a26 (13:26) relaunched by wave (restaged epyc9->epyc7). a26 FAIL FLOW @lec_tools 14:56: ValueError runner template differs from pinned scheduler snapshot (scheduler/tool pin mismatch, not RTL or route). Still no GRT/DRT result.

Successor 19:3x PST 11-14: lec_tools pin fixed by KIT-OPS-5 (15:10). Attempts a27 (epyc8 fail), a28 (epyc10), a29 (epyc8, gen_lint/gen live at 19:31, admitted via ot-heavy). Still no GRT/DRT result for this type. Not relaunching: a29 is live. Waiter: ~/coord/lanes/handoff/TL-SLC3XT1.watch.log (no LLM).
