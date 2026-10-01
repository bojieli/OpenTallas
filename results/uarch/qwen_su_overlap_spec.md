# Qwen ROM stream-unit overlap (dataflow level 1, cycles part) — design spec (W12b, 2026-10-01)

Status: SPEC ONLY. Priority after the one-segment all-reduce, tile closure at 1.2 GHz and the TP-4 token (root).
Opt-in parameter, off by default; bit-exact gate on Qwen TP-4 layer 0; adopted only if W16b prices it >= 1%.

## Why the lane register file alone saves ~0 cycles

In `rtl/hdc/ot_hdc_vstream.sv` / `ot_hdc_vstream_lane.sv` (generated from `ot_hdc_stream.sv`):

1. **One class per unit.** The SFU path is selected by the unit-level register `cls`. `ready = !active &&
   (i_sfu == cls || inflight == 0)`: every class change drains the whole lane pipeline (21 / 49 / 58 / 70 / 101
   cycles for NONE / RECIP / RSQRT / EXP / SIGM).
2. **Full-drain release.** The sequencer releases a dependent SU op only on `wait_su` or `barrier` (the unit's
   registered idle). There is no SU→SU chase; chase exists only for ME→SU and SU→ME.
3. A KR read sits where the VM read sits (address cycle → S1 → S2 capture), and a KR write sits where the VM
   write sits. With (1) and (2) unchanged, a KR consumer starts exactly when a VM consumer would.

The KR (W11 fields `kr_w/kr_wb/kr_r/kr_rb`, reserved `xkr*`) therefore saves VM ports and energy, at about 0
cycles.

## What saves cycles: per-vector overlap

The goal is a consumer that issues once its producer's *first* vector has retired, rather than after a full
drain.

- **A. Per-element class tag.** Carry `cls` in the element tag (`e_tag`, the tail) instead of the unit
  register. Each SFU instance is enabled by its element's own tag. The write stage takes the result from the
  element's own tap. Two classes may then be in flight together.
- **B. Write-port schedule.** Each lane has one VM/KR write port. The element of a deeper class retires
  `D_cons - D_prod` cycles later than one issued at the same cycle. The controller holds the consumer's issue
  so that no cycle has two retiring elements: a retire-slot scoreboard of depth `TAPMAX + 1` bits, shifted
  each cycle, with an issue rule of `slot[D_cls] == 0`.
- **C. Per-vector KR credit.** The consumer's vector v reads KR entry `kr_rb + v` at its S2 capture. It may
  issue at the earliest cycle at which the producer's vector v has been written, as counted by the producer's
  per-vector retire counter (already `n_retire` / `progress`).
- **D. Sequencer SU→SU chase.** A new chase kind: an SU op whose `chase` bit is set waits for the latest SU
  op's `progress >= chase_n` vectors instead of `wait_su`. The compiler (the W11 fuse pass, `form_chains`)
  sets it only on KR edges.
- **E. Reductions stay chain ends.** Their scalar results are cross-lane, as in W11's core. The rsqrt/recip
  of a reduced scalar keeps its drain; level 3 (reduction on the arriving stream) is a separate item.

## Expected value (estimate, to be priced by W16b)

hdc_timing replay of the TP-4 die program at SW 64:

- 254 dependent SU→SU pairs per token.
- Saving per pair is about (producer vectors − 1) + 3, about 5.6k cycles per token in total (≈ 6% of the
  90.6k-cycle replay at position 0). Most of it comes from the 64- and 96-vector RMS / residual / SiLU ops.
- Turnaround alone (KR, no overlap) is 0.7k at most, and about 0 in this RTL.

## Gate

- `tools/qwen_rom_rt_token.py` at TP-4, layer 0, with the overlap parameter on: every X word must equal the
  TP-4 oracle on all 4 dies.
- The cycle delta is measured with `RT_ITRACE` against the 4,669-cycle baseline.
