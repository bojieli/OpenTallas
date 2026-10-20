# HWIN full-size four-state receipt collection — OPEN

This additive record continues the existing NS47/NEV16 job from source/sim
packet `69e7ec3a6`, canonical candidate `51e3f48f3`, selected anchor
`1e057b7bf`. The collector reads the running job and stores completed logs.
The source packet remains independent of current public main.

At the 2026-10-19 23:15:55 UTC observation, all eleven raw reset phase
logs **0–8, 90 and 93** have completed `MUWIN PASS` and `EARLY_MITER`.
Phases0–8 report19127..19135 edges, phase90 reports19217 and phase93 reports19220.
Each reports188 starts and2528 fires, matching2528 expected. The source and
compiled-input hashes remain unchanged. Both final injected-X logs contain
`EARLY_X_CAUSAL` at c1132 with valid1/fresh1, followed by the expected qualified
payload/control fatal. All19 final logs are preserved in `final_receipts/`.
The scope is now inactive. These are positive raw-case and expected negative
witnesses; the overall outer job exit remains **UNKNOWN**, as explained below.

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

The original controller session 6284 was marked failed/exit -1 at
22:34:29 UTC when its worker ended, although the remote source harness
continued. `original_controller_record.json` preserves that exact task-scoped
record. Its outer `OT_RUN_EXIT` stream is unavailable; this is a controller
collection limit, not a remote source-test failure. No terminal exit is inferred.

The remaining original06 raw-case collection is complete. `collect_final.py`
checks every phase and both final causal logs without inferring an outer exit. Preserve a real
failure and obtain ROOT disposition. Root separately owns the private source
package choice, complete mapped retention/cost, macro/PG/clock and physical
qualification, parent adoption, and single/multi-user token dependencies.

The separate namespace package source9e7921b40/replay06f8ca8dc is not covered
by this raw collection. Its independent all-shape/core/full-size reset receipts
live under results/arch/s81_hwin_private_package_1019/.
