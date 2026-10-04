# Qwen3-8B ROM DSpark in the system RTL: minimum components and the composed step

> **TAU SUPERSEDED (owner rule 2026-10-04).** `ctx8k/step_composed_ctx8k.json` is now composed at the third-party published tau (3.1445, `tools/third_party_tau.py`, `results/speculative/third_party_acceptance_20261004/`). Hand-written figures below that quote tau 3.0375 are the superseded self-measured composition: scale MTP tok/s by 3.1445/3.0375 = 1.0352 (and MTP J/token by its inverse); AR figures are unchanged. The off-target P255 `step_composed.json` was not regenerated and keeps 3.0375.

These records cover the Qwen3-8B ROM DSpark function in the system RTL. Everything is default-off and lives in successor files only. The pinned REAL_MEM sources, including `ot_qwen_rt_kv_fill_service`, are byte-identical.

The vehicle is the VPRM die, `rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_vprm.sv`, configured as follows:
- VPOS core, `ENABLE_ARP`, and the accept unit.
- KV goes through `rtl/hdc/kv/ot_qwen_rt_kv_mp_service.sv` and `ot_qwen_hbm_model_ack` (NPC 32, `WR_ACK`) on the REAL_MEM path.
- TP4, G 6,144, SW64.

It is run by `tools/qwen_rom_rt_vprm_w12.py` on ot-epyc1tb at `/srv/opentallas-scratch/claude/qwen-dspark-system`. The sources are `src-aec77a75f`, which contains the host model-eval-before-preload fix (the VPRM twin of 15778679a). The job list is in `components/comp.sh`.

## Target context (owner rule): P ~8,191 -- the headline record (`ctx8k/`)

These components supersede the P = 255 numbers below for any rate claim. Records: `ctx8k/step_composed_ctx8k.json`,
the per-job results `ctx8k/k_*.json`, `ctx8k/c_H*.json` and their `ctx8k/runs/*/token.log`.

Vehicle and path:
- The VPRM REAL_MEM die (`bld_dbg`: HEAD sources; the datapath is identical to `aec77a75f`, plus the fault
  observation port). The host evaluates every model before the stage-0 preloads (the VPRM twin of 15778679a).
- The adopted HBM_STREAM controller (081875cf2) cannot serve P >= 2048: `ot_qwen_rt_kv_stream_service` faults at
  pos >= 2048 and its stream map has one DRAM row per layer. The 8K components therefore run on the REAL_MEM tagged
  fill path, the same path as the realmem-ctx8k AR measurement. The AR layer here (P8187) is 14,574 cycles, which is
  identical to that record's P8191 layer.

Goldens (local GPU, `tools/qwen_rom_position_oracle_gpu.py --layers 1`, scripts in `ctx8k/scripts/`):
- A: the 8,192-token prompt, positions 8187..8191. P8191 reproduces the retained realmem-ctx8k golden bit for bit.
- B: the prompt to 8187, then three draft tokens [10952, 18065, 1269] at 8188..8190 that differ from the prompt's
  [20, 13, 15]. The drafts are all rejected.
- Drafter: `tools/qwen_rom_dspark_drafter_reencode.py` re-freezes the D0 program at start 8188; start 49 is
  reproduced byte for byte first. The golden (`tools/qwen_rom_dspark_drafter_layer_golden.py --kv-window`) uses a
  real-magnitude context window: the prompt's target layer-0 K/V, rows < 8188, per die.

| job | what | cycles | result |
|---|---|---|---|
| k_L0 | Verify layer 0. S1 is block 8187..8190 (np 4). The host commits 1 (a = 0), so rows 8188..8190 are rolled back. S2 is block 8188..8191 over the HBM the RTL left. | S1 24,320; S2 25,252 | PASS: 40 checks, 0 mismatches, no faults, `committed_len` 8188 |
| k_AR0 | Layer-0 AR (np 1) at P8187 | 14,574 | PASS, exact |
| k_D0r | Drafter layer 0, S = 3, start 8188, real-magnitude window | 30,611 | PASS: 16 checks, 0 mismatches, no faults |
| k_D0 | The same with the seeded synthetic window | 30,611 | X/K/V exact (16/16), but the ME fault flag is set (see below) |
| c_H0/H1/H2 | lm_head p = 1; verify head p = 4 with the accept unit (a = 0, and a = 3) | 2,999 / 11,993 / 11,993 | Position-independent; measured at P255 (above) |

The verify layer pays 3,249 cycles per extra position at 8K. The KV fill (131,032 sectors, about 10.4K cycles)
is shared by the 4 block positions.

Composition (`tools/qwen_dspark_step_collect.py --map`):
- verify = 36 x 24,320 + 11,993 = 887,513
- draft = 5 x 30,611 + drafter head 8,995 + priced ingest/Markov 7,875 = 169,925
- commit = 65
- step = 1,057,503 cycles
- AR token = 36 x 14,574 + 2,999 = 527,663

At tau 3.0375 (the owner 6-class equal blend of `tau_w8_S3_B4`; not measured here):
- **DSpark 3,447 accepted tok/s per user**
- **AR 2,274 tok/s**
- **1.516x**

The bounds are:
- A free drafter would give 1.806x.
- The verify layer breaks even at 39,466 cycles, so the measured 24,320 has a 38% margin.
- The priced terms are 0.74% of the step.

### Drafter fault root cause (`ctx8k/drafter_fault/`)

An instrumented debug-only build (`debug_only_trace_patch.py`; nothing in `rtl/` changed) shows the source. The ME
lane BF16 multiplier `ot_qwen_w12_bmul` fails closed (result 0, fault) on products below 2^-133.

The seeded synthetic E4M3 history gives subnormal softmax probabilities:
- At P49 there are 2,083 such deep-underflow PV products.
- At 8K there are 1,586,817.

