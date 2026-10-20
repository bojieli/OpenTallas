THIS subdirectory supersedes the parent model for Yosys formal import.
Use canonical_ASR_normalized.v SHA256 ee63e9a38cab2a9fa507f6fdc0480b04f047088a2f76464a5fca6182a9ba26d5 and canonical_DFF_normalized.v SHA256 cbba1c176afe1a03e677d21ee4e095c7b3d326689d8ec5ec46640d3e43a26254.
ASR event wires AND branch predicates both use asr_clear/asr_set, so PROC_DFF recognizes the asynchronous controls. The parent simulation-only model tested RESETN/SETN in the body and cannot be lowered by Yosys; preserve it as history.
Re-qualified544 ASR transition/configuration checks and128 plain HQN checks against the same source-pinned canonical PDK UDPs. Actual imported old-Yosys ASR still FAILS; actual imported plain HQN still PASSES.
Actual Yosys0.67 PROC+async2sync+clk2fflogic+check smoke PASS; exact version/hashes/cell inventory in proc_smoke/identity.json. No other cell types qualified.
Generator: tools/qwen_kv_die/canonical_seq_coupon.py
Smoke: python3 tools/qwen_kv_die/canonical_seq_proc_smoke.py --models THIS_DIR --out NEW_DIR --yosys YOUR_YOSYS
