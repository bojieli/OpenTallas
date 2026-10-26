# Wavefront-reset negative control for the xt1 both-cluster pass (2026-10-25)

Same carve, sources and inputs as `../xt1_wavefront_r3` (actual r3 wavefront bound top; copied from
epyc3:/srv/opentallas-scratch2/claude/codex-qc-wavefront-run-1025/both). Only `tb_smoke.sv` changes: `+START_DELAY=<n>`
starts the calendar n clocks after die rst_n deasserts (default = the carve's CALENDAR_START_DELAY 130). Fresh build
(28 min, 79.5 GB peak) via ot-run (epyc3 -> spilled to epyc2, unit oth-ubuntu-2111593-1792927913), `run_early.sh`.

Published releases of the 22 carved partitions (bind_reset.json): sl_W5_* 77..91, c_W5_tn_* 94..110, c_W5_tf_* 101..116
(die-wide latest 128, latest core pin 129).

| calendar start after rst_n | result |
|----------------------------|--------|
| 130 (published contract) | PASS near 64/64 + far 64/64; every cw_go / result edge identical (relative to start) to the original run |
| 100 (before c_W5_tf/tn releases 101..116) | PASS 64/64 + 64/64, same edges: the first command word reaches those tiles ~150 clocks after the calendar starts (d_clu 152), i.e. after their release |
| 0 (keyed to the reset edge, the pre-decision-13 practice) | **FAIL near 0/64, far 0/64**: the xpf/command words reach sl_W5_fw (release 88) at clock 61, `FAULT heads` at 200, every result word wrong |

Conclusion: the carved partitions really are held by the wavefront (the bench is sensitive to it), and the published
start contract (130) is safe with margin. The 100 PASS says the static start could be tightened per path (start >=
release - first-arrival lead for each partition), but the plan keeps one die-wide start; no change proposed.