They are absorbed in the sums, so every output is exact. This is the existing lane contract, shared with the AR
layers; it is not a DSpark bug. A real-magnitude window has 0 subnormal products, and k_D0r runs fault-free with
the same 30,611 cycles.

### Verdict (target context)

**Mandatory function: CLOSED at 8K, exact, fault-free.** The closure covers:
- the multi-position KV service with per-position visibility at P8187..8191;
- accept with a rejection, and accept with full acceptance (heads);
- commit, and rollback of the rejected KV rows;
- the next block over the RTL-left HBM;
- the drafter as a separate component.

**Rate: ADOPT, 1.516x per user at 8K (3,447 vs 2,274 tok/s).**

The following remain unvalidated:
- near-HBM attention, or HBM_STREAM, at 8K: neither is integrated with VPOS;
- the priced drafter ingest and Markov terms;
- tau, which comes from 3 prompts a class;
- SS/FF closure of the VPOS/ARP/accept/mp-service logic.

The P = 255 composition below (0.833x) is superseded: short context hid the KV cost that the verify block amortises.

## Components (each bit-exact against the GPU ISA golden on all 4 dies)

The golden is `tools/qwen_rom_dspark_oracle_gpu_w12.py` on the 256-token prompt, from the `claude/qwen-dspark-oracle-20261004` records.

| job | what | cycles | result |
|---|---|---|---|
| c_L0 | Decoder layer 0. S1 verifies block 255..258. The host commits 1, so 256..258 are rejected and rolled back. S2 verifies block 256..259 over the HBM the RTL left behind. | S1 12,520; S2 13,872 | PASS. X of 4 positions x 4 dies and the K/V blocks are exact in both steps. `committed_len` is 256. The rejected rows are rewritten before they are read. |
| c_AR0 | Layer 0 AR (p = 1) at P = 255, same path | 4,338 (+7 start) | PASS |
| c_H0 | lm_head, p = 1 | 2,999 | PASS |
| c_H1 | Verify head p = 4 plus the accept unit, step 1 | 11,993 | Argmax is [98951, 484, 3856, 334] = oracle. The accept unit gives a = 0 (3 drafts rejected), bonus 98951. |
| c_H2 | Verify head p = 4 plus accept, step 2 | 11,993 | Argmax is [3856, 334, 320, 1958] = oracle. The accept unit gives a = 3 (all accepted), bonus 1958. |
| d_D0 | Drafter layer 0 (packed DSpark drafter program, S = 3, start 49) | 20,112 | 3 slots x 4 dies X and K/V exact against the corrected golden (see below). The core fault flag rises at cycle 4,657 in segment 0 on all dies; see "Open" below. |

### Golden bug fixed

`tools/qwen_rom_dspark_drafter_layer_golden.py` decoded the segment descriptors with the 8-bit count. The drafter's all-reduces carry 768 words, with the high bits in [23:20]. The old golden therefore folded only slot 0 and kept per-die partials for slots 1 and 2, which is why c_D0 "mismatched".

The goldens were regenerated on the local GPU with the wide decode; `drafter_golden_fixed/` holds their manifests. Slot outputs now equal the RTL bit for bit. The K/V and slot-0 files are unchanged.

## Composition (analytical, `tools/qwen_dspark_step_collect.py` -> `step_composed.json`)

The one-stream communication is fixed, so the step is composed from the measured components:

- verify = 36 x S1(L0) + H1 = 462,713
- AR token = 36 x AR(L0) + H0 = 159,167
- draft = 5 x D0 + drafter head over 3 slots (from the measured p1 and p4 heads) + context ingest 3,024 and Markov 4,851 = 117,430. The ingest and Markov terms are priced, not RTL (`drafter_rom_schedule.json`).
- commit: the accept unit fires within the host's 64-edge accept window, plus 1 cycle.

The step is 580,208 cycles.

At tau = 3.0375, the equal-weight average over the owner's 6 classes (`tau_w8_S3_B4` from `drafter/tau_summary.json`):
- DSpark: **6,282 accepted tok/s per user**
- AR: **7,539 tok/s**
- Speedup: **0.833x**

Bounds:
- **Free drafter:** even a drafter that costs nothing gives only 1.045x. The verify layer pays +2,727 cycles per extra position at P = 255 on the in-tile attention path.
- **Break-even:** a verify layer of 9,833 cycles or less.
- **1% gain:** a verify layer of 9,700 cycles or less.
- **Drafter serialisation:** the drafter layer spends 9,406 of its 20,112 cycles with SU ops waiting on a busy SU, because the drafter program puts a barrier before every op.

## Verdict

**The function is closed and exact on the REAL_MEM path.** That covers:
- multi-position KV write and read with per-position visibility;
- accept with a rejection and with full acceptance;
- commit and rollback, and the next block over the RTL-left HBM;
- the head and the drafter as separate components.

**As a rate lever on this datapath, DSpark is rejected (owner rule <1%): 0.833x.** It needs the adopted 2x near-HBM attention lanes in the runtime, a verify layer of 9,700 cycles or less, and a de-serialised drafter program before it can gain.

## Open

RESOLVED (see the target-context section): the core fault flag (cycle 4,657, segment 0, all 4 dies) is the ME lane multiplier's fail-closed deep-underflow check, triggered by the seeded synthetic KV history. With a real-magnitude window the drafter layer runs fault-free.

## Claim boundary

- All measurements are at P = 255 with in-tile KV slices, not near-HBM attention.
- The 36-layer and 5-layer totals are composed from layer 0.
- Drafter ingest and Markov are priced.
- tau comes from 3 prompts per class.
- There is no SS/FF closure of the VPOS/ARP/accept/mp-service logic, and there is no whole-step RTL run.
