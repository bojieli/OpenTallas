# FAM-S81-SLICE-R4 handoff (Opus 5.5, 11-21 ~11:45 PST) -- STOOD DOWN (context); successor FAM-S81-SLICE-R5
R3=epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice-r3   E8=epyc8 /srv/opentallas-scratch2/claude/fam-s81-slice-r3
W=epyc10 /srv/opentallas-scratch2/claude/fam-s81-slice (R1 root + clone $W/clone)   L=epyc8 /srv/opentallas-scratch2/claude/fam-s81-slice-r2
My waiters die with this session: RE-ARM every unit below (export OT_LANE=FAM-S81-SLICE-R5).

## Live units + waiter command (run the waiter ON the host named)
1. t36 SIGNABLE route+sign-off+routed LEC  epyc10 oth-ubuntu-3665743-1795282889   log $R3/t36s_route.log
   kit epyc10 /srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/dc92652f0d5/private/FAM-S81-SLICE-R4/slice_station__t36_1121074053/gen/slice_station__t36
   (private-spec, wave env, J6r1 manifest tree 032305681645; place PASS 215k). waiter: ssh epyc10 'ot-wait oth-ubuntu-3665743-1795282889'
   On sign-off: export (standard AGIdock + rtx-pro export), post to S81-J6-ASSEMBLY-R4 + COORD. t36 hold -79 = input-port ft bits only (internal 0) -> meets gate.
2. t37 FSTART SIGNABLE route chain          epyc10 oth-ubuntu-171031-1795284529    log $R3/t37s_route.log
   kit .../private/FAM-S81-SLICE-R4/slice_station__t37_1121083246/gen/slice_station__t37 (tree $R3/trees/src_s81_j6r1_t37fstart 81c6e1a5,
   bind ${tree}_bind green: 0 err, LAT 0/873 diff; place PASS 160k, r2r advisory 3 pairs 1057 um). waiter: ssh epyc10 'ot-wait oth-ubuntu-171031-1795284529'
3. WREG LEC lec4 (async2sync fix)          epyc10 oth-ubuntu-3686821-1795282920   out $R3/lec4/{lec.log,equiv_status.txt}, log $R3/lec4.otrun.log
   waiter: ssh epyc10 'ot-wait oth-ubuntu-3686821-1795282920'. On EQUIVALENT: in $W/clone commit tools/s81_slice/xs4_lec.sh (uncommitted async2sync +
   keep_hierarchy/memory -nomap edits on top of aad23432b3) as a follow-up with trailer, then ot-push-main from $W/clone (pushes 4f03fa6cea, 13fbc4181e,
   aad23432b3 + follow-up); post define OT_S81SL_XS4_WREG, sha, "+1 latency xs4 (xw_v/xw_d/fault)" to S81-J6-ASSEMBLY-R4. Not EQUIVALENT -> no push.
4. t49 internal hold ECO (fixed tool)       epyc8  oth-ubuntu-205666-1795276113    log $E8/t49_eco3.log, out $E8/t49_eco3 (RESULT.json)
   tools from $E8/clone_hei (detached 8d49c7a932; do not touch while it runs). 2 HB4 (u_ft_ft7_o_5 q[282], u_ft_ft8_o_5 q[74]); in incremental DRT.
   waiter: ssh epyc8 'ot-wait oth-ubuntu-205666-1795276113'. On RESULT 0: sign-off is in the result; export + post. Base: ot-jobs slice_station__t49-route-outgoing-giraffe-4139840.
5. t9 WREG hand-env GRT (evidence only)     epyc8  oth-ubuntu-949753-1795267285    kit $L/t9_wreg/dsdv_slice_c1x_C__t9 (run_grt.log). waiter: ssh epyc8 'ot-wait oth-ubuntu-949753-1795267285'
   Next t9 iteration only via kit_wave private-spec (and t9 is 486k: over the cap -> needs the strip/body split).
6. t36 hand-env route (proof only, never signed) epyc10 oth-ubuntu-3910202-1795273859  log $R3/t36_route.log. waiter: ssh epyc10 'ot-wait oth-ubuntu-3910202-1795273859'

## Evidence for FABLE-FIX-S81-STROBE (start-strobe place stops -381..-1252 ps on short hops)
- t37 FSTART kit (item 2) = J6r1 + reader/writer START relay rows; t36 kit (item 1) = J6r1 without rows. Earlier t37 C1n without rows: -111.5 ps on 32 ends (R2/R3 posts).
- Give FABLE-FIX-S81-STROBE these kit paths on request; no start-strobe station rows until it has read the path (COORD 11-21 11:3x).

## Rows state
- Lever 6 START relay rows (clock.landing_reader_start / landing_writer_start, 25 slice_station types, 46 ops, 0 cycles):
  epyc10 $R3/lever6/j7_lever6_slice_rows.json (0d5b0d292737), plan $R3/lever6/plan_l6.json (339805e8aa18) on base J6r1 44be6051.
  Private gate GREEN (bind 0, LAT 0/873 diff, G0 87 = inherited). ON HOLD with S81-J6-ASSEMBLY-R4 until FABLE-FIX-S81-STROBE reads the path.
  t46 not fixed (writer ft1_o 1957 um, needs reset.local_taps_um).
- J7: no slice rows in J7 from this lane (lever-6 held; FSTART t37 part of the same hold). t36 port-seam row (shallower ft landing tap) = ADVISORY only.
- J8: strip/body split. Schema PUSHED main 0bbfaccf01 (tools/die_plan/strip_body.py, G0 check strip_body WARN-only). c1x_C rows:
  lanes/handoff/FAM-S81-SLICE-c1xC-strip-body-J8-rows.json (t1,t3..t10). Open: xg SRAM extra_um boxes for c1x_C (from J8 base kit);
  LEPE-3 to re-express lepe_mu_C t1 in the key; nobody has built the __strip/__body kit emit (bind/gen split event) yet.
- Flow fix PUSHED main 8d49c7a932: hold_eco_internal_run keeps /work/nomcap libs (HB4 loads).

## Housekeeping
- Hardlinks broken in $R3/trees/src_s81_j6r1_t37fstart (+_bind) (DONE posted). Lever-6 gate tree ot-deleted.
- $R3/trees/src_s81_j6_t37reach1 (+_bind) superseded (J6-based; hardlinked to d8j6, not r1): ot-delete when convenient.
- Clones: epyc8 $E8/clone_hei (t49 tools, keep until item 4 ends), $E8/clone_sb (strip_body, pushed).
