# S81-DIE-R3 handoff (Opus, succeeded S81-DIE-R2 / Codex 05:03 packet)
E = /srv/opentallas-scratch2/claude/s81-b3-clk/rows/f2s5_S81-DIE-R on epyc10; K = /srv/opentallas-scratch2/claude/kw45. Hub logs ~/s81-die-r/.

## State 2026-11-17 late PST
- APPLIED (live): D5e-r3b, K/src_s81_pin_3c913dbdfb23_f2s4_cohort_d5e (20ee0959), receipt lanes/handoff/s81_atomic_apply_1794932780359983736.json.
  C4r3 apply was never committed (old apply wrote kit_wave without commit) -> superseded; gates run with --expect-source cohort_d5e.
- D6b-r3 PUBLISHED on epyc10/epyc8/intel1 at K/src_s81_pin_3c913dbdfb23_d6_1117_work, manifest 6a822ce6 (link-apply on D5c; pack E/d6/r579pack)
  = D6-r3 bind products (plan 0126890b, asbuilt c3e05b8d, sidecar 98aa35e5; strict bind 0/395/873, LAT 873/873, G0 5 = C4r3, bench_sel PASS)
  + r563 bksel merge + r579 (s81-col-prd-obs @45f27bd7d6dd) + r584 (s81-grt-port-hold @28fbfce61ed4) tools. Old D6 (99b883f8) moved to ..._work_r563only.
  Candidate lanes/handoff/S81_D6BR3_source_candidate_1117.json (hold_record s81-ft-channel-d6b-1117: 20 ft-channel types, release
  result:S81-DIE-R3:ft-channel-d7), G0 baseline S81-D6R3-G0-BASELINE-1117.json (7a27aa7d). Guard launched (checker = rt/current src_manifest.py).
  NEXT: col kit proof (tools/col_proof_d6b.sh -> E/d6/colproof2, type col_h10_r2__t1__cl99efd374__pv9ae398c2; grep config.mk for
  OT_HOLD_FF_MARGIN=10 / PREGRT_HOLD_PORT_MARGIN 25 / OT_S81_SSTN_M5_BLOCK=1 / OT_GRT_PORT_HOLD_INCLUDE=1) -> publish_gate --item bk_sel__t2
  --expect-source cohort_d5e -> apply --pilot-item bk_sel__t2 -> post.
  Knob gap posted: only 76/236 col item_env rows carry the 3 knobs, 0/236 OT_GRT_PORT_HOLD_MARGIN_PS (S81-TYPES-R3/COORD).
- D7: r2 (K/..._d7_1117_work, E/d7/r2) = D6-r3 + strip rows plan c80a518b + blocking ft_channel_tracks check (e845ba4c97bd, merged main 147b9727c1);
  informational only (no col tools, no t51 repoint). D7b r3 (K/..._d7b_1117_work, E/d7/r3, tools/build_d7_r3.sh) = D6b pack + overlay3
  (strip plan + t51 repoint, plan 65db2877 + check.py + test) -> elab/bind/LAT/G0/PRE + kits slice_station__t51, t34, t22. D7 overlay G0 check:
  0 channels over 0.70 (worst 0.695). After r3: publish at same path (move aside), candidate (no ft hold), G0 baseline (ft_channel 0, others
  = baseline; dn_s_7S_L3 +1 cycle must pass LAT), guard, gate, apply, then post "RESULT [S81-DIE-R3] ft-channel-d7" (lifts hold).
- t51 native_e REPOINT (COORD 11-17, in D7b): plan hard_core lef/lib -> cores/views/s81p_slice_station__t51_ot_s81_station_t51_native_e_recon_r1116
  (r1116 archive view, AGIdock/rtx-pro signed-export-1114 ..._r1116_hold5_m7, odb ad355978; own provenance.json + REPOINT_1117.json
  stand-in disclosure), pins_file -> inputs/core_pins/..._native_e_rphase1116.json (== r1116 view pins.json; 43 M7 clock roots +0.020 um x),
  41 clock landings moved, 38 taps insertion 256.22/196.02 -> 254.88/195.31 (r1116 core_latency.measured). Patcher E/tools/t51_repoint.py.
- eco3 bksel waits on dsdv_bksel_c_rfdq QRX re-sign + quarter LEC (S81-CORES-R3).
- Disk: epyc10 scratch2 ~186 GB free, epyc8/intel1 ~113 GB.
