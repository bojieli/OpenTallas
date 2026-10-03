# Qwen3-8B ROM near-HBM attention: sustained HBM3E read rate per stack

Question: can each HBM3E stack sustain 0.9 TB/s (750 B per 1.2 GHz edge) of KV reads to one in-order local consumer? If so, what controller does it need?

Short answer:
- **Yes, with a streaming controller and stream-aware per-bank refresh (REFpb).** In RTL, every one of 288 layers (36 layers at each of 8 refresh phases) completes its 1 MiB K+V stream in at most 1,082.4 ns, against 1,165.1 ns needed. That is **0.969 TB/s worst layer** (96.9% of the 1.0 TB/s peak), including 24.6 ns to the first data. The data phase alone runs at 0.991 TB/s.
- **No with all-bank refresh (REFab).** Under strict REFab, 0.9 TB/s is not reached.
- **No with today's r14/credit17 controller.** It cannot issue at this rate.

All refresh is strictly on schedule, and the bench measured zero timing violations and zero byte mismatches.

## 1. Model (`model-r1.json`, `tools/qwen_hbm_sustained_bw_model.py`)

**Timing sources.**
- Picosecond values are the `ot_hdc_hbm_model.sv` parameters: Ramulator 2 HBM3 preset; JESD238 tREFI 3.9 µs and tRFC 350 ns.
- tRFCpb is 200 ns (`ot_hdc_v41x_idx_hbm.sv`, JESD238 Table 93).
- Organisation: 32 PCs × 32 banks (2 SID × 4 BG × 4), 1 KB rows, BL8 = 32 B per 1.024 ns per PC (`ot_hbm3e_phy.json`, `technology.json`), giving 1.0 TB/s peak.
- tRREFD = 8 ns is **assumed**; it is not sourced in the repo.

**Pattern.**
- Per layer per stack: K(A), K(B), V(A), V(B). That is 2,048 positions × 128 B × 2 heads × 2 = 1,048,576 B, against a need of 1,165.1 ns.
- **KV map (low to high bits):** BG[1:0] | PC[4:0] | column[4:0] | bank-set[2:0] | row = layer.
- Consequences of this map:
  - One layer of one stack is one row index in every bank of every PC.
  - Each bank is opened once per layer and gives 32 row hits per ACT.
  - The BG rotates every sector, so the 4-cycle BG period is at least tCCD_L (3).
  - The next bank set is opened one set ahead, which hides tRCD and tRP.
  - tFAW and tRRD need about 11% of their allowance.
  - The row-command slot is about 14% used per channel.
  - The column bus is 100% used, at 1 RD per 2 tCK per PC. HBM3 is built for this.

| bound | value |
|---|---|
| peak layer time | 1,048.6 ns |
| start-up (ACT, tRCD, CL, BL, PHY) | 45 ns |
| REFab, strict, per event | tRP + tRFC + tRCD = 385.6 ns |
| REFab, long-run fraction of peak | 90.1% (0.901 TB/s) |
| REFab, a layer that is hit | 1,479 ns (0.709 TB/s) |
| REFpb, stream-aware | 0 data-bus loss, provided the refreshed bank is outside the stream's current set and next two |

**Policy.** The cycle model of the sequencer (the same policy as the RTL):
- 8 phases × 36 layers at the r2 layer period of 5,234 ns.
- REFpb is issued every tREFI/32 on the due cycle, each bank once per 32-command round.
- The bank is chosen 48 cycles ahead: closed, not protected, nearest upcoming set first; when idle, the middle sets first.
- The descriptor is posted ahead of `go`.

| case | model worst | RTL worst | layers over 1,165 ns (RTL) |
|---|---|---|---|
| REFpb, hint 320 cycles (328 ns) | 1,104.9 ns | **1,082.4 ns (0.969 TB/s)** | 0 / 288 |
| REFpb, hint 200 | 1,135.6 | 1,140.7 (0.919) | 0 / 108 |
| REFpb, hint 100 | 1,238.0 | 1,244.2 (0.843) | 15 / 108 |
| REFpb, no hint | 1,341.4 | 1,344.5 (0.780) | 33 / 108 |
| REFab, staggered tREFI/32 | 1,484.8 | **11,769 (0.089)** | 140 / 144 |
| REFpb, back-to-back layers | 1,119.2 | 1,573.9 (mean 0.904) | 8 / 72 |

**The advance hint is required.** The consumer must post the layer's descriptor at least about 261 cycles (LEAD 48 + tRFCpb 196 + tRCD 19) before `go`. Decode is a static schedule, so this is available, but it is a new handshake.

