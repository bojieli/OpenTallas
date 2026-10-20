# KV-TXDP 10-19: mu-kv-ctx rebase on origin/main 34428d840 + KV MU image TXDP resolution

Bench (fleet ot-epyc8, Verilator 5.050, run_mu_kvctx.sh on the rebased tree): MU_KVCTX_PASS; kmut 1/2/3 + rmut 1 each
MU_KVCTX_FAIL (witnesses *.out here). MU_KVCTX BENCHES: PASS.

D2D_TXDP_K: the correct word is 0x03030416 [22,4,3,3] (= main 6c8b3c908 = KV GEN9 claude/kv-gen9-1019 3923bb422).
- Every KV source (main, GEN9, QW-TOK3 975074bdd, mu-kv-ctx) instantiates qkd_native_attention_programme .LAND(1) in
  qkd_kvs_tiles_hroot_ff_k.sv, so layer_compile.kv_codec_edges = 2 (ATTN_LAND1 registered source, +1 edge).
- K0 = KS_TXS 9 + codec 2 + SK_TXP 9 + PR 2 = 22.  Seam 2,2,2,3,2,2/11,11,9,9,9,9,9 (approved MU pair seam).
- Fleet recompile (../image_recompile_1019.log): D2D_MU=1 production.sh = committed d2d_cal_image_mu.svh byte-identical
  (sha e7d4d2d0...); D2D_MU=0 = d2d_cal_image.svh byte-identical (f9d7818c...); D2D_KV_CODEC=1 diagnostic gives
  0x03030415 [21] and is byte-identical to QW-TOK3 975074bdd's image (blob 9ea2b27a0): 975074bdd was compiled on a
  branch without 367d817b0 (codec read from .LAND), i.e. codec 1 -- stale.
- QW-GEN3 7493fff78 'K 23': its compiled_L1 used --kv-stages kv_kvs14c_relay_stages.json.gz (old kvs14c KV die,
  SK_TXV/TXP 11, torn K bundles) -> 9 + codec + 11 + 2 = 23. Recompile with the GEN9 KV seam (SK 9) -> 22 = 0x03030416.
