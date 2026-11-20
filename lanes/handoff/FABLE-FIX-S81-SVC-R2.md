# FABLE-FIX-S81-SVC-R2 handoff (written 2026-11-20 ~10:00 PST)

Owner of the S81 svc family (16 H8 types, 112 do-not-count on D8i) and the svc H8 package. Succeeds S81-SVC-SPLIT-1119.
Deliverable: J6 rows to S81-DIE-R4 by 11-21 13:30; one representative svc kit through place, GRT, sign-off; post every 2 h.
Nothing is bound, placed or delivered yet.

## Update 12:15 PST (newest; read first)
- Driver R5b strict bind: exit 1, 458 errors. Root cause of the 224 hslice reset errors: u_irg_00..06 are `dsdv_idx_rg3`, bound as ONE
  leaf (not in the manifest `dissolve`), so the 32 plan hslice rows of lo rs t1-t6 and rs_w t1 find no leaf. u_irg_07 (t7) is
  `dsdv_idx_rg3_nq`, dissolved, and its hslice reset leaves bind (0 reset errors on t7). Plan rows need no change.
- TIED: the 199 printed lines are a 200-line cap, all u_irg_07. The full set is 1,881 tied bits on 285 leaf pins in 14 classes
  (`bind_tied.json`), on hi AND lo types: hslice cs_in / cf_in / first, ksadd_k b / cin, dsdv_idx_rg2_m1k ra / wa / wd / re / we,
  ot_hdc_v41x_dly d, sml_fold2 sk_en, smd_fold2 cfg_p. My 11:50 post "svc_hi 0 errors" was wrong; corrected at 12:15.
- J6 manifest delta: `lanes/handoff/s81-svc-h8-j6-manifest-delta-1120.json` (generator epyc9 `fable-fix-s81-svc-r2/mkties.py`):
  `dissolve` += `dsdv_idx_rg3`, 23 `declared_ties` rows with path regexes; covers 1,881 / 1,881 tied bits of R5b. Five classes have a
  reviewed source line (hslice x3, ksadd x2); the other nine carry proof "UNVERIFIED": review dsdv_idx_rg2_m1k, ot_hdc_v41x_dly,
  sml sk_en, smd cfg_p sources (or get the per-site bench) before adoption. `first`, `sk_en`, `cfg_p` are per-instance config straps:
  S81-DIE-R4 may prefer the manifest `straps` list over declared_ties.
- R7 validation chain (ELAB + BIND on the r5b plan with manifest `ksrc/asbuilt_svc_d8i_h8_proto_r7.json`): intel2 client 2427234, log
  `~/fable-fix-s81-svc-r2/r7.log`, out epyc9 `fable-fix-s81-svc-r2/bind_r7`; prints `R7_ERRORS n` and `R7_CLASS` lines. About 2.5 h.
  Expect: 0 EMIT wavefront core reset, 0 TIED on svc; new TIED classes may appear on u_irg_00..06 after the dissolve -> add rows, rerun.
  Risk not checked: dissolving dsdv_idx_rg3 changes the lo t1-t6 / rs_w parent (the reader body becomes parent glue, as on t7) and
  its internal station pricing / LATCHECK.
- Private hi rs t4 proof kit: `prep_kit.py` -> epyc9 `fable-fix-s81-svc-r2/kit_hi4_a`, log intel2 `~/fable-fix-s81-svc-r2/kit_hi4_a.log`.
  Uncounted, unpublished (COORD OK 11:5x). It binds with the undeclared sml / smd / dly ties of R5b.
- RDPIPE bench relaunched at 96 GB: log `~/fable-fix-s81-svc-r2/rdpipe2.log`, result epyc9 `rdpipe/done.txt`. First run was killed in compile
  (39.8 GB peak vs 24 GB request).
- Counts run B (epyc8) queued since 10:50: `count/<type>.B.stat.txt`.

## Update 10:55 PST (supersedes "In flight" item 1 and 3 below)
- R6 is DEAD: BIND exit 2, stale dead-input source `dsdv_pv_so_ingress_h8.sv` (both proof files record an older module hash than the
  bind source). It duplicated the driver. Do not launch an R7.
- Use the driver's R5b instead: epyc9 `s81-svc-split-1119/t7_resolve_1120/bind_d8i_h8_bind_source_r5b`, plan
  `prototype_src_r4/physical/die_plan/s81/plan_svc_d8i_h8_bind_source_r5b_1120.json`, manifest `asbuilt_svc_d8i_h8_proto_r5b.json`,
  log intel2 `~/svc-t7-bind-die-proto-r5b-e9-1120.log` (markers `H8_D8I_BIND_RC=0`, `H8_D8I_LATCHECK_RC=0`). In BIND at 10:50.
  `ksrc` predates the r5b plan and manifest: copy those two files in (and commit) before fresh_kit.
- Count jobs: run A failed (ROM model unparsable by yosys read_verilog). Run B relaunched 10:50 with ROM files excluded:
  intel2 `~/fable-fix-s81-svc-r2/count-*-B.log`, output epyc8 `count/<type>.B.stat.txt`.
- RDPIPE bench still compiling at 10:50.

