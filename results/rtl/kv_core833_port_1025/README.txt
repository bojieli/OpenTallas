Port check of the common833 controller-core COMPILER delta (Codex 6b0ac47a0 + bc751c01a, tool files only) onto
main 20b4554a0f + 12e2 MU/AGES1 ABI. Commit under test: claude/tok-qk-kv833c-1025@3f57063f21 (checked out on intel2).
Inputs: Codex's kv44 compile fixture (img44: kv_flags.env, die_ages_bound_padded.json, relay_stages_bound.json,
d2d_cal_image.svh) at intel2 codex-kv-token-1025/img44 -- OUT OF REPO, so this is a port-equivalence check only,
not rule-3 evidence for any token/boot claim.
TOK-QK 2026-10-25 19:47 PDT, ot-run intel2:
- hbm_duty.py with OT_KV_CONTROLLER_CORE=1: duty_core.json equal to Codex's duty_native_core.json in every field
  (all 128 PCs, layer period 6798 HBM edges, shape 8/11=0.7273 <= 0.73, token period 293376) plus the 2 new fields.
- kv_boot_v36.py compile --no-mu (= what 6b ran: old compile_ forced MU off): all 15 images/bundle files
  BYTE-IDENTICAL to Codex native_core_bundle (boot_bundle.json, target*.hex, layer_programme_image.svh);
  report/programme differ only in recorded source sha256s and the new native_die_config_words=0 field.
  COMPILED_NOT_QUALIFIED, token busy 290059, emb margin 1158.
- With 12e2 the compiler now honours the captured OT_KV_MU=1: the MU frame search (mu_calendar.kv_frame_search)
  at 833 on this img44 profile did not finish in 42 min (unforced) nor 10 min (OT_KV_MU_FRAME_F=3). Codex r9 MU
  compile (different tree/flags, legacy 625/768) took 14 s. OPEN: MU+833 image for the current bind.
Default OFF: without OT_KV_CONTROLLER_CORE the legacy 625/768 + K8/2 V8/3 constants are unchanged
(tools/qwen_kv_die KV test fail-set identical to main; test_rd_shape_candidate 2/2 PASS on and off).
