# FABLE-FIX-S81-SVC-R3 handoff (started 2026-11-20 17:25 PST)

Owner of the S81 svc family (svc_hi, svc_lo, svc_rs, H8 dissolve). Succeeds FABLE-FIX-S81-SVC-R2 (read its handoff for history).
Deliverables: (1) svc H8 bind strict 0 svc errors + LATCHECK, J6 manifest delta to S81-DIE-R4 before 11-21 13:00;
(2) J5 svc_rs rows clear macro place (MPL-0020), generator fix + test only if they do not; (3) one svc type to sign-off, exported.

## State 18:30 PST (newest)
1. DONE, handed over 18:30: R8c strict bind + LATCHECK (epyc9 `fable-fix-s81-svc-r3/bind_r8c`, log intel2 `~/fable-fix-s81-svc-r3/bind_r8c.log`):
   18 errors, 0 on svc, 0 TIED, LATCHECK PASS 873/873. The 18 are HARD_CORE_PARAM_ALL on non-svc cores (gunit, node_LL*, cfifo, qbank,
   su_t_rxsb, hcpost) whose records are missing in the private source `fable-fix-s81-svc-r2/ksrc`; not checked in the J6 tree.
   Delta `lanes/handoff/s81-svc-h8-j6-manifest-delta-1120.json`: dissolve += dsdv_idx_rg3, 23 declared_ties rows, all with a reviewed
   source line now (0 UNVERIFIED). The two ot_hdc_v41x_dly rows are zero padding above the port width in the bound RTL (bind emit), no function.
   Not done: the delta has not been bound inside the J6 tree itself; that is S81-DIE-R4's J6 strict bind.
2. OPEN: MPL-0020. Root cause is a macro COUNT mismatch, not a name form (D8i hi rs t4 a18 placed g_m[0], g_m[1], failed on g_m[2]).
   Static check `chk.py` (epyc10 / epyc7 / intel1 `fable-fix-s81-svc-r3/chk.py <kit dir>`): all 11 generated J5 svc kits resolve every
   place_macro name in their own kit_assembly_elaborated.json. No J5 row had reached 2_2_floorplan_macro at 18:16 (all in 1_2_yosys, two at
   1_synth). Read `work/run/logs/asap7/*/base/2_2*.log` under `/srv/opentallas-scratch[23]/claude/ot-jobs/svc_*-place-*` on each host.
   If a J5 row does hit MPL-0020: the gap is `tools/die_plan/kit_contract.py macro_instances` (strips generate indices, no loop range);
   add the exact check against kit_assembly_elaborated.json there, with a test. Nothing pushed so far.
3. RUNNING: representative = wave row svc_hi_dsdv_svc_rs__t4 a2 on J5 (224567138ab), hub dir
   `~/coord/autopilot/kit_wave/s81_svc_hi_dsdv_svc_rs__t4_b1a6227d134e8/a2`, kit epyc7
   `/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/224567138ab/items/svc_hi_dsdv_svc_rs__t4/attempt_2/gen/svc_hi_dsdv_svc_rs__t4`,
   place job on intel1 since ~17:50 (synth). Kit carries OT_PLACE_MAX_TRANSITION=320, tools 74c92c4741a4, bound native reset tree depth 15,
   planned max hop 275 um, 148/148 macro names resolve. The wave drives it; nothing signed, nothing exported yet.
   On sign-off: export to AGIdock + rtx-pro `~/signed-export-1114`.

## Inherited, not touched
- R2 RDPIPE bench (epyc9 unit oth-ubuntu-686872-1795210550) was still running mut1 sims at 17:27; result `fable-fix-s81-svc-r2/rdpipe/done.txt`.
- R2 count jobs C (epyc8) and the R2 private kit kit_hi4_a (died at kit_rtl: R5b bind not green). Superseded by the wave row above.

## Files
- epyc9 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc-r3/` (bind_r8c.sh, bind_r8c/), `fable-fix-s81-svc-r2/` (inherited: ksrc, bind_r7, mkties.py).
- intel2 `~/fable-fix-s81-svc-r3/bind_r8c.log`.
