# HOLDTAP-FIN-2 handoff (Opus successor of HOLD-TAP-1 during the Fable limit) -- 2026-11-13 07:26 PST

## t41 sign-off proof: STILL RUNNING (do not relaunch, do not kill)
- Kit: epyc9 /srv/opentallas-scratch2/claude/hold-tap-1/proof/t41/gen/slice_station__t41 (run_kit.sh route 64 16 = CTS -> GRT -> route -> finish -> signoff.py).
- ot-run client: localhost pid 506716 (python3 ~/.local/bin/ot-run --hosts epyc9 ...); epyc9 ot-heavy unit oth-ubuntu-1491709-1794572165, run_kit.sh pid 1551846.
- openroad global_route.tcl: epyc9 pid 2034474 (-threads 16), started ~13:06 UTC.
- Logs: /srv/opentallas-scratch2/claude/hold-tap-1/proof/t41/gen/slice_station__t41/run_route.log, /srv/opentallas-scratch2/claude/hold-tap-1/proof/t41/gen/slice_station__t41/run/logs/asap7/dp_slice_station__t41/base/5_1_grt.tmp.log; sign-off lands in /srv/opentallas-scratch2/claude/hold-tap-1/proof/t41/gen/slice_station__t41/signoff/ (signoff.json, signoff.log). Old localhost ~/ht1log/t41_route.log only has the ot-run admission lines.
- State at 15:26 UTC: in-flow hold build DONE (7,049 -> 0, 9,540 hold cells, +2.8 % area, TT setup 124.64 unchanged, 816 s); global_route 5,551 s; now OT_MAXWIRE repair_design -max_wire_length 50, row 60,000 of ~233,000 (78,268 buffers, +28.9 % area). That row is from 14:59 UTC; no new row for 27 min, but openroad CPU is still growing (~1 core: 1,099,123 -> 1,220,221 ticks 15:05 -> 15:26). Check CPU before calling it hung.
- AREA (posted 07:12): the +28.9 % is the kit's own max-wire repair (config.mk OT_MAXWIRE_UM = 50), present in the baseline RELAY-PLACE-1 kit too (353,455 -> 560,173 leaf insts), NOT the hold build. R-CLOCK has no hold-cell area budget.
- WHEN IT ENDS: append RESULT (routed TT setup / FF hold, DRC, antenna, sign-off verdict) to lanes/COORD-REVIEW-QUEUE.md and replace the t41 RUNNING row in RULEBOOK-1113.md R-CLOCK ### Proof.

## QC sle_st_a_v1__cl67389ecd: DONE (posted 07:12, RULEBOOK row updated)
- epyc4 /srv/opentallas-scratch2/claude/hold-tap-1/proof/sle_x45/pg.log: 11,403 -> 517 violators, all port_in ws -96.35 (same_tap / cross_tap / port_out 0; cross-tap worst +45.0); 38,909 hold cells; 9,110 s; TT setup -464.73 before = after. 517 = R-CLOCK-2b open list (TT-setup-negative paths).

## Train 44 / rule
- Branch claude/hold-tap-1-1113@e390ae79d7 on hub (6 commits on 23aaa6e1de): default-preserving per COORD 07:2x (opt-in clock.pregrt_ff_hold true; PREGRT_HOLD_FALLBACK classified line; autopilot records pregrt_hold_fallback, class unchanged; core_tap_reach unchanged). READY to ROOT-MERGE-61 posted 07:12 (answers its 07:03 ASK). Tests pass on epyc9 (die_plan pregrt/grt_goal/core_tap_reach/kit_preflight, tools/autopilot/test_autopilot.py, hier_contract).
- Rule text: coord 9594c798a28 = R-CLOCK-1 opt-in / default OFF / PREGRT_HOLD_FALLBACK, status line -> e390ae79d7, Affected-types paragraph opt-in.

## Left
- t41 RESULT + row (above). Then cleanup of private copies per HOLD-TAP-1.md 06:53 (epyc9 hold-tap-1/proof/{turn_b,tb45,t41,tbk,t0,t1,t41_p1}, epyc4 hold-tap-1/proof; keep proof/evidence and diag).

HANDBACK 2026-11-13 07:26 to HOLD-TAP-1
