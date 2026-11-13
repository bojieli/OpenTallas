# KIT-OPS-1 handoff (kit-wave operations lane; COORD is the coordinator) -- 2026-11-12 20:21 PST

## Done (RESULT posted for each)
- KV re-kit vN2: coord 9fa10c7b844, 33 launches. Open: kv3_hg*/hgi*/hg_v1p* holds wait on GEOM-VIS-7.
- QC epyc7 SRC-INCOMPLETE restored. Branch f35e1e8835 = train 22, merged 8fc4972f54.
- (a) Missing sources staged from epyc9 into real dirs, manifest-verified. Units: S81 epyc7/epyc2 (bsrc4_r12ng 2a1f65c304baccee, bsrc4_main a510c318b31b6100, out_r12ng, asbuilt_f_s87r12); HBM epyc2/intel1 (src_hbm 34bbe65bc619a672, p37*, die-hbm-95/bind, t39w, sm1109, scratch3 codex-hbm-lat-1113/.../sfu_param_1113 e1a521a644418871). No SRC-INCOMPLETE from the 19:4x tick on.
- (b) 4 epyc5/6 rows closed as terminal FAIL with their verdict (superseded blocks); epyc5/6 were in no active host list. COORD accepted.
- (d) Live intel2 kw38/rt/tools/autopilot/kit_wave.py = main 21bad708b185 (md5 2952e6334476, new inode), backup kit_wave.py.bak-kitops1-train22-1112 (9036dc997ae4). Clean tick 19:22-19:30.
- (c) HEAD rp18 armed 19:57 (event head_rp18_1112, prepared plan 53d5e794105f at epyc8 + 4 gen hosts kit-ops-1/head_rp18c/prep, src kw45/src_head_main_2dd0d8c9fd + overlay). Backup kit_wave.json.bak-kitops1-headrp18-1112; revert = s81_head.prev_kitops1_rp18. 20:07 launches: hd_tile, turn_a, turn_b, eshim_rx, wshim_rx, wshim_tx, + hd_st_n4@2 (old retry entry). eshim_tx eligible next tick.
  Holds: hd_serdes, hd_ctl_n, hd_mesh, hd_st_str (changed, not in the re-kit list), hd_lep0N (window re-sign), hd_spn/hd_spn_end (export FAIL).
  rp18 defects (HEAD-96): orphan raw-export rows (hd_tile raw_7, eshim_rx raw_1, hd_spn raw_42, hd_spn_end raw_0/1) cause PORT_BIND FAIL for hd_tile and eshim_rx. Duplicate relay exports (hd_spn u_rrl_93/114, hd_spn_end u_rrl_194) make kit_rtl fail. On the HEAD-96 fix: re-run run_head_rp18c.sh-style prep in a NEW dir (no deletes), re-stage, switch plan, add retry entries hd_tile@1 hd_spn_eshim_rx@1, drop the spn holds.

## Open
- (e) S81 ready12b-A: waits for train 25 (rest of origin/claude/s81-r12ba-fin-1112, rtl acceptance = bsrc_r12bA_dst/rtl). Then: archive main -> kw45/src_s81_main_<sha>; check its S81 rtl = /srv/opentallas-scratch2/claude/s81-r12ba-fin/bsrc_r12bA_dst/rtl. Strict bind with events/s81_ready12bA_1112/asbuilt_ist.json; its absolute paths (base s81-leaf-floor-2/bsrc_main2_lfcs, type-safe-4 romq, codex-wave-bind-1106 map_b178, kit-wave/s81/bind_h10, wt/kw-fix-4-s81h10) must exist on the gen hosts or be rewritten to the archive. Stage src+bind to epyc7/8/9/2/intel1 by manifest, then switch.
  Launch set (epyc8 kit-ops-1/s81_cmp/sets.json): 71 RTL types (11 also block-changed), 16 block-only types to hold, leaf__t3 stays WAIT-FORM. 62 of the 71 sit under die holds and 31 are outside only_items. Releasing exactly those is part of the switch; list them in the RESULT.
- A main archive of 21bad708b185 is at epyc8 kw45/src_s81_main_21bad708b1 (pre-train-25; do not use for the bind).
