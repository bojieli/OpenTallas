# FAM-S81-SLICE-R5 handoff (Opus 5.5, live; updated 11-21 12:10 PST)
Predecessor handoff lanes/handoff/FAM-S81-SLICE-R4.md (paths R3/W/L/E8 defined there). Waiters run in this session; a successor RE-ARMS all.

## Live units
1. t36 SIGNABLE route+sign-off+routed LEC  epyc10 oth-ubuntu-3665743-1795282889 (log fam-s81-slice-r3/t36s_route.log). CTS post-hook TT +127.37, pre-GRT hold pass done; in GRT 12:0x.
2. t37 FSTART route chain epyc10 oth-ubuntu-171031-1795284529 (t37s_route.log). CTS TT +46.37, +24.27 after pre-GRT hold; in GRT.
3. t36 hand-env route (proof only) epyc10 oth-ubuntu-3910202-1795273859.
4. t49 internal hold ECO epyc8 oth-ubuntu-205666-1795276113 (fam-s81-slice-r3/t49_eco3, RESULT.json).
5. t9 WREG hand-env GRT (evidence) epyc8 oth-ubuntu-949753-1795267285.
6. kv512_C t1 private-spec run-item intel2 pid 1315433 (spec ~/coord/autopilot/private_specs/FAM-S81-SLICE-R5/s81_dsdv_slice_kv512_C__t1_1121120337, log /srv/opentallas-scratch2/claude/fam-s81-slice-r5/*.runitem.log). Claimed 11-21 12:0x (dead owner S81-DIE-R5).
7. c3x_C t1 private-spec run-item intel2 pid 1315434 (spec .../s81_dsdv_slice_c3x_C__t1_1121120339). Claimed (unowned).
Waiter: ot-wait <unit> on the named host; ot-wait <pid> --cmdline run-item on intel2.

## Done
- WREG LEC lec4 EQUIVALENT 77321/77321 (define off). PUSHED main 7694816880 (c2907ed768, f1aa185305, 904afefed8, 7694816880). Posted to S81-J6-ASSEMBLY-R4.

## Holds
- Lever-6 START relay rows ON HOLD until FABLE-FIX-S81-STROBE reads the path (no post from it yet at 12:10). Evidence: t37 FSTART CTS TT +24..+46 real clock.
