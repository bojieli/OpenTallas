# LATCH-SWAP-0045 handoff (Opus, started 2026-11-21 00:0x PST)

Task: resizer latch -> flop swap (LOCKUP-STATION-R2 t39 proof4) as a possible functional class on all dies: LEC claim, exposure scan, flow-wide fix.

## Findings
- Swap is REAL (not a mapping artefact). epyc7 proof4_t39 ODB master counts (seqcount.tcl via ot-run): 1_synth / 2_floorplan / 3_3_place_gp
  DLL 32,457, DFFL 5,533 (all DFFLQNx1), 0 DFFLQx4; 3_4_place_resized DLL 31,469, DFFLQx4 988 (all u_fl_nl_*); 4_cts same 988.
  Cause: repair_design (place resize) upsizes a DLLx2 to DFFLQx4 (same CLK/D/Q pins); OpenSTA equiv-cell grouping does not separate latch/flop.
  Same risk DHL -> DFFHQx4.  Synth never emits DFF[HL]Qx4 (dfflibmap maps DFF[HL]QNx1); no repo flow script inserts them.
- LEC: in-flow lec_async proves RTL vs synth (1_2_yosys / ODB export) only -> blind to any later swap.  Sign-off (autopilot signoff_chain.py,
  s81_eco publish_view, head_post_route_eco) runs routed LEC of 6_final.v vs RTL and needs EQUIVALENT.  lec.py models a lockup latch as a
  wire (latch_to_wire) and every $_DFF_N_/$_DFF_P_ as an AIGER register (polarity dropped), so a swapped DFFL is an extra gate register with
  no RTL counterpart -> NOT EQUIVALENT / UNPROVEN, never EQUIVALENT.  LEC does not treat DLL and DFFL alike.  So routed LEC would catch it.
- Exposure scan (scan.sh, all 7 hosts, every 6_final.v / 5_route.v under /srv/opentallas-scratch*, ~moved skipped): suspects = routed netlist
  holding any DFF[HL]Qx4.  intel1 11,418 + intel2 3,713 netlists: 0.  others: see Update.
## Fix
- main 38faab8511 (LOCKUP-STATION-R2): restore u_fl_/u_lk_nk_ only, at clock_taps + POST_CTS.
- intel1 clone /srv/opentallas-scratch2/claude/latch-swap-0045 commit ae39f0a78d4: tools/die_plan/latch_restore.tcl (name-free: every
  DFF[HL]Qx4 -> D[LH]Lx3 same Vt, legal at same origin; incremental GRT at post_grt; unrestorable -> FAIL_LATCH_SWAP + stage error),
  gen_phys latch_restore_hook_lines chains it after the kit's own POST_FLOORPLAN/POST_RESIZE/POST_CTS/POST_GLOBAL_ROUTE hook;
  signoff.py latch_swap check (6_final.v DFF[HL]Qx4 > synth -> blocking FAIL; NOT RUN does not block); test_latch_swap.py (6 pass).
  Not covered: core-kit generators outside gen_phys (gen_core_kit_kv, S81/QC/HBM core run_kit) -> only the signoff.py backstop.
