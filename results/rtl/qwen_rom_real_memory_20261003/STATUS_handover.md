# REAL_MEM Qwen ROM TP4 stream — STATUS (handover to Codex, 2026-10-03 06:25 PDT)

Host ot-epyc1tb, scratch /srv/opentallas-scratch/claude/realmem.  Branch claude/qwen-real-memory-runtime-20261003.
Everything below runs detached; jobs/MANIFEST logs START/END, jobs/<run>.log/.exit, runs/<run>.json + runs/<run>/token.log.

## Results so far (all bit-exact)
- Standalone service benches PASS (results/rtl/qwen_rom_real_memory_20261003/standalone/).
- real_p0 (token 0) and real_p255 (prompt token 6280): stages E (embedding ROM), L0, L1, L2 — every layer X on all
  4 dies bit-exact vs tools/qwen_rom_position_oracle_w12.py; the token K/V written back to HBM exact.
  Cycles: real_p0 L0/L1/L2 = 4960/5736/5348; real_p255 = 5075/5436/5587 (retained ideal 4669 L0, 4668 others).
  ideal (A/B, attempt-1 binary) L0: p0 4804, p255 4828.  Records: results/.../runs_attempt2_srcdrift (status=fail ONLY
  because src was re-synced mid-run: source_stable=False; numerics exact).
- Stall causes (MEMSTAT, per layer, die0): stall_bridge 425 (KV_VEC_WRITE_BRIDGE su_idle serialisation),
  stall_drain 278-1130 (token write-through waits for tagged HBM write-done; up to 552 cycles when a write meets
  an all-bank refresh), stall_kv 15 at P0, 170-339 at P255 L1/L2 (fill 1159-1210 cycles exposed by refresh).
- Defect found: ot_qwen_rom_rt_die_w12 leaves core HID/HALF/HD at 128/8/16; wrong RoPE row + K/V write address at
  any position != 0 (retained P0 token unaffected).  Fixed only in the REAL_MEM die.

## Running
- chain3 (src_v2 frozen + build_v2, source-pinned reruns): real2_p0, real2_p255, real2_p1023.
- chain2 (build_v2): ideal2_p0, ideal2_p255, ideal2_p1023 (A/B references).
- gold_big ENDED exit=143 (SIGTERM, cause unknown) after recording P255 and P1023; P2047 NOT produced, so the
  chains skip 2047.

## Next steps
1. When chain2/chain3 runs end: copy runs/{real2,ideal2}_*.json + token.log into
   results/rtl/qwen_rom_real_memory_20261003/runs/ (tools/qwen_rom_realmem_collect.py), summarise real-minus-ideal
   cycles per layer and stalls, update REPLAY.md results section, commit by explicit paths, push.
2. Optional: relaunch epyc_gold.sh (positions ...,2047) and a real2/ideal2 pair at 2047.
3. Never rsync into src/ or src_v2/ while runs are live.
