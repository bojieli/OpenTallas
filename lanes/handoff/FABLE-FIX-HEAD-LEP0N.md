# FABLE-FIX-HEAD-LEP0N (Fable, restarted 11-22 03:3x PST by COORD; pairing OPUS-FIX-HEAD-LEP0N-R8)

The 11-21 07:50 stand-down text of the first lane of this name is in git history of this file (and in -R2..-R7, OPUS -R8 handoffs).
Goal: hd_lep0N (+_w) signed off = HEAD complete. I diagnose + write the structural fix + build ONE sealed private kit. R8 keeps its builds.
Post with: POST_NO_RESOLVE=1 bash ~/coord/bin/post.sh FABLE-FIX-HEAD-LEP0N "..." (without it the post is redirected to R8).

## Dirs
- epyc9 lane dir L=/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-1122 (tmp/ringff_fix.py, trees/, plan/). Hub logs intel2 ~/fable-fix-head-lep0n-1122/.
- Base tree (Codex seal, epyc9 only): /srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r18e_split_s0 (b4f489665c04, plan sha256 e84371ca5dcf).
- My fork: L/trees/s81_head_r18f_ringff (ot-tree-fork of r18e, started 03:5x; log ~/fable-fix-head-lep0n-1122/fork_r18f.log).

## DIAGNOSIS (measured)
Failure history by form: uncut 2x2 (r11b/r16 wave) and shelf: GRT overflow flat + 98.9 % of the 400k cap -> type split W|E (R4-R7).
Split kits E7/W7 (F tree): CTS post-hook setup -1007 / -1465 on the unrelayed landing fault path (u_cland_*_i/u_fault_port -> u_cland_up_*_o/fault_o);
r18 added the status relays. r18b/c/d died in kit_rtl on tools (v1 stage groups, missing common_flow). r18e = first complete tree.
1. SETTINGS (W only, E is exact wave env): kit_wave.json item_env has no hd_lep0N_w row, so W builds with die_gen_env only:
   OT_PG_PIN_CHECK=1 (hd_lep0N: warn), no OT_PG_CELL_KEEPOUT=0, no OT_PG_TRACK_TRUTH_WIDE_SPACING=1, no OT_IO_HOLD=sender_min /
   OT_GEN_M8_GRANT=1 rows. Also plan clock.tap_window.per_port_ps / tap_offset.per_port_ps and die.layer_budget.type_m8_grant.type_guides
   name hd_lep0N only (old uncut tap names; advisory, die clock retargets the pieces).
2. STRUCTURAL (W): R7 tmp/recompose_merge.py ran CLP.compose(band_reserve='padded', band_ring='all', ring_ff_min_bits=0). Bands coll_i1 /
   coll_i2 of hd_lep0N_w lost ring_place=ff + spread (r16/r17b: ring:coll_i2@2.0666+ff, rect 45.36 x 206 on the pins). r18e tags are
   ring:coll_i1 / ring:coll_i2 = whole ring FIRM in netlist order (FABLE-FIX-S81-RINGS class; kit_preflight ring_ff only judges die s81),
   and coll_i2 is a 12.96 x 531.36 sliver [17.28,17.28,30.24,548.64] (pair 2 at x 34.56 leaves a 17-um W channel).
   r18e W placed DB (epyc9 .../opus-fix-head-lep0n-r8/r18e/hd_lep0N_w_dry, 3_place.odb f59f132d39c1): TT setup -495.73 (ctl_lap -> lap_ok,
   max_delay 416.5), -204.08 (g_oh -> ghi0 half cycle), -135.10 (tc -> wen), tns -62198, all in u_cland_coll_i2; OT_PLACE_WIRE_RATIO
   ghi1 -> ghi2 direct 1.9 um built 654.6 um; 40,751 FIRM cells. coll_i0 (ring ff) +392, coll_i1 +231.
   main _storage_band at ring_ff: coll_i1 legal [17.28,634.78,62.64,840.78] @2.0666; coll_i2 FAIL "required depth 23.76 um" (channel 12.96).
3. E piece: bands all ring ff; r18e E place still running at 03:5x (dpkit-hd_lep0N-734152 epyc9). E7 CTS: fault path -1007 (relayed in r18),
   coll_i3 fs_q -> wen -216 (fclk), lap_ok -155: re-read on the r18e E placed DB.

## FIX LEP-RINGFF-1 (L/tmp/ringff_fix.py TREE [--dry])
hd_lep0N_w bands: coll_i1 same rect [17.28,634.24,58.32,840.24] + ring_place ff + spread 1.8697; coll_i2 rect [17.28,110.16,30.24,336.96]
(pin window y 120-326) + ring_place ff, flops-only reserve 2134.84 um2 (band_use_ff 0.726). Also collector_local_sources band copies,
wave_prepare.prepared_plan_sha256. Dry on r18e: new plan sha256 c2f3d21378f6, die ring_place_missing 0.

## NEXT
1. Fork done -> ringff_fix.py on the fork -> plan_gate_pre check (as r18e/apply_r18e.sh, --ref-tools rt 6d2e187f0d65 or current), landing_band_core,
   landing_place tags (+ff), kit preflight.
2. item_env.hd_lep0N_w row (= hd_lep0N row) via kit_wave_edit, else --ab keys with --why.
3. private-spec s81_head hd_lep0N_w --tree fork --plan fork plan --goal finish --host epyc9 --lane FABLE-FIX-HEAD-LEP0N (seal default), run-item
   under systemd-run --user on intel2, ot-wait --durable. One kit only (W). E is R8's (r18e E run-item after its place).
4. Rows to R8 + COORD; flow fix: kit_preflight ring_ff must judge s81_head too (ot-push-main from a lane clone).
