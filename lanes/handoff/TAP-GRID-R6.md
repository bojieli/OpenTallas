# TAP-GRID-R6 handoff (Opus 5.5; started 11-23 05:50 PST, replaces TAP-GRID-R5; updated 11:10 PST)
Lane dirs: /srv/opentallas-scratch2/claude/tap-grid-r6 on intel2/epyc7/8/9/10 (bin/ = tap_split.py main c84f72ee2c, tap_offset_cover/fill,
census.sh = TAPOFF-ALL census, caloc.sh + cal_oc.py = SINK-EST calibration + over-cap census). Clone intel2 tap-grid-r5/repo (branch tapgrid-r6).
## Landed on main
- 7b6367f4a3 TAPOFF-ALL-PRE: PRE TAPOFF-MISSING = tap_offset_cover census (all tap modes + window form); tap_split writes window rows same step; R5 LOO tol.
- c84f72ee2c tap_split imports TAPOFF siblings from its own dir (older --tools trees lack them; python3 -I drops script dir).
- (R5) ea26701db7 TAPOFF-1123, f26171d92a SINK-EST-1123.
## Census results (census/ dirs per host)
- TAPOFF: KV K3 f75a71af72eb PASS 56/56; HEAD r18z2 3 window types 43 ports; KV c25 19/1676 (filled by K-chain); QC c3n 106 types/1858; S81 dr4 157/1167.
  S81 Wave A 4662b734580b census running epyc10 census/s81_wavea_4662.log (Codex fill 6549/200 types).
- SINK-EST calibration (types with plan taps within 10% of kit): plan/real -> est/real: S81 0.33->1.24 (101), QC 0.40->1.49 (61), KV 0.13->1.33 (8 unsat), HEAD 0.55->0.80 (7).
  Residual: QC sle/slw hc* bins kept (placed <=1.2x bins) but one kit tap 3-9k = concentration, not count. Cache bins are pre-move geometry (hub_Wo artefact).
- KV K3 over 3000: pv_v3e 22413, pv_v1n 21842 (real, offered split, GO from KV-D29), hub_Wo artefact, hgi_v1 cl42 3200 advisory. Posted 11:0x.
## Open
- svc re-cut for S81 (COORD, due 14:30 to S81-SVC-J9 + S81-J9-ASSEMBLY-R6): epyc10 tap-grid-r6/svc (svc_recut.sh; 8 types with netlist flops 590k-926k, cap 800). Queued on epyc10 load cap.
- rc98 QC pinreg (TGR5-QCV4-PINREG-1): Codex delivered c4 latest0814_pinreg_filled d2c83b3d7fbb; QC C4 81fd3e6370c0 is gating -> confirm row in V4 to QC-V4.
- D29 SOFTFLOP + rc119 pc: DELIVERED, in K3 (Codex rs6 k2 ba59584701e3, pc_socket_search 1b52ed206c35).
- J9 tap regen: Codex Wave A tap delivery 63bafd10e3c5 / 4662b734580b; my dry5b out2 had no plan_j9taps (check log) - superseded by Codex j9_regen_v6.
