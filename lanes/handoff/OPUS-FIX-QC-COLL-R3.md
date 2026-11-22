# OPUS-FIX-QC-COLL-R3 handoff (Opus; successor of FABLE-FIX-QC-COLL-R2, started 11-21 23:1x PST)
Goal: QC coll_core + coll_ftc sign-off; coll seats for V3/V4. Read lanes/handoff/FABLE-FIX-QC-COLL-R2.md (method, solver, files) first.
Work dir: epyc10 /srv/opentallas-scratch2/claude/fable-fix-qc-coll-r2 (reused; hub specs same path on intel2). Clients of the kit units live on intel2 (tolerant-swine): ot-wait there with --host epyc10.

## STATE 11-21 23:3x PST
- v3 seat bind DONE rc 0 (oth-ubuntu-3836728-1795329935): strict 0, LATCHECK 1921/1921, kit-rtl done (pk4/rebind_rtl). R8 table = cb7f8940cd90 (same as pk3/cr8).
  OFFERED to QC-PLAN-R13 as relay_sites value_file swap: lanes/handoff/OPUS-FIX-QC-COLL-R3-V3seats.json (pkg5/rows_v3p5r.relay_sites.json sha 022d10f88709).
- tree_fork: ot-tree-fork --verify OK after I broke 725 lane-internal hardlinks pk4/bind_plan <-> tree_fork/plan_of_record (bind_pkg4 cp -al) by copy+mv in pk4/bind_plan.
- v2 proof kit pkit_core1 (tree cr8, READ ONLY): route unit oth-ubuntu-3825799-1795329899, at CTS. Owed reads: post-CTS reset recovery, u_tcv qdata fan-out, OT_RELAY_SITES unmatched. At its end: ot-delete cr8 + rt_tools_launch/qwen_compute_v2r10_famqc_cr8@*.
- coll_ftc pkit_ftc2: route unit oth-ubuntu-3640525-1795329160; CTS post-hook TT WNS +44.23, hold gate PASS FF -86.46 (structural limit -152.8, forwarded ring inputs). Next GRT.
- v3 proof kit LAUNCHED 23:3x: intel2 core3_chain.sh (setsid pid 3471649, log core3b_chain.log, run log pspec_core3b.run.log) -> spec pspec_core3b, kit epyc10 pkit_core3b, goal auto.
  src_manifest OK 194356459b67 (I installed cr8's .src-manifest.{json,sha256} into tree_fork: content identical = famqc + R8 cb7f8940cd90 overlay; so the v3 build is signable).
  pspec_core3 (first try) died src_manifest DRIFT: ignore.
## Next
1. Watch pkit_core3b place read (INLOCK half-cycle class should be gone) -> CTS -> GRT -> route -> sign-off.
2. Reads on v2 kit at CTS/GRT; ftc GRT/route/sign-off -> export.
