# DSpark (V4.1 MTP) on the V4.1 HBM comparator — RTL, default-off

Branch `claude/dshbm-dspark-rtl-20261003`, from `origin/main` 298ba9d79.
DeepSeek-V4.1's `mtp.0-2` form one DSpark block drafter. The golden for this work is
`tools/hdc_golden_v41.py`, `Model.generate_spec` and `Model.draft`, which commit 328b5fff checked at ISA level.

## What is new (all opt-in; nothing existing instantiates it)

| File | Role |
|---|---|
| `rtl/gpu/dshbm/ot_dshbm_dspark_ctl.sv` | The control loop. Runs prefill, then per step: draft (3 stages and the LM head as engine commands), then `g` serial Markov steps, then a layer-major verify of `g+1` positions, then accept (reuses `ot_hdc_accept`), emit, and commit `n <- n+1+a`. |
| `rtl/gpu/dshbm/ot_dshbm_spec_state.sv` | Position-indexed state addressing. The window and DSpark rings are `W+PMAX` slots, compressor slots `r_max+PMAX`, token history `NG+PMAX`, and compressed rows are linear. Rollback is therefore one register write. |
| `rtl/gpu/dshbm/ot_dshbm_accept_port.sv` | Accept stage port. `ACCEPT_LEAF=1` REUSES Codex's protected DS MTP accept leaf `rtl/experimental/ds_mtp_accept_20261003/ot_hdc_mtp_accept_guarded.sv` (89bf0783a/6fc0a3954, unmodified: start/TOKX/AMAX/ACCEPT, output ACK, end-of-step fence); `ACCEPT_LEAF=0` uses `ot_hdc_accept`. No accept arithmetic of our own. |
| `rtl/gpu/dshbm/ot_dshbm_argmax.sv` | SM epilogue argmax with exact `numpy.argmax` semantics. Adds the Markov bias through `ot_gpu_fadd`. |
| `rtl/gpu/dshbm/ot_dshbm_expert_union.sv` | Union of a pass's per-position top-k, with per-expert column masks, feeding W19's `ot_gpu_expert_fetch`. |
| `rtl/gpu/dshbm/ot_dshbm_dspark_top.sv` | Composes the blocks above with two of W19's `ot_gpu_router_topk`. |
| `rtl/test/tb_dshbm_dspark.sv`, `rtl/test/tb_dshbm_argmax.sv` | Benches. |
| `tools/dshbm_dspark_trace.py` | Golden run plus bench script. Also captures the SM operands. |
| `tools/dshbm_dspark_rtl_campaign.py` | Argmax unit, loop bench, mutations, merge. |
| `tools/dshbm_dspark_sm_campaign.py` | Every SM matvec of a step on `ot_gpu_sm_v`, plus the full-shape DSpark shapes. |
| `tools/dshbm_dspark_model_compare.py` | RTL cycles against the speculation price (d2aff19ef). |

## Replay

```
export HDC_V41_ARITH=chunk8 OPENTALLAS_BUILD=/home/ubuntu/OpenTallas/build   # reduced-v2 checkpoint
T=/tmp/claude-1000/dshbm
# 1. golden traces (each asserts tokens + logits == Model.generate and committed state digest == AR state)
python3 tools/dshbm_dspark_trace.py --out $T/tr_dspark     --drafter dspark --ngen 16 --sm-steps 1
python3 tools/dshbm_dspark_trace.py --out $T/tr_forced     --drafter forced --ngen 24
python3 tools/dshbm_dspark_trace.py --out $T/tr_forced_w16 --drafter forced --ngen 32 --window 16
python3 tools/dshbm_dspark_trace.py --out $T/tr_dspark_w16 --drafter dspark --ngen 24 --window 16
# 2. control-plane RTL (Icarus)
python3 tools/dshbm_dspark_rtl_campaign.py argmax --out $T/parts/argmax.json
python3 tools/dshbm_dspark_rtl_campaign.py union --out $T/parts/union.json
for t in tr_dspark tr_forced tr_forced_w16 tr_dspark_w16; do for L in 0 1; do
  python3 tools/dshbm_dspark_rtl_campaign.py bench --leaf $L --trace $T/$t --out $T/parts/bench_${t}_leaf$L.json; done; done
python3 tools/dshbm_dspark_rtl_campaign.py bench --trace $T/tr_forced_w16 --mut 1 --out $T/parts/mut1.json  # must FAIL
python3 tools/dshbm_dspark_rtl_campaign.py bench --trace $T/tr_forced_w16 --mut 2 --out $T/parts/mut2.json
python3 tools/dshbm_dspark_rtl_campaign.py bench --trace $T/tr_forced_w16 --mut 3 --out $T/parts/mut3.json
python3 tools/dshbm_dspark_rtl_campaign.py bench --trace $T/tr_forced_w16 --wr 16 --out $T/parts/mut_wr.json
python3 tools/dshbm_dspark_rtl_campaign.py bench --trace $T/tr_forced_w16 --sr 2  --out $T/parts/mut_sr.json
python3 tools/dshbm_dspark_rtl_campaign.py merge --parts $T/parts/*.json --out results/rtl/dshbm_dspark_rtl_20261003/dshbm_dspark_rtl.json
# 3. SM element on every matvec of one speculative step (reduced) and on the full-shape DSpark shapes
python3 tools/dshbm_dspark_sm_campaign.py reduced --ops $T/tr_dspark/sm_ops.pkl --out results/rtl/dshbm_dspark_rtl_20261003/sm_reduced.json
python3 tools/dshbm_dspark_sm_campaign.py fullshape --out results/rtl/dshbm_dspark_rtl_20261003/sm_fullshape.json
# 4. measured vs model
git show d2aff19ef:results/speculative/v41_hbm_speculation_methods_20261003/inputs/w19_hbm_token_compose_71b3ffc5.py > $T/composer.py
python3 tools/dshbm_dspark_model_compare.py --composer $T/composer.py --fullshape results/rtl/dshbm_dspark_rtl_20261003/sm_fullshape.json \
  --argmax $T/parts/argmax.json --bench $T/parts/bench_*.json --out results/rtl/dshbm_dspark_rtl_20261003/model_compare.json
```

