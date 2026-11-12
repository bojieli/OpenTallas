# BUS-GEAR-2 lane handoff (S81 x feed 2:1 bus gear), updated 2026-11-12 08:2x PST (see CORRECTION 08:09, STATE 08:13, ASK 08:1x)

## 1 Scope
S81 x feed 2:1 gear (owner street lever 4): commit BUS-GEAR-1 work, unit benches + EQ (tb_s81_xgear_eq), plan lane-cycle
declaration, TOK-VERIFY, strict bind on ready12 base (then ready12b), READY to COORD + DIE-S81-88. Folds into ready12b if READY by
11-13 18:00 PST, else ready12c.

## 2 Worktree
epyc7 /srv/opentallas-scratch2/claude/wt/bus-gear-1, branch claude/bus-gear-1-xint-1112, HEAD 877cfc14f1 (pushed to hub), clean.
Commits: 360aaab821 (BUS-GEAR-1 work), b9553ae961 (merge origin/main d767dc851b), b490b95b86 (design fix + generated
inputs/die_b178_xg.v, models/s81_asb_xgear_models.sv), 1cc1d0ae85/2d25d93cf8/5bc8495432/504253ae12 (EQ closure, tb models,
docker env), 19a57e1d68 (EQ compares landed words + frame bands per edge), cabebb8f2a (tx_release.py + tx_release_r12ng.json), 877cfc14f1 (TX framed by xw_v = x[1]/x[567], sticky flt into u_frs_<slice>_C NL+1, die_b178_xg.v regen, EQ bench v3 + MUT4, TX smoke run_tx_smoke.sh).
DESIGN: ot_s81_xc_gear_tx passes beat 0 combinationally into the partition face flop, holds beat 1 one edge -> lane register
stages unchanged, word +1 edge. Plan decl = beats 2 / word_bits 1104 / beat_index_bits 4, fixed_cycles NOT touched.

## 3 Running jobs
- EQ pkg7 (877cfc14f1) h9/h10 on epyc2: ot-run clients intel2 pids 1329158/1329159, logs ~/bus-gear-2-logs/xeq7_*.otrun.log;
  results epyc2 .../bus-gear-2/pkg7/out/summary_h9.txt|summary_h10.txt + xeq_h9.log|xeq_h10.log. Expect MUT0 SEED1-4 PASS (H2), SEED1-2 (H3);
  MUT1/2/3/4 FAIL.
- v2 strict bind epyc9: ot-run client intel2 pid 1344101 (log ~/bus-gear-2-logs/bind3.otrun.log), script r12ng/rebind_v2.sh, log
  r12ng/rebind_v2.log + r12ng/bind.run; out r12ng/out_bind (v1 kept in out_bind_v1, asbuilt_xg_v1.json).
- Rebuild pkg: on epyc7 `PKG=pkgN bash /srv/opentallas-scratch2/claude/bus-gear-2/mkpkg.sh`, scp tgz to epyc2, extract, copy run_fr.sh in.

## 4 Watchers
Only local background polls (no cron). Nothing to re-arm.

## 5 Results (posted)
- Strict bind geared ready12ng: rc 0, errors [] (epyc9 r12ng/out_bind; manifest r12ng/asbuilt_xg.json ef75bec8d54e). vs twin
  s87bind/out_r12ng (manifest s87bind/asbuilt_f_s87r12.json): 873 crossings both; bits 606,281 -> 566,825 (-72x548); bound_stages =
  plan_cycles on all buses; 24 x_E*/x_W* as-built stage count -6 (leaf moved to u_xg_u_s_*.xb), bound unchanged.
- G0 74 -> 72, 0 NEW, s_2N_L1 cut gone. TOK lane model: 0 change (expected); exact price = TOK-VERIFY-2 xcad_c2 on my A/B.
- Pkg5 EQ was vacuous (ret = cfifo head, 5 changes/6000 edges) -> bench strengthened in 19a57e1d68.

## 6 Next steps
1. EQ pkg7 + v2 bind RESULT -> post; compare v2 bind vs v1 (expect same crossings/bits; frs NL+1 only).
2. DIE-S81-88 one-line confirm of x[1] / x[567] = v (my ASK 08:1x). I verified all 13 xw4 definitions share the layout.
3. ready12b re-run (prep_r12ng.sh with SRC0/AB0 for ready12b + rebind) when DIE-S81-88 names it.
4. READY claude/bus-gear-1-xint-1112@<sha> to COORD + DIE-S81-88 + TOK-VERIFY-2 (die HELD until EQ+bind+confirm pass).

## 7 Open asks
- DIE-S81-88: confirm x[1]/x[567] = v, v=1 only on word edges; ready12b tree/manifest.
- TOK-VERIFY-2: gear price A/B on my paths (08:0x STATE item 1), compiler x_cadence branch claude/tok-verify-2-xcad2-1112.

## 8 Gotchas
- epyc7 load gate blocks ot-run for long; use epyc2/epyc9. ot-run script must sit inside --dir.
- Never edit files in bsrc4_* trees (DIE-S81-88's); my tree is a full copy r12ng/bsrc_xg.
- Do not set fixed_cycles on geared lanes (bind adds pad stage).
- crs4 markers x[0]/x[566] = mkq[1] = constant 1 after release: NOT a word valid. Word valid v = x[1] (= x[567]).
- There is NO go tag in x (go/go_tag are frame-local, cfg7_seq). COORD's option (1) became (1') = framing on v.
- EQ: bubble upper beat is don't-care (RX OGATE 0); compare landed words only on R-valid edges.
- ot_s81_frs is the fault ring, not a start sequencer.
