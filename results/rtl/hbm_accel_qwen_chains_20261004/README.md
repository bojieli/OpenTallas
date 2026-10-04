# Qwen3-8B HBM accelerator at 8K: serial chains, SRAM spread and the DSpark verify (2026-10-04)

**Result (P8191, every term a measured exact RTL stage unless marked).**

| | (a) TP2, 8 stacks | (b) TP4, 16 stacks |
|---|---:|---:|
| AR baseline (main `qwen_hbmacc_p8191_20261004`) | 1,161,915 cyc, 1,032.8 tok/s | 557,056 cyc, 2,154.2 tok/s |
| AR + SRAM spread | 1,159,917 cyc, 1,034.6 tok/s (+0.17 %) | 540,594 cyc, **2,219.8 tok/s (+3.05 %)** |
| DSpark verify layer, p = 4 (vs AR HBM layer) | 33,580 (33,051) | 16,044 (17,237) |
| DSpark step / rate at tau 3.0375 | 1,488,871 cyc, 2,448 tok/s (**drafter unvalidated**) | 721,020 cyc, **5,055 tok/s = 2.28x AR** |

Verdicts:
- **Chains in HBM layers are already at their floor.** The (a) layer is 33,051 cycles against 33,046 at the measured controller rate (0.962 TB/s a stack; 31,792 at peak). The (b) layer is 17,237 against 17,014. The chains finish inside the stream: the window is never blocked. The chain breakdown is in `breakdown/`.
- **Exposed chains: the SRAM-resident layers and the head.** TP2 L0 is 6,392 cycles against a 2,536-cycle KV floor. TP4 L0 is 5,885 against 1,268. In (a) the stream stays busy prefetching L1 while L0 runs, so only (b) exposes these chains.
- **SRAM spread (overlap with the weight stream): ADOPT for (b) (+3.05 %), REJECT for (a) (+0.17 % < 1 %).**
  - Spread means the same SRAM budget goes to every layer's leading code words (75 for TP4, 31 for TP2) instead of to whole leading layers.
  - Every layer is then stream-bound, and the chains run under the stream.
  - It is a planner change only (`--sram-spread`, default off), with no new hardware. The X is exact on every die.
- **DSpark verify with multi-position weight reuse: ADOPT (mandatory DSpark function).**
  - Each HBM code word is read 4 times from the prefetch window while it is resident.
  - The window slot is released on the last pass, by `rtl/hbm_accel/qwen/ot_hbmacc_win_usecount.sv`.
  - The verify layer then costs about the same as an AR layer: 1.016x (a), 0.93x (b, with spread).
  - All of these verified exact, all positions on all dies, with reads equal to 4 x the HBM words and no release fault:
    - TP2 and TP4 verify layers, on the zero-latency model and on the synthesizable release;
    - TP2 head p = 4 (argmax records = oracle);
    - TP4 DSpark drafter layer D0 (S = 3, start 8188, real-magnitude window, weights and KV streamed).
- **Window size for verify.** The window must hold the largest matvec plus the lag: TP2 gate/up is 512 words, TP4 is 256.
  - TP2 at 576 words blocks the stream during the 4-pass gate/up (room_block 36,496). 1,024 words removes the block and is adopted: 35,283 → 35,096 cycles at the AR preroll.
  - TP4: 320 words (16,242) beats 512 (16,389).
  - Verify layers are composed with the measured verify tail as preroll (HA8 method): 2,321 / 2,186 cycles.

**Release block physical screen.** `ot_hbmacc_win_usecount` (pre-layout, SS, 0.833 ns, 60 ps; `screen/`):

| Version | r2r |
|---|---|
| Per-slot counters | 650 MHz (rejected) |
| 32-bit pass counter | 803 MHz (rejected) |
| Adopted: 16-bit pass counter, 3 stages | **1,204 MHz, WNS +2.7 ps**, 85 µm², 530 cells |

- In-system it adds 4 cycles of release lag and 0 measured cycles: d4 is 22,893 on both release models.
- The routed SS/FF closure is handed to the 1.2 GHz closure program, together with VPOS/ARP/accept, which is unvalidated in the ROM DSpark record.

**Remaining chains above their floor.**
- **TP4 drafter layer:** 22,893 cycles against a 17,014-cycle stream floor. The stream unit is at 14,896, because the drafter program puts every op behind a barrier. That program is shared with the ROM DSpark owner.
- **TP2 verify layer:** 2.5 % above its floor, from the 4-position softmax on the SU (11,615).

**Unvalidated (listed, not claimed):**
- Drafter context ingest plus Markov: 7,875, priced on the ROM.
- The TP2 drafter layer: no TP2 drafter images exist. The proxy is the TP2 verify layer x d4/v4, so the (a) DSpark rate is not a measured claim.
- tau: from the ROM record.
- Embedding fetch, KV write-back, and window data (arrival timed, data from images).

**Files.**
- `runs/*`: per-run cmd, plan, token.log and token_result.json. `tp4_ar_exactness.json` covers the TP4 AR runs whose driver failed only on a missing oracle.json.
- `breakdown/*`: the per-chain critical-path cycles (`tools/qwen_hbmacc_chain_breakdown.py`).
- `terms.json` (from `make_terms.py`) and `composition.json` (`tools/qwen_hbmacc_chain_compose.py`).

**Vehicle.**
- `rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12_vp.sv` and `qwen_hbmacc_rt_w12_vp.cpp`: the HA8 die plus the ROM verify changes plus use-count release.
- `tools/qwen_hbmacc_rt_verify_w12.py`.
- TP2 verify images come from `tools/qwen_rom_verify_program_w12.py` with `QWEN_O4_TP=2` (head at p = 1 equals the pinned head).
- Goldens: local GPU (`tools/qwen_hbmacc_position_oracle_gpu.py` TP2 block 8187..8191 and P0..3 heads; ROM ctx8k golden A for TP4; `tools/qwen_rom_dspark_drafter_layer_golden.py --kv-window` for D0).
- Runs on ot-epyc1tb at `/srv/opentallas-scratch/claude/qhbm-chains`.
