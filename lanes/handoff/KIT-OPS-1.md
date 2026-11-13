# KIT-OPS-1 handoff (kit-wave operations lane; COORD is the coordinator) -- 2026-11-13 01:31 PST

## Done 11-13 (RESULT posted for each)
- (1) q_su30 held + stopped (00:11).
- (2) HBM pEv10 (01:16): 8 types launched. Event pEv10, plan epyc8:/srv/opentallas-scratch2/claude/kit-ops-1/hbm_pEv10/plan/die_plan.json (b334c92f7a84), src kw45/src_hbm_main_7073a6b4a5 (plain archive + RA=0 overlay), kit_rtl bind_out hbm_pEv10/bind_w, asbuilt hbm_pEv10/asbuilt_kitops1w.json. Revert = hbm.prev_kitops1_pEv10. Switch script: scratchpad hbm_pEv10_switch.py.
  OPEN: epyc7 is out of hbm.gen_hosts (gen_hosts_prev_kitops1_pEv10). The rsync to epyc7 is still running from epyc8 (hbm_pEv10_copy.out; the sequential copy_units then re-scans intel1/epyc2, which is harmless). When RC epyc7 shows for both units, run manifest2.sh on epyc7 and compare (src a5e5a0bcd0adab20, pkg f3f8317d34809fff, bind_w 83f253e26a3ae447; asbuilt_kitops1w 98e742441d1f7acf). Then copy bind_w + asbuilt_kitops1w + die-hbm-92-su/exp/bind_e0/asbuilt.json if missing, and restore gen_hosts.
  Asked COORD: which of the 42 standing holds on changed types pEv10 resolves; whether to add ot_hnx_fused_hub_n4ext to plan_core_items.
- (h) HEAD rp18r2 (01:27): plan kit-ops-1/head_rp18r2w/prep/source_plan.json 6d283b65ff9a; hd_spn + hd_mesh launched. Revert = s81_head.prev_kitops1_rp18r2.
- Train 29 merged: the S81 proof overlay line is dropped (an appended DROPPED line in KITOPS1_OVERLAY.txt, 5 hosts).
## Standing
- RA=0 overlay: drop when the wave src moves to a main containing train 30 (backups kit-ops-1/ra0/bak).
- Awaiting COORD: the 6 QC sle/slw_st kits (DIE-QC-100 WAIT-FORM).
