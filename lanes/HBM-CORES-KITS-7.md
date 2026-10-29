# HBM-CORES-KITS-7 (lane file; successor of HBM-CORES-KITS-6, started 2026-10-29 02:39 PDT after Codex handback)

## 2026-10-29 02:39 PDT RESULT / PARKED
- Estimate GQ q1->ring: claude/hbm-cores-kits-7-1029@803d659e9 results/hbm_cores_kits_7 (see queue RESULT+ASK). Recommend paired-lot relocation (0 cyc); pipeline fallback costs -0.25..-0.33 % ds_ar (N=3/4), -0.66 % if q0 needs N=8.
- RING GRT DONE (epyc2 .../codex-hbm-ring-1029/kits_v2/ot_hfd_coll_q2_hard_v8g__ring_ag_71d2c363c67b-_c25c1029v2/run/results/.../5_1_grt.odb): overflow 0, setup -17.46/2 endp, FF hold -12.49 post-repair. NEAR MISS; no DRT.
- SUCCESSOR, collect (do not relaunch):
  - qcore M7 GRT: epyc2:/srv/opentallas-scratch2/claude/codex-qcore-m7-1029/kit (unit oth-ubuntu-326967-1793261912, docker codex-qcore-m7-grt). Read run/logs/.../5_1_grt*.log for overflow, the OT_HOLD_MM TT/FF lines and 5_1_grt.odb. Trial only, no DRT/adoption.
  - selector GEN resume2: intel2:/srv/opentallas-scratch2/claude/codex-selector-gen-1029 (unit oth-ubuntu-1020446-1793264339). Success = gen_trial.sh prints SELECTOR_GEN_PREFLIGHT_DONE, plus preflight.json and kits/mk_c20_result.json with rc 0. Stuck in yosys ProcDffPass (yosys PID 1122596); procsplit 75b86a6d9 awaits ROOT review.
  - TOPK LEC64: intel1 K=/srv/opentallas-scratch2/claude/codex-hbm-topk-1028/kits_v4/ot_hbm_idx_topk_link_static_4b8bc21191aa-_tree1028v4. Read K/lec_m64/lec.json (container codex-topk-lec64-1029). No TOPK P&R until the geometry is fixed.
  - Ring next step: root-cause the 2 setup endpoints (u_ring g_lane[3] u_add u_cd rd[1]) and the FF hold residual before any DRT.
