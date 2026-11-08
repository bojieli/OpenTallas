# HBM stale-core takeover 2026-11-08 02:22 PST

## Current step
N4 pad-selector structural pilot underway on own codex branch, collect healthy existing jobs. No merge/tag/POR changes.

## CODEX notes
- N4 vRF1b FINISHED NOT SIGNED (epyc4 scratch3/claude/die-hbm-89/n4rf/kits/n4_vRF1b/ot_hnx_fused_hub_n4ext_c756b86982b8): TT -11.83 ps/1, FF -8.07/43, slew TT40/FF19, DRC0, LEC EQUIVALENT57691. Cause measured from signoff/tt/sta.log: pb_q -> pad SRAM wd_in[68], nine fanout buffers, sink slew304ps, ~706ps clk-Q-to-SRAM including mux/wire. Not an ECO under strict 20-slew guideline. Actual GRT PNG viewed /tmp/dh89/n4rf/vrf1b_grt/congestion.png: W macro input edge and channel hotspots; pins <=0.259 track use. REDESIGN: same-edge pad_b replicated into 102 local selectors, each <=8 mux inputs. Opt-in OT_HNX_PAD_LOCAL_SELECT, 0 PIN CYCLES.
- CODEX took over N4 fix on codex/hbm-n4-pb-local-0222@603b03287ac4a53cc199e00d6f70e8d52e981652 (pushed hub). Own repo epyc4 /srv/opentallas-scratch3/claude/codex-hbm-stale-0222/repo. Small SAT lockstep PASSES; inverted-selector mutant FAILS. Also preserved predecessor vRF1b divider/node source, which had not been committed. New PLACE-only pilot kit E4 .../n4_local_vA, ot-run40GB/16T client3609529; controller log localhost /tmp/codex-hbm-stale-0222/n4_local_vA.otrun.log; no route until placed image read.
- lane_c vM2 FINISHED NOT SIGNED (epyc4 scratch3/claude/die-hbm-89/lanec_vM2): TT-52.26/56, FF-14.99/98, TT slew379 cap159, FF slew231 cap159, DRC0. Cause measured signoff/tt/sta.log: dx_q[2] -> ws[1][584], decoded control drives many muxes through BUFx2 tree; the structural hold-pad form adds HB4 to this now-critical data path. Actual vM2c/final_place_clock.png viewed: N/W density hot beside empty S corners, pin-driven floorplan. REDESIGN needed, no ECO. Proposed same-edge per-word write select replication; N/W pin move needs future die-owner plan event.
- topk vD HEALTHY epyc2 scratch3/claude/die-hbm-89/topk/kits/ot_hbm_idx_topk_link_static_fa4a6c51ad35-_vD, container hbmcore-..._vD_-1688555. In GRT hold repair u_bin_selected_line port flops ~-346ps; non-port/parent split must be read after route. Its pd3w+east-SRAM structural form already fixes old 4.6ns popcount path and W SRAM wall; keep running.
- programme_store_r10 vK0 + wave a7 HEALTHY intel1 scratch2/claude/hbm-cons-2/kits/ot_hgi_sfu_programme_store_r10_67927302fa18_vK0/... and hbm-wave-1105e4/.../attempt_7. Both GRT extra iterations (14/30 and21/30 at collection), no duplicate/retry.
- hfd_hgi_vms_glue_nw_t a11 HEALTHY intel1 scratch2/claude/kw25-wave-1106/runs/hbm/kit-wave/hbm/d44v/items/hfd_hgi_vms_glue_nw_t/attempt_11/gen/hfd_hgi_vms_glue_nw_t_bb7727c8971e; container ..._-2857001, GRT extra9/30; keep running.
- q2n2_vm vK0 HEALTHY TWO existing forms E2 scratch3/claude/hbm-cons-2/kits/ot_hfd_coll_q2n2_vm_core_e6416e70b87e_vK0/... container ..._-3310443, and E6 hbm-cons-1 ..._-1873150. E2 extra8/30; no relaunch of old hold-237ps form.
- lane1p existing E2 hbm-gaps-1/l1pm6/..._-2689749 still DRT, 6148 violations at70%; HARD-5 owns redesign plan event (taller outline, memories edge), not duplicated.
- hnx_rp3h_xs a8 DPL single-overlap failure already has merged final-DPL class fix20cff21bab; owed a9 relaunch handed to root wave/gaps agent (do not duplicate).
- tkm_tp192 root wave a12 queue rejected stale FAIL_PREFLOOR; actual failed LEC must be collected before fresh fixed kit.
- kshare v700685 wave queue rejected stale FAIL_PREFLOOR; v8e478a has LEC failure; inherited split tiles need collection, no automatic unchanged relaunch.
- h9b source OT_H9B_WQDIAG was already MERGED18:37 main c6424882a38 (branch9ab510cfbfc); predecessor PARKED wording "approved pending" was stale. Physical class remains to collect, no adopted plan event.
- pdie_serdes_rx_bm3_rest no live run in latest predecessor census; old vA TT-132.94/92, FF-137.22/8113, slew883, DRC6 is a large miss. No ECO/retry. Parent PHY binding class is KCLS-owned.
- dma_back_vp4 vM_rstpose_r4 was intel1 GRT at20:33 but no VP4 live container at02:2x; result location pending collection.

## Next
Read N4 pilot synthesis/LEC and PLACE image, ensure selector copies remain distinct physically, then CTS/GRT only after review. Continue collecting remaining tkm/kshare/VP4 and diagnose. Keep healthy GRT jobs running.

## Milestone 02:33 PST
N4 E4 waiter3609529 cancelled NOT RUN before admission (E4 admits6GB); own kit moved through hub to intel1 scratch2/claude/codex-hbm-stale-0222/n4_local_vA. New ot-run client3616233, --crit40GB16T, log /tmp/codex-hbm-stale-0222/n4_local_vA_i1_launch.otrun.log, waiting on measured admission36GB. No physical build duplicated. tkm_tp192 root handed to /root/gaps: current IQN3+REPLICA_MATCH LEC on own intel1 codex-tkm-root-lec-0222/kit, unit4013959-1794133925, 48GB4T; actual old6355 differs preserved, not just a queue failure.
