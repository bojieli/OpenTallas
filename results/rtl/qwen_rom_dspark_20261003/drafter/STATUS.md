# qwen-rom-dspark-drafter (STEP 3) STATUS -- HANDED OVER TO CODEX
Branch claude/qwen-rom-dspark-drafter-20261003 @ 4c2fe2242 (records in results/rtl/qwen_rom_dspark_20261003/drafter/).
RUNNING (local GPU + CPU, detached chain.sh): golden.json <- src/qwen_rom_dspark_drafter_golden.py (exit file golden.rc, log golden.log). Leave it running.
DONE: drafter facts (deepseek-ai/dspark_qwen3_8b_block7@03326e50, license not stated); ROM model (+1 4096x266 bank a tile = 30.84 mm2,
  r2 -> 822.8 mm2, 7.8 over 815; 8192-row re-bank fails SS 1.2 GHz; Markov w1 2.98 mm2 at IO); draft step model S=3 43,865-69,955 cycles;
  tau sample tau.json (B4 3.02 equal-weight 8 classes; 3.30 vs priced 3.13 on 5 priced classes; multilingual 1.96, creative 2.13; W8 = BF16).
NEXT: when golden.rc exists, copy golden.json to the branch records, fill GOLDEN_RESULT in REPLAY.md (tokens_equal per S/kv,
  max_abs_logit_diff), commit+push; then TP4 lowering order of the golden, drafter ISA program, the 815 fit decision, larger tau sample.
EPYC dir /srv/opentallas-scratch/claude/qwen-rom-dspark-drafter: stopped (no inference on EPYC); partial logs only.
