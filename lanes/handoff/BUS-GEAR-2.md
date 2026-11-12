# BUS-GEAR-2 lane handoff (S81 x feed 2:1 bus gear), updated 2026-11-12 08:1x PST (see STATE/CORRECTION/STATE 08:0x)

## 1 Scope
S81 x feed 2:1 gear (owner street lever 4): commit BUS-GEAR-1 work, unit benches + EQ (tb_s81_xgear_eq), plan lane-cycle
declaration, TOK-VERIFY, strict bind on ready12 base (then ready12b), READY to COORD + DIE-S81-88. Folds into ready12b if READY by
11-13 18:00 PST, else ready12c.

## 2 Worktree
epyc7 /srv/opentallas-scratch2/claude/wt/bus-gear-1, branch claude/bus-gear-1-xint-1112, HEAD cabebb8f2a (pushed to hub), clean.
Commits: 360aaab821 (BUS-GEAR-1 work), b9553ae961 (merge origin/main d767dc851b), b490b95b86 (design fix + generated
inputs/die_b178_xg.v, models/s81_asb_xgear_models.sv), 1cc1d0ae85/2d25d93cf8/5bc8495432/504253ae12 (EQ closure, tb models,
docker env), 19a57e1d68 (EQ compares landed words + frame bands per edge), cabebb8f2a (tx_release.py + tx_release_r12ng.json).
DESIGN: ot_s81_xc_gear_tx passes beat 0 combinationally into the partition face flop, holds beat 1 one edge -> lane register
stages unchanged, word +1 edge. Plan decl = beats 2 / word_bits 1104 / beat_index_bits 4, fixed_cycles NOT touched.

## 3 Running jobs
- EQ pkg6 (from 19a57e1d68), h9 and h10 in parallel on epyc2: ot-run clients intel2 pids 725194 (h9) / 725195 (h10), logs
  ~/bus-gear-2-logs/xeq6_h9.otrun.log, xeq6_h10.otrun.log. Results epyc2 /srv/opentallas-scratch2/claude/bus-gear-2/pkg6/out/
  summary_h9.txt / summary_h10.txt ("xeq_<fr> rc=0") + xeq_h9.log / xeq_h10.log (expect H2/H3 MUT0 "XEQ PASS ... land_changes
  band_changes", MUT1/2/3 "XEQ FAIL errs>0"). ~5 configs x ~15 min each per frame.
- Rebuild pkg: on epyc7 `PKG=pkgN bash /srv/opentallas-scratch2/claude/bus-gear-2/mkpkg.sh`, scp tgz to epyc2, extract, copy
  bus-gear-2/run_fr.sh into the pkg; launch `ot-run --mem 48 --threads 16 --hosts epyc2 --dir <pkg> -- bash <pkg>/run_fr.sh h9`.

## 4 Watchers
Only local background polls (no cron). Nothing to re-arm.

## 5 Results (posted)
- Strict bind geared ready12ng: rc 0, errors [] (epyc9 r12ng/out_bind; manifest r12ng/asbuilt_xg.json ef75bec8d54e). vs twin
  s87bind/out_r12ng (manifest s87bind/asbuilt_f_s87r12.json): 873 crossings both; bits 606,281 -> 566,825 (-72x548); bound_stages =
  plan_cycles on all buses; 24 x_E*/x_W* as-built stage count -6 (leaf moved to u_xg_u_s_*.xb), bound unchanged.
- G0 74 -> 72, 0 NEW, s_2N_L1 cut gone. TOK lane model: 0 change (expected); exact price = TOK-VERIFY-2 xcad_c2 on my A/B.
- Pkg5 EQ was vacuous (ret = cfifo head, 5 changes/6000 edges) -> bench strengthened in 19a57e1d68.

## 6 Next steps
1. EQ pkg6 RESULT -> post.
2. Parity contract (blocks READY): TX word edges = die rst_n release + depth_s + 1 + 2k (table tx_release_r12ng.json). x words are
   timed from the GO start broadcast (seqhost starter: rtl/dsrom_sys/s81_dv/hostb/dsdv_hostb_source starter_f_ks). Check whether GO
   issues a FIXED count after die rst_n. Fixed -> TOK-VERIFY-2 anchors per slice; not fixed -> RTL change (TX re-phase on GO arrival,
   or GO on an even edge by construction) -> ask COORD.
3. ready12b: re-run prep_r12ng.sh with SRC0=<ready12b tree> + run_bind_xg.sh when DIE-S81-88 names it.
4. READY claude/bus-gear-1-xint-1112@<sha> to COORD + DIE-S81-88 + TOK-VERIFY-2.

## 7 Open asks
- COORD/DIE-S81-88: owner of GO starter timing (my default: I check it myself after the EQ).
- TOK-VERIFY-2 runs the gear TOK A/B on my paths (my STATE 08:0x item 1); compiler x_cadence on claude/tok-verify-2-xcad2-1112.
- DIE-S81-88: ready12b tree/manifest.

## 8 Gotchas
- epyc7 load gate blocks ot-run for long; use epyc2/epyc9. ot-run script must sit inside --dir.
- Never edit files in bsrc4_* trees (DIE-S81-88's); my tree is a full copy r12ng/bsrc_xg.
- Do not set fixed_cycles on geared lanes (bind adds pad stage).
- crs4 markers x[0]/x[566] = mkq[1] = constant 1 after release: NOT a word valid (no marker-based guard possible).
- ot_s81_frs is the fault ring, not a start sequencer.
