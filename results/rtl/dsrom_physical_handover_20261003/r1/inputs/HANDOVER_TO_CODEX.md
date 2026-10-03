# Handover from Claude to Codex (user directive 2026-10-03: "offload tasks to Codex; don't own everything")

Codex is not rate-limited and runs continuously, so it takes the long, waiting-heavy and iterative physical work and the HBM-side integration. Each item: branch, live state (STATUS.md), next steps. Apply FLEET_AND_FLOW.md: all 4 hosts by job type, ORFS 16-24 threads, hierarchical flow, detached jobs.

## Handed to Codex
1. **DS ROM die-level feasibility** (pairs with Maxwell/Archimedes). Branch `claude/dsrom-die-feasibility-20261003`; STATUS at ot-epyc1tb:/srv/opentallas-scratch/claude/dsrom-die-feas/STATUS.md. Scope: full-die floorplan with element black boxes (original q frame 510.84x126.9 may route once macros are aligned), pin access, top-level global route, PDN IR at 204 W hottest die, clock trunk skew including relay sites.
2. **DS ROM q-element routes and pipelining iterations** (Maxwell/Epicurus).
   - **Re-frame routes:** branch `claude/dsrom-qframe-20261003`; STATUS ot-epyc1tb:/srv/opentallas-scratch/claude/qframe/STATUS.md (A_r3/B_r3/C_r2_mig and D_r2 running; C at its own frame was converging before a VM OOM).
   - **Pipelining:** branch `claude/dsrom-qelem-pipeline-20261003` (R_cap0/R_cap1 at 20 threads). Target is signoff only (SS setup ≥0 at 60 ps, FF hold ≥0 at 25 ps), minimum stages, zero-latency fixes already exact.
   - **Price added cycles** into the DS model.
3. **DS HBM full-system integration and DSpark on SM.**
   - **Branches:** `claude/hbm-system-rtl-20261003` and `claude/dshbm-dspark-rtl-20261003` (STATUS under /srv/opentallas-scratch/claude/).
   - **Scope:** MoE dispatch, collectives, CDC at service rate, launch/completion, DSpark draft, 6-position verify with expert-union streaming, reusing your accept leaf, and the end-to-end DS HBM token with Kepler's numerics.
4. **Qwen near-HBM attention element P&R verdicts** (hub_r7, row_engine_r6 on epyc; row_engine_r4 on agidock). Branch `claude/qwen-nearhbm-attn-20261003`; STATUS ot-epyc1tb:/srv/opentallas-scratch/claude/nearhbm/STATUS.md. Exactness already PASS; collect SS/FF/DRC. If an element fails, deeper pipelining first, 0.9 GHz only if pipelining can't close. Use 8 row engines per stack (1,824 cycles/layer).
5. **Layer-parallel reruns** (clean one-layer wall time; AR256 NaN-fill). Branch `claude/layer-parallel-sim-20261003`; STATUS ot-epyc1tb:/srv/opentallas-scratch/claude/layer-parallel-sim/STATUS.md. Then build the DS V4.1 layer-parallel entry state (mHC 4-stream residual, window/compressed KV, indexer keys preloads; only L0/L20 images exist).
6. **Qualified DSpark acceptance post-processing.** GPU generation is still running locally (/tmp/claude-review-20261003/mtp_q/run, run_b2); branch `claude/v41-mtp-acceptance-qualified-20261003`. When generation ends, compute per-class tau, the blend with equal weights, the envelope, and rates. Use the LMSYS published values for chat/math/creative (Arena-Hard 3.78, GSM8K 5.24, Poetry 2.91; verify windows, V4-Flash) and measured values for coding, long-doc, multilingual, long agentic and assistant.
7. **Finalise the Qwen speculation re-check record.** Uncommitted results in /home/ubuntu/qwen-rom-spec-recheck-20261003 (branch `claude/qwen-rom-speculation-recheck-20261003`): add a test, commit, push. The decision is already taken (DSpark b4 + 2x attention adopted, gated).

## Claude keeps
- Disaster-risk checks: DS context capacity, control-loop clock ceiling, performance-vs-spec ledger, Qwen reticle fallback.
- Qwen full-die composition, the corridor gate and the DS edge index scorer.
- Qwen DSpark gate/build, and Qwen and DS ROM system RTL (including phase merge and the L0 diagnosis).
- Real-memory runtime, async collective, DS ROM DSpark RTL.

Report progress as runs and numbers in codex_notes.txt. Claude will integrate and review.
