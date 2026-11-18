# S81-DIE-R3 handoff (Opus, succeeded S81-DIE-R2 / Codex 05:03 packet)
E = epyc10 /srv/opentallas-scratch2/claude/s81-b3-clk/rows/f2s5_S81-DIE-R; E8 = epyc8 /srv/opentallas-scratch2/claude/s81-die-r3-e8;
K = /srv/opentallas-scratch2/claude/kw45 (on epyc2 a link to scratch3). Hub logs ~/s81-die-r/ and (intel2 root full 11-17 19:0x) /srv/opentallas-scratch2/claude/s81-die-r3-hub/.

## State 2026-11-17 19:20 PST
- APPLIED (live): D6z, K/src_s81_pin_3c913dbdfb23_d6z_1117_work, manifest 0ce242a9, plan 30c40fae (gate ab239565, apply e013593d,
  RESULT d6b-applied PASS 14827634). On all 4 gen hosts (epyc8 built; epyc10/intel1 D5c pack; epyc2 D5e pack E8/d6z/pack_d5e with
  overlay_drop fix E8/d6z/fix_overlay.py). Hold s81-ft-channel-d6z-1117 (20 types) still on until D7w.
- D7w (E8/d7w/r1, K/..._d7w_1117_work, plan 1698c515 = D6z + D7 strip rows + t51 native_w signed rc51f repoint): strict bind 0, LAT 873/873,
  G0 5 cuts (ft_channel 0), PRE PASS, t51 kit GEN+lint PASS. Baseline lanes/handoff/S81-D7W-G0-BASELINE-1117.json committed.
  Chain RUNNING: hub/d7w_chain.sh (out hub/d7w_chain.out): waits build -> E8/d6z/publish_w.sh (pack on D6z, all 4 hosts) -> hub/mk_cand_d7w.py
  -> commit -> guard -> publish_gate (--expect-source D6z) -> apply --keep-gen-hosts -> posts RESULT ft-channel-d7 PASS. On CHAIN_STOP: fix, rerun stages by hand.
- D8 (plan posted ffc70d19): D7w plan + TAP-GROUP-CAP-1 (E/tools/tap_split_family.py, 11 serdes, cap 1700) + CUT-WALL 12 rigid y moves
  (E8/d8/cut_wall_fix.py, log E8/d8/cut_try2.log): census 0 segments > 0.58, KITFIT 0, taps legal. Plan c9a952e0 (added_taps notes stripped:
  schema). Build d8b RUNNING (E8/d8b/r1, log ~/s81-die-r/build_d8b_e8.log; kits bk_sel__t2, t51, serdes t13/t2, leaf t43/t2).
  Then: G0 expect 0 ERRORs; publish on D7w after D7w applies (publish_w.sh with base D7w), candidate, gate, apply.
  d8 r1 tree (K/..._d8_1117_work) failed PRE on the note keys: superseded.
- Tools on main: claude/s81-cut-census-t51w-1117 @cf133c2b62c0 (cut_census, CUT-SEGMENTS-1 G0 list, t51w repoint), READY.
- Superseded trees (D6b/D6c/D6x/D7/D7c/D7x/D7z/d8) -> FLEET-OPS-R after 24 h.
