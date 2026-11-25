# QC-FEV1-CL08 handoff (owner of qwen_compute slw_fe_v1__clfe325744__cl08d14f0d)
- 11-24 23:55 PST. Live kit: C1h private spec hub-coord/autopilot/private_specs/QC-ALLFIX/qwen_compute_slw_fe_v1__clfe325744__cl08d14f0d_1124082558, kit epyc9 .../s29q103S4Q9N46R6V4/private/QC-ALLFIX/slw_fe_v1__clfe325744__cl08d14f0d_1124082533/gen/slw_fe_v1__clfe325744__cl08d14f0d, unit oth-ubuntu-626515-1795547086. Stage detail route (iter 3, 47.5k DRV at 23:48).
- GRT: TT -113.89 single path (TNS=WNS), FF hold est -159.6. Cause: unstaged 877 um cland_rstart_tx hop (QC-FEV1-FLAT 21:13). V3 flat kit dc5cb0b30431 ended EXHAUSTED TT -166.
- Never signed under any plan (no AUTO-EXPORT row).
- Fix: C1n 26036a30b94f (intel1 QC-CB-C1L/c1n/final/plan_c1n.json) carries landing_relay_tx_stages=2 + relay_sites p0 [23.04,354.24] p1 [8.64,627.84]. C1m does not.
- Next: when the C1n tree + strict bind are done (QC-CB-C1L posts), run kit_wave.py private-spec --plan C1n --tree <C1n tree> --bind-out <C1n bind> --goal route --host epyc7|intel1. Do not use --allow-bind-stale.
- 11-25 00:21 PST: per QC-ALLFIX, relaunch binds to C1n-r c26a5b81029d (C1n + RRDRV reset-tap remap; epyc2 /srv/opentallas-scratch3/claude/QC-CB-C1L/rr/plan_c1n_r.json). Checked: the type keeps landing_relay_tx_stages=2 and the same relay_sites. Launch on QC-CB-C1L BIND-PASS.
