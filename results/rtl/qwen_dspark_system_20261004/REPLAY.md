# Qwen3-8B ROM DSpark in the system RTL: minimum components and the composed step

These records cover the Qwen3-8B ROM DSpark function in the system RTL. Everything is default-off and lives in successor files only. The pinned REAL_MEM sources, including `ot_qwen_rt_kv_fill_service`, are byte-identical.

The vehicle is the VPRM die, `rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_vprm.sv`, configured as follows:
- VPOS core, `ENABLE_ARP`, and the accept unit.
- KV goes through `rtl/hdc/kv/ot_qwen_rt_kv_mp_service.sv` and `ot_qwen_hbm_model_ack` (NPC 32, `WR_ACK`) on the REAL_MEM path.
- TP4, G 6,144, SW64.

It is run by `tools/qwen_rom_rt_vprm_w12.py` on ot-epyc1tb at `/srv/opentallas-scratch/claude/qwen-dspark-system`. The sources are `src-aec77a75f`, which contains the host model-eval-before-preload fix (the VPRM twin of 15778679a). The job list is in `components/comp.sh`.

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

The drafter run raises a core fault flag. Outputs are exact. The flag rises at cycle 4,657 in segment 0 on all 4 dies; the collective is clean. The source is being located with the `dbg_fault_src` observation port (`FAULTTRACE` lines from the host).

## Claim boundary

- All measurements are at P = 255 with in-tile KV slices, not near-HBM attention.
- The 36-layer and 5-layer totals are composed from layer 0.
- Drafter ingest and Markov are priced.
- tau comes from 3 prompts per class.
- There is no SS/FF closure of the VPOS/ARP/accept/mp-service logic, and there is no whole-step RTL run.