**Where the model and the RTL disagree.**
- **REFab.** The model has no coupling across PCs, and it under-predicts badly. With finite landing credits (32 per PC), the in-order consumer stalls on whichever PC is refreshing. Staggered REFab (386 ns every 122 ns across PCs) leaves almost no gap, so the stream crawls.
- **Back-to-back.** The bench posts the next descriptor only after the previous stream is consumed. The model posts it early.

**Existing models, the same stream, NPC = 32** (`tb_hbm_stream_existing_models.sv`, 8 layers):

| model | mean | worst |
|---|---|---|
| `ot_hdc_hbm_model`, single in-order port | 0.107 TB/s | 0.093 TB/s |
| the same, PC_RDY = 1 | 0.19 TB/s | 0.168 TB/s |
| `ot_hdc_v41x_idx_hbm` REFPB = 0, per-PC ports | 0.72 TB/s | 0.69 TB/s |
| `ot_hdc_v41x_idx_hbm` REFPB = 3, per-PC ports | 0.90 TB/s | 0.84 TB/s |

None of these holds 0.9 TB/s every layer.

## 2. Controller change

| | r14 / credit17 today | needed (built) |
|---|---|---|
| issue | per-PC FR-FCFS FSM, accept II 5 edges, LEN1 → 204.8 GB/s/stack; 4 column paths/stack → 128 GB/s; tCCD_S ceiled to 2 edges at 1 GHz → 512 GB/s | descriptor-driven sequencer, 1 RD per cycle per PC, no per-sector request |
| clock | 1 GHz service edge | HBM CK/2 = 976.6 MHz (DFI 1:2): tCCD_S = 1 cycle exactly. CDC to the 1.2 GHz consumer happens at the landing FIFO. |
| command buses | 1 or 4 shared per stack | per PC: its own column slot. Per channel: 1 row slot shared by 2 PCs, refresh first. |
| refresh | REFab | REFpb, stream-aware, strictly on schedule (`REF_MODE=1`; `REF_MODE=0` keeps REFab for comparison) |
| return | per-PC return RAM | 256 b per PC per cycle into a CRED = 32 sector landing FIFO. CRED = 24 measured 0.843 TB/s, too small. CRED 64 gives no gain. |

The new files are `rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc.sv` and `ot_hbm_r14_stream_stack.sv`.
- Both default to `ENABLE=0`, which ties all outputs to 0.
- Nothing instantiates them.
- No r14 or pinned file was modified.

**Area.**
- One channel slice (2 PCs + arbiter, `NCH=1`) is 1,768 µm² of cell area after local TT synthesis (12,728 cells, 1,848 flops).
- ×16 that is **0.028 mm² per stack, 0.113 mm² per die**.
- The landing FIFO (32 × 256 b per PC) adds 0.111 mm² per stack (0.443 per die) of flip-flop area. That is 8,192 FF per PC at the 0.42282 µm² model-r3 constant, and the read multiplexers are not priced. It can instead reuse the existing per-PC 64×512 return RAM (13,319 µm² each).

**SS screen.** See `physical-ss-r1.json`.

## 3. Bench (`rtl-bench-r1.json`, `logs/`)

- The bench is `tb_hbm_stream_bw.sv`, run under Verilator 5.050.
- A picosecond checker checks every ACT, PRE, PREab, REFab, REFpb and RD against tRCD, tRP, tRAS, tRC, tRTP, tCCD_S/L, tRRD_S/L, tFAW, tRFC, tRFCpb and tRREFD. It also checks that refresh is never overdue and that each bank is refreshed once per round.
- Data comes from a backing array filled through the bench's own copy of the map. The in-order consumer compares every sector against the source function.
- The checker was shown not to be vacuous: the negative controls (tRCD +1 ns, one flipped bit, tREFIpb −1 ns) all FAIL.

## Limits (not modelled)

- **Real PHY and analog:** DFI training, retraining and periodic ZQ/VREF calibration, and read DBI or ECC.
- **Thermal behaviour:** a hot stack doubles the refresh rate (tREFI/2), which would halve the REFpb slack. Throttling is not modelled.
- **Shared-traffic effects:** write turnaround from the new-token KV write, and the host's other traffic.
- **REFpb bank-order rules:** these are taken from the repo's encoding (each bank once per round).
- **Assumed parameters:** tRREFD, and the row-command slot of one per channel per controller cycle.
- **Data rate:** the bench uses 7.8125 Gb/s (1.0 TB/s), not Micron's 1.2 TB/s parts.
- **Clocking in the bench:** the consumer and controller share one clock. The CDC FIFO is not simulated.
