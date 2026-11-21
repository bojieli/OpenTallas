# FABLE-FIX-S81-SVC-R3 handoff (started 2026-11-20 17:25 PST)

Owner of the S81 svc family (svc_hi, svc_lo, svc_rs, H8 dissolve). Succeeds FABLE-FIX-S81-SVC-R2 (read its handoff for history).
Deliverables: (1) svc H8 bind strict 0 svc errors + LATCHECK, J6 manifest delta to S81-DIE-R4 before 11-21 13:00;
(2) J5 svc_rs rows clear macro place (MPL-0020 name mapping), generator fix + test if not; (3) one svc type to sign-off, exported.

## State 17:35 PST
- R8 never bound under R2: r8 died in 1 s on a cp, r8b was refused by ot-run (`--priority plan` needs `--plan-job bind` or a `bind*` script name).
- R8c launched 17:28: epyc9 unit oth-ubuntu-1337266-1795224509, script epyc9 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc-r3/bind_r8c.sh`,
  out `fable-fix-s81-svc-r3/bind_r8c`, log intel2 `~/fable-fix-s81-svc-r3/bind_r8c.log`. R7 ELAB hardlinked, r5b plan, manifest
  `fable-fix-s81-svc-r2/ksrc/asbuilt_svc_d8i_h8_proto_r8.json`. Prints `R8_ERRORS n svc m`, `R8_LATCHECK_RC=0` / `R8_LATCHECK_EXIT`. About 1.5 h.
  Expected: 18 HARD_CORE_PARAM_ALL on non-svc types remain (records missing in the private source), svc 0.
- R2 kit prep kit_hi4_a died: `bind: ERROR kit-rtl: failing global bind needs an explicit verified LOCAL component proof` (R5b is not green).
- R2 RDPIPE bench (unit oth-ubuntu-686872-1795210550) is still running on epyc9 (mut1 sims); result `fable-fix-s81-svc-r2/rdpipe/done.txt`.
- R2 count jobs C on epyc8: never admitted as of 13:35.

## Files
- epyc9 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc-r3/` (mine), `fable-fix-s81-svc-r2/` (inherited: ksrc, bind_r7, mkties.py).
- intel2 `~/fable-fix-s81-svc-r3/*.log`.
- hub delta: `lanes/handoff/s81-svc-h8-j6-manifest-delta-1120.json` (9 tie classes still proof UNVERIFIED).