## Do not touch
A detached driver (posts as S81-SVC-SPLIT-1119 / S81-DIE-R3) still launches the 16-type FT / clock / START closure in
epyc8 (and a copy on epyc9) `/srv/opentallas-scratch2/claude/s81-svc-split-1119/t7_resolve_1120`. Read only. Latest whole
geometry I read: `h8_start_16_collector_model_1120/plan_h8_start_16_collector_model.json`; newer per-type `h8_*_joint_*` dirs keep appearing.

## My files
- epyc9 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc-r2/`: `wt` (lane clone of main, sparse), `ksrc` (private git copy of the
  driver's `prototype_src_r4`, commit 6dee7273fb89, for fresh_kit `--source`; not for merge), `r6.sh`, `bind_r6/`, `rdpipe.sh`, `rdpipe/`.
- epyc8 `/srv/opentallas-scratch2/claude/fable-fix-s81-svc-r2/count/`: `mkcount.py`, `count.sh` (parent cell count on the R2 bound RTL).
- intel2 `~/fable-fix-s81-svc-r2/*.log`: ot-run client logs.

## In flight
1. R6 strict chain (ELAB -> BIND --strict --all-gaps -> LATCHECK), epyc9 unit oth-ubuntu-3189264-1795197350, intel2 client 475809,
   log `~/fable-fix-s81-svc-r2/r6.log`, markers `R6_ELAB_RC=0`, `R6_BIND_RC=0`, `R6_LATCHECK_RC=0`. Plan
   `physical/die_plan/s81/plan_svc_d8i_h8_bind_source_r3_1120.json`, manifest `asbuilt_svc_d8i_h8_proto_r6.json` (both in ksrc).
   R6 = R5 + `reprove_svc_h8_bind_source_1120.json` in `dead_input_proofs` (R5 bind exit 2 on exactly that). ELAB ~40 min, BIND ~60 min.
   A hub waiter posts `R6-RESULT` under this lane when the chain ends. COORD said keep R6.
2. RDPIPE lock-step bench (`rdpipe.sh`: flop form vs MEM_MACRO+RDPIPE, negative controls MUT1 and MUT2, seeds 1-3), epyc9 unit
   oth-ubuntu-2222755-1795196220. Result in `rdpipe/done.txt`, `mut1.out`, `mut2.out` (a `mut2.out` with "Cannot find file" is the stale first run).
3. Three count jobs queued on epyc8 (clients 5148-5150 on intel2), not admitted at 09:55: lo t7, pvso_entry t1, hi rs t4, tag A.
   Output `count/<type>.A.stat.txt`. Untested script: first check the `.yosys.log` for a missing module.

## Next steps
1. R6 green: `fresh_kit.py --source ksrc --profile partition --plan <R6 plan> --type svc_hi_dsdv_svc_rs__t4 --overrides ov.json --out <new>`
   via ot-run on epyc9. Overrides need `bind_out` (bind_r6), `asbuilt`, `reset_mode` (native needs `reset_context_plan` = the same plan),
   `assembly_contracts` for the hard views. Review the image, then run_kit.sh GOAL=route, then sign-off. Not attempted yet.
   R6 uses the R5 plan geometry, which differs from the latest geometry in clock / reset / contents rows; a private proof, not a counted kit.
2. R6 red: read `bind: ERROR` lines in r6.log; R2 had 18 TIED (fixed on main 8941c0023b5), 960 unreachable reset leaves, provider config groups.
3. RDPIPE passes: tell S81-DIE-R4 and the driver to add `OT_SVC_ATT_RDPIPE` to the manifest defines and the 16 rows before the final strict bind.
4. Counts back: decide the lo t7 / pvso t1 cut to <= 400k. No signed view of `dsfd_ctrl_rg3_native32` or `dsdv_idx_rg3` exists; a cut means a
   new core through the provider flow (epyc8 `s81-svc-split-1119/spec_*.json`, `build/route_prov.sh`, `build/sign_core.sh`).
5. Write the J6 rows: start from the driver's final 16-type plan; add RDPIPE, the cut, RDREG only with its per-site bench.

## Findings so far
- attnh is 1,077 b on all 16 rows and in the R2 bound t7 ports. t7 pbuf + qmem are at the hrow band; wq + sw stay under the N face.
- `OT_SVC_ATT_RDPIPE` is in none of the 16 rows and not in the R5 / R6 manifest: these binds use the `mem_la` sw form.
- RDREG defines (`OT_S81_SVC_PBUF_RDREG`, `_QMEM_RDREG`, `_WQ_RDREG`) are on main, default off. Not examined further.
- mem_ar per-instance: R5 ELAB restored `dsdv_svc_mem_ar` per instance (`svc_h8_wq_qmem_instance_widths.json`); width gate PASS 1758 / 109. Not checked further.
- 43 landing bands on 11 types record `max_pin_to_band_hop_um` 301-403 (`clock_landing_plan.py` is written for 405). They pass the 405
  check rule (`cbc_rules.REACH_GATE_UM`); above the 300 aim. Advisory, no hold.
- Stopped inherited intel1 unit oth-ubuntu-2294416-1795091014 (29 h yosys of the superseded H16 flat lo t7 shell).

## Posts
lanes/posts/FABLE-FIX-S81-SVC-R2.md: TAKEOVER 09:26, STATE 09:45, R5-RCA 09:57. Next due 11:30.