## Results: control plane (Icarus 12, ot-agidock128; the argmax and union units ran on Icarus 11, locally)

All golden traces assert three things against `Model.generate`: the emitted tokens are equal, the logits are bit-equal, and the committed state digest equals the autoregressive (AR) state.

The benches replay the golden's engine events against the RTL. Each run checks:
- every command;
- every gather of window, DSpark, compressor-slot, index-key and selected rows (an FNV fold of the content tags);
- the router top-k ids;
- the expert union and its masks;
- every streamed SMEM line from `ot_gpu_expert_fetch` and the HBM model;
- every argmax;
- the emitted tokens and the per-step accept count;
- 48–51 FINAL gathers at the last committed position against the AR state (exact rollback).

| Trace | Accept unit | Result | Steps | Tokens | Accepts | Gathers |
|---|---|---|---|---|---|---|
| dspark W128, 16 tokens | leaf, hdc | PASS, PASS | 15 | 16 | all 0 (seeded weights) | 8,864 |
| forced W128, 24 tokens | leaf, hdc | PASS, PASS | 8 | 24 | 0,1,2,3,4,5,0,1 | 5,057 |
| forced W16, 32 tokens (ring wraps) | leaf, hdc | PASS, PASS | 10 | 32 | 0..5,0..3 | 6,134 |
| dspark W16, 24 tokens | leaf, hdc | PASS, PASS | 23 | 24 | all 0 | 13,184 |

Mutations. Every one is DETECTED with both accept units:

| Mutation | How it is caught |
|---|---|
| commit `n+2+a` | command mismatch |
| bonus `t_{a+1}` | token mismatch |
| accept ignores the last draft | accept mismatch (hdc unit) |
| window ring `WR=W` | 480 gather mismatches and 43 FINAL mismatches |
| compressor slot ring `SR=r` | 350 gather mismatches and 4 FINAL mismatches |

So the speculative ring headroom (`W+PMAX`, `r_max+PMAX`) is what makes rollback exact.

Argmax unit:
- 22/22 exact against `numpy.argmax`, covering ties, -0/+0, NaN, inf, subnormal and Markov-biased rows.
- Full shape: one SM's 43 biased logits take 18 cycles, the die's 32-SM merge 16 cycles, and a 4,040-row stream 517 cycles.

Union unit:
- 8/8 exact (384 experts, top-6, 6 positions).
- The first id comes 1 cycle after flush; a union of 27 drains in 39 cycles.

The control loop's own cycles (outside engine commands) are 840–1,900 per run including prefill. That is about 60 cycles per step, roughly 50 ns, which is negligible against a pass of about 750 us.

Claim boundary: the engine side (SM matvecs, attention, hyper-connections and norms) is replayed from the golden. The SM matvecs are checked separately on `ot_gpu_sm_v` (below). No P&R and no SS/FF figure is claimed.

SM element (`ot_gpu_sm_v`, Icarus 12.0, ot-epyc1tb, chain `jobs/chain.sh`, both rc=0; every `source_sha256` entry matches 0d70f912c; collected 2026-10-04):
- `sm_reduced.json`: PASS, 2,159/2,159 SM passes of one DSpark step exact (2,595 simulations; phases D 84, DH 1, MK 5, SEED 4, V 2,064, VH 1), 0 accumulator/output mismatches, no fault or timeout; ops pickle sha256 3e427858....
- `sm_fullshape.json`: PASS on released weights, 0 accumulator mismatches: Markov head (bf16, K 256, 43 rows, 1 col) 560 cycles; LM head 5 slots (bf16, K 5,120, 43 rows, 5 cols) 3,671 cycles; main_proj 6 positions (fp8, K 15,360, 2 rows, 6 cols) 449 cycles.
- Not done: `tools/dshbm_dspark_model_compare.py` composition (no per-user rate is claimed from these records).

