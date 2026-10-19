# HWIN full-size four-state receipt collection — OPEN

This additive record continues the existing NS47/NEV16 job from source/sim
packet `69e7ec3a6`, canonical candidate `51e3f48f3`, selected anchor
`1e057b7bf`. The collector reads the running job and stores completed logs.
The source packet remains independent of current public main.

At the 2026-10-19 23:00:21 UTC observation, reset phases **0–8** have completed
`MUWIN PASS` and `EARLY_MITER edges 19127` through `19135`. Phase 90 is running.
Remaining phases 90/93, final qualified payload/control X witnesses, and
the overall job exit remain **OPEN**. An active scope or individual phase
log establishes no terminal job verdict.

The existing job runs on `ot-epyc8` in
`oth-ubuntu-2036610-1792446395.scope`; local ot-run PID 2697898, SSH PID
2697929, tool session 6284. Its immutable source staging is
`/srv/opentallas-scratch/claude/s81-hwin-early-source-1019/src_rx06` and its
receipt directory is `run_four_state_fullshape_06/four_state` beneath that
same base. The `.scope` suffix matters when querying systemd.

`observations/` retains dated scope status, all phase hashes, eleven staged
source hashes and actual projected-input hashes, including `tb.vvp`.
`static_receipts/` retains the parser projection, binding audit, projected
source/diffs, Icarus version and primitive probe. The prior source packet
contains the original failure history and qualification of these projections.
`projection_traces/` additionally preserves all six actual original06 trace files
and their six logs; seeds 1/19/313 are byte-equal between original and projected
RTL. These are the running original06 job's receipts, independent of namespace replay.
Run `collect_traces.py` to verify their immutable identity again.

Completed log files are immutable: `collect.py` refuses changed receipts or
source inputs. Its observations preserve incomplete-log hashes without
copying them as positive evidence.

Collect another read-only observation with:

```sh
python3 results/arch/s81_hwin_live_collection_1019/collect.py
```

When the job finishes, collect its actual `OT_RUN_EXIT`, final causal logs and
all remaining phases before changing the overall verdict. Preserve a real
failure and obtain ROOT disposition. Root separately owns the private source
package choice, complete mapped retention/cost, macro/PG/clock and physical
qualification, parent adoption, and single/multi-user token dependencies.
