# TOKSIM-S81C/MTPD -- MTP draft, draft head, head.argmax_merge (10-19)

## Draft head golden run (NEW, this lane)
- Bench: live head-return seam `tb_s81_bundle_token_return` (codex/s81-token-integrate-1019@98a2f06da; 128-row actual
  ROM group, ten ot_rom_4096x274_m8, ot_dsrom_head_bundle IOREG=1 SAFE=1, ot_rom_argmax_rows, ot_s81_bundle_token_return),
  the immutable built exe + ROM images of ot-epyc5:/srv/opentallas-scratch/claude/s81-live-head-return-1019/run
  (weights_slice_sha256 ee9236fc..., rank-0 head.weight rows 21888..22015 from the released checkpoint).
- The draft head IS this matvec: dv_layer_fixtures.py `draft.head{i} = V.mv(m.w["head.weight"], xn)` (same head.weight, K 5120).
- Inputs: MTP layer fixture (hdc_golden_v41 chunk8, DeepSeek-V4.1-Flash dba1be0a, 1M ctx, checks draft_logits_equal_model_draft)
  draft.head{0..4}.norm.scale (exact BF16). Checker: golden draft.head{i} logits of the same 128 rows (every returned logit
  word) + first-max token/bits of those rows. Driver tools/s81_dv/layer_prog/qf_producer/toksim_mtpd_draft_head.py.
- Job ot-epyc5 oth-ubuntu-604012-1792476740 (Verilator 5.050): 5 drafts x 3 owners PASS bad=0, age 8416 every case;
  mutant (head_d forced 0) FAIL bad=387 for every draft. Evidence draft_head_run/mtpd_draft_head.json, MTPD_draft_head.otrun.log.
- Also verified (read-only) the original HEAD-input run: its logits.hex = HEAD fixture head.lm_head rows 21888..22015
  (128/128 bit-equal), xa/xb = HEAD fixture head.norm.scale (5120/5120), token 21946 / 4173a558 = fixture next_token.

## Draft Markov (collected)
- HEADB fused_head_tp4 FH=1 (claude/tok-s81-headb-1018@641239174, ot_rom_argmax_rows same blob e0092764): draft0..4,
  129,280 fused lanes each, 0 bit mismatches vs MTP fixture draft.markov{i}.logits, argmax = golden draft tokens
  108193/8674/71/95391/12184; mutants mut_lg / fh0_draft0 FAIL. Measured fuse extra = 6 cycles a step.

## head.argmax_merge (collected)
- XDIE MU gate c_g1 (origin/claude/xdie-s81-mu-1019@eb0d31c63 record_c_g1.json, MU die ceaed19c4 endpoints, Verilator 5.050,
  PASS 12,096/12,096 beats bit-exact, in order, by deadline): argmax_merge AG 32 B E = [563, 564], E_meas 564 incl. the
  453 modelled PHY -> RTL part 111 (base record 82b1e956e: E [563, 572] -> 119). On-die leg 134 -> 140 already in LEG.
