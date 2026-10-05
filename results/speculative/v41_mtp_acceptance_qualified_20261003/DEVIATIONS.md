# Deviations from the pre-registered protocol

This file was written before any acceptance result was computed (2026-10-03, ~11:05 UTC). At that point batch 1 was at decode step 42 and batch 2 at step 20.

1. **Output length: 161 generated tokens, not 512.**
   - **Batch 1** (120 agentic prompts with greedy and T=1 twins, 240 traces) decoded at 220-450 s per step on the shared host. That host was running ORFS, Verilator and another agent's GPU job at a load of about 140 on 32 cores, and the per-trace decode path was CPU-launch-bound. Reaching 512 tokens would have taken more than 24 h.
   - **Batch 2** (96 prompts, 192 traces) was launched with `--batched-decode --stop-after-steps 160`.
   - Batch 1 is stopped after its step-160 save, so both batches end at the same length. The pilot also used 160 tokens.
   - Traces that hit EOS earlier end there, as before. Late-output acceptance (tokens 161-512) is not measured. The record reports τ over the first and second halves of each trace's output as a trend check.
2. **Supplementary thinking-on workloads not run.** `coding_humaneval_think` and `reasoning_math500_think` were dropped from batch 2 to save GPU time; they were never class values. The batch-2 core selection is `prompts_b2_core.json`, sha256 `b25e0167144418512afff2d817be85bd57b7d6588176b89898ddc653458cd515`: the pre-registered 144 prompts minus these 48.
3. **Batch 2 decode path.** Batch 2 uses `--batched-decode`, so its decode GEMMs see M = N rows. This changes rounding the way batch composition already does: validation on 40 traces showed 30 token-identical and divergences only at near-ties, with the same magnitude as the existing batch-composition noise.
4. **An unbatched batch-2 attempt was aborted during its prefill** (`run_b2_aborted_unbatched/`); no result was computed from it. An earlier attempt was killed by OOM at a 30% GPU cap, and batch 2 runs at 50%. A competing process held about 22 GB at the time.
