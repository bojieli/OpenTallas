# HEAD-SPE-EXPORT handoff (child of HEAD-TYPES-R2), 2026-11-16

## Task 1: SPEPRD3 export fix (DONE)
- Branch claude/head-spe-export-1116 @9dd182a70bd (worktree epyc7 /srv/opentallas-scratch2/claude/head-spe-export/wt; succeeds Codex WIP claude/head-speprd3-export-1116 @b5bd2c9e3a2). GREEN 76/76 on main dd34c34ecec, record intel2 ~/merge-queue/gates/9dd182a70bd5e6c1731e95a9b8f717b711499478.json. READY posted; awaits COORD approval.
  - prd_mk eco_post sources output_net_identity.tcl (renames the internal net that kept a moved output BTerm's name).
  - tools/die_plan/netlist_alias_check.py: re-read exported V; FAIL on assign/alias cycle (incl BUF/INV), self alias, 0 modules.
  - die_sta verdict FAIL on null seam (TT max / FF min), partially timed group (SEAM ... bits N), unreported group, 0 seams, part netlist alias cycle.
  - signoff netlist_alias check: advisory under R-MINIMAL (COORD: NOT in MINIMAL_GATES), blocking in legacy.
  - Export refusal: rtx-pro /home/ubuntu/head-spe-export/ffht_export_v2.sh (= ffht_export.sh + remote alias check before any copy; probe on old base REFUSE rc 8).
- Codex rename+RCX job E8 oth-ubuntu-548149-1794887400 finished: renamed=566, cells/nets unchanged. Its V had DECAP/FILLER/TAP; V rewritten from renamed ODB with -remove_cells (E8 spe_hold20_xw25/export_fix). Staged base E8 spe_hold20_xw25/export_final.
- Physical identity proof: DEF COMPONENTS/PINS/SPECIALNETS sha equal; all 104716 NETS identical after name map; SPEF 103624 D_NETs, total cap 425.769162 equal.
- NEW archive entry s81_head/hd_spn_end__nf15_speprd3_fix_1116 (BOTH stores, INDEX appended, odb sha e515fc1d..., provenance/ subdir). Old entry kept.
- Pair harness on corrected view (E2 /srv/opentallas-scratch3/claude/head-spe-export/run_pair_fix): PASS, link_i 566/566 bits timed, TT setup +521.21, FF hold +45.06 (old: link_i null, false PASS).
- Family finding (COORD relays to QC/KV owners, do not fix here): cyclic archived exports QC qfd_su_mem44_seg8_kv1 191, KV qkd_pv_fin_s8_pin 279, _/signoff_s8pin2b 279.

## Task 2: NF15c real-view die STA
- Run dir E7 /srv/opentallas-scratch2/claude/head-spe-export/nf15c_real (manifest.json, coverage.json, views/, parts/, spine_{TT,FF}.json from fdh_nf15c/proof tap_arrivals; top fdh_nf15c/tree/kit/sta/die_top.v b860b3989c4b asserted). Selector select_views.py: last INDEX row per type, signoff SIGNED or LOCAL_PASS_NEEDS_PARENT, port superset of NF15c stand-in (extras only cland_*/fclk_* or outputs, left unconnected), netlist alias PASS.
- 18 real: ctl_e host_e(he12h_drc2) host_n mesh_e spn spn_end(fix) spn_eshim_rx/tx spn_wshim_rx st_k5 st_m st_n3_transit st_n3_turn st_n4 st_str st_turn tile turn_a.
- 8 stand-ins: hd_ctl hd_host_w hd_lep0N hd_mesh hd_serdes (no signed entry), hd_ctl_n (archive NOT SIGNED), hd_spn_wshim_tx hd_turn_b (archive has ODB only, needs V/SPEF re-export).
- Launched ot-run client intel2 (log ~/head-spe-export-logs/nf15c_real.log); results run/die_sta.json, RUN.log.

## Results 2026-11-16 ~21:20 PST
- run1 (old hd_tile) and run2 (E7 nf15c_real2, TP2 hd_tile__nf15c_tp2_hold1_1116) both verdict FAIL (fail closed): 379/1182 seam groups untimed at TT and FF. Every untimed seam captures in a u_cland_* landing ring clocked by fclk_*/cland_* ports that the NF15c die_top.v lacks (0 refs). Real-view landed-hop timing needs a die top generated with the landing/fclk network. Old E2 fdh_st/real_sta had the same blind spot (355/1148 null).
- Timed seams only (run2): TT setup -396.17 (sp4->sp3/start_i, 1693 neg), FF hold -1442.41 (lk_HOST1->lk_ES0 arst_n/start_i on serdes stand-ins, 8814 neg), FF setup -197.51, TT hold -1626.15. Part netlist alias: all PASS.
- hd_spn NF13a view = NF15c pins exactly (6371 pins name/layer/centre, outline 587.52x2073.6); record E7 head-spe-export/hd_spn_pin_diff.json.
- Next owner: die top with landing network (HEAD-DIE-R / plan), then rerun the run2 recipe (run_nf15c2.sh, build_nf15c.py, select_views.py in the run dir). host_w coll_o0 port hold to check first when host_w signs.
