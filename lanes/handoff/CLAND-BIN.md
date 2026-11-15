# CLAND-BIN handoff (2026-11-15, lane Sonnet)
Branch claude/cland-bin-1115 @3d2854f4fab on hub (new branch off claude/fable-genbug-1115-1 @4e7f20bccb8). Clone intel2 /srv/opentallas-scratch2/claude/cland-bin/wt (sparse). Proof kits + logs: epyc2/7/8/9/10/intel1 /srv/opentallas-scratch2/claude/cland-bin/{proof,proof_eq}; intel2 ~/cland-bin-logs/.

## State (STATUS line for FABLE-CLOSURE-STRATEGY / DIE-QC-103)
- G2 is OPT-IN (OT_CLAND_BIN unset/0 off, =1 beside ring, =eq equal-hop at OT_CLAND_BIN_FRAC 0.5 of ring -> anchored load). Not default: eq proof does NOT show all hops <= 405 um.
- cbf_q01 eq proof (epyc2, place-only, hop_census on 3_place.odb), MEASURED:
  | | wave | G2 beside ring | G2 eq |
  | ring -> u_bin over 405 um | 1,024 of 1,032 (max 721) | 0 | 255 of 1,032 (max 739) |
  | u_bin -> u_st over 405 um | - | 1,784 of 1,792 (max 850) | 179 of 1,792 (max 489) |
  | type over-reach hops | 3,583 | 4,246 | 2,816 |
  OT_CLAND_BIN: 1,274 u_bin FIRM, longest planned hop 358.1 um, 275 bits without an anchored load left to GPL (those are the 255 ring->u_bin hops; b_q-only bits have no tap pin within 2 ranks). The 179 u_bin -> u_st hops (max 489) are u_st registers GPL pulled off the line (b_q also feeds the next station).
- kv3_hub_Wo with OT_LAND_RESERVE=1 (epyc2): both literal-local-reset bands placed, OT_CLAND placed 171,422 cells, global place passed, now in 3_5 detail place. Confirms the LAND_RESERVE cause; the generator/config should set OT_LAND_RESERVE=1 for that kit. (Kit there ran the old default-on G2 block, 0 captures.)
- c1x_C__t1 proof: running on epyc7, in 3_3 global place.
- u_st plan site: the hook side can take it: anchor = a plan site instead of the walk (a `cland_bin_sites` name->xy table beside ft_bit_sites.tcl), which would remove the 275 unanchored bits and the 179 pulled u_st. NOT built; I have not read the generator side, so whether gen can emit u_st sites is unverified. Needs DIE-QC-103 to say where the sites come from (plan stations list).
- G6: OT_FT_LANE_GATE line (reach+5 %, per-slot worst, displaced-station split) added, advisory unless OT_FT_LANE_GATE=1. S81 leaf t56 cause NOT traced (results cleaned); read the new line on the next S81 run.

## Next
1. c1x_C__t1 census when its place ends (log ~/cland-bin-logs/proof_c1x_C__t1.log); kv3_hub_Wo place end.
2. Decide u_st plan sites (above); then eq default-on only if every hop <= 405 um.
3. Coordinate: TYPE-QCCB-GEN owns core_input_chain.tcl (untouched here). GENBUG-IMPL: install nothing yet, G2 opt-in; face_flops.tcl G6 change is safe to install.

- 2026-11-15 CLAND-BIN CHECK epyc7: two c1x_C__t1 openroad global_place = two different dirs. PID 839846 container dpkit-dsdv_slice_c1x_C__t1-1935886 mounts /srv/opentallas-scratch2/claude/cland-bin/proof/dsdv_slice_c1x_C__t1 (MINE, the proof, 173% CPU, log growing). PID 161160 container dpkit-dsdv_slice_c1x_C__t1-1525696 mounts the wave kit items/dsdv_slice_c1x_C__t1/attempt_7 (S81 wave, not mine) - left alone. No stray of mine; kv3_hub_Wo on epyc2 at 103% CPU, not hung.
