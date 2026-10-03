# Qwen3-8B ROM near-HBM attention: sustained HBM3E read rate per stack

**Question.** Can each HBM3E stack sustain 0.9 TB/s (750 B per 1.2 GHz edge) of KV reads to one in-order local consumer, and what controller does that need?

**Answer (final RTL, r6).**

**Yes, with a streaming controller and stream-aware per-bank refresh (REFpb).**
- The run covers 288 layers: 36 layers at each of 8 refresh phases, at the r2 layer period of 5,234 ns.
- Every layer completes its 1 MiB K+V stream in at most **1,094.7 ns**, against 1,165.1 ns needed. That is **0.958 TB/s on the worst layer**, 95.8% of the 1.0 TB/s peak.
  - This includes 24.6 ns from `go` to the first data.
  - The mean layer is at least 0.967 TB/s, and the data phase alone runs at 0.982 TB/s.
- Refresh is strictly on schedule. The bench saw 0 timing violations and 0 byte mismatches.

**No with strict all-bank refresh (REFab), and no with today's r14/credit17 controller.**

The controller closes at SS for its own clock, HBM CK/2 = 976.6 MHz. It misses the 1.2 GHz SS screen by 4.7 ps (§2).

## 1. Model (`model-r1.json`, `tools/qwen_hbm_sustained_bw_model.py`)

**Timing.**
- Picosecond values come from the parameters of `ot_hdc_hbm_model.sv`: the Ramulator 2 HBM3 preset, plus JESD238 tREFI = 3.9 µs and tRFC = 350 ns.
- tRFCpb = 200 ns comes from `ot_hdc_v41x_idx_hbm.sv` (JESD238 Table 93).
- Organisation: 32 PCs × 32 banks (2 SID × 4 BG × 4), with 1 KB rows. Each PC moves BL8 = 32 B per 1.024 ns, giving a 1.0 TB/s peak (`ot_hbm3e_phy.json`, `technology.json`).
- **Assumed:** tRREFD = 8 ns, and one row-command slot per channel per controller cycle.

**Pattern.**
- Each layer per stack reads K(A), K(B), V(A), V(B). With 2,048 positions × 128 B × 2 heads × 2, that is 1,048,576 B.
- KV address map, low bits to high: BG[1:0] | PC[4:0] | column[4:0] | bank-set[2:0] | row = layer.

Consequences of this map:
- One layer equals one row index in every bank of every PC.
- 32 row hits per ACT.
- The BG rotates every sector, so the 4-cycle BG period is at least tCCD_L.
- The next bank set is opened one set ahead, so tRCD and tRP are hidden.
- tFAW and tRRD use about 11% of their allowance.
- Row slot use is about 14% per channel.
- The column bus is 100% used. HBM3 is designed for that.

**Closed-form bounds.**

| Quantity | Value |
|---|---|
| Peak layer time | 1,048.6 ns |
| Start-up latency | 45 ns |
| REFab per event | 385.6 ns |
| REFab long-run rate | 90.1% of peak (0.901 TB/s) |
| REFab, a layer that takes a hit | 0.709 TB/s |
| REFpb, stream-aware | no data-bus loss |

The stream-aware REFpb has no loss when the refreshed bank lies outside the current set and the next two sets.

**Cycle model, the same policy as the RTL.**
- REFpb fires every 118 cycles (120.8 ns, which is ≤ tREFI/32). Each bank is refreshed once per 32-command round.
- The bank to refresh is chosen 48 cycles ahead: closed, not protected, nearest upcoming set first. While idle, the middle sets go first.
- The descriptor is posted HINT cycles before `go`.

| Case | Model worst | RTL r6 worst | RTL layers over 1,165 ns |
|---|---|---|---|
| REFpb, hint 320 cycles (328 ns) | 1,104.9 ns | **1,094.7 ns (0.958 TB/s)** | 0 / 288 |
| REFpb, hint 200 | 1,136.6 | 1,152.0 (0.910) | 0 / 108 |
| REFpb, hint 100 | 1,238.0 | 1,254.4 (0.836) | 15 / 108 |
| REFpb, no hint | 1,341.4 | 1,354.8 (0.774) | 30 / 108 |
| REFab, staggered by tREFI/32 | 1,484.8 | **11,774 (0.089)** | 140 / 144 |
| REFpb, back-to-back layers | 1,384.4 | 1,593.3 (mean 0.842) | 21 / 72 |

**The descriptor must arrive about 261 cycles before `go`.** That is LEAD 48 + tRFCpb 196 + tRCD 19, about 267 ns. Decode follows a static schedule, so this notice can be given, but it is a new handshake with the consumer.

**Back-to-back layers do not hold 0.9 TB/s.** This case has no idle time and is not the deployed pattern.

**The model misses the REFab collapse.** It has no coupling across PCs. In the RTL, the in-order consumer has 32 landing credits per PC and stalls on whichever PC is refreshing. Staggered REFab takes 386 ns every 122 ns across the PCs, so the stream crawls at 0.089 TB/s.

**Existing models on the same stream** (`tb_hbm_stream_existing_models.sv`, NPC = 32, 8 layers). None of them holds 0.9 TB/s on every layer.

| Model | Mean | Worst |
|---|---|---|
| `ot_hdc_hbm_model`, one in-order port | 0.107 TB/s | 0.093 TB/s |
| `ot_hdc_hbm_model`, PC_RDY = 1 | 0.19 TB/s | 0.168 TB/s |
| `ot_hdc_v41x_idx_hbm` REFPB = 0, per-PC ports | 0.72 TB/s | 0.69 TB/s |
| `ot_hdc_v41x_idx_hbm` REFPB = 3, per-PC ports | 0.90 TB/s | 0.84 TB/s |

## 2. Controller change and area

| | r14 / credit17 today | Built (`ot_hbm_r14_stream_pc.sv`, `ot_hbm_r14_stream_stack.sv`) |
|---|---|---|
| Issue | per-PC FR-FCFS FSM: accept II = 5 edges at LEN1 gives 204.8 GB/s per stack; 4 column paths give 128 GB/s; tCCD_S rounded up to 2 edges at 1 GHz gives 512 GB/s | descriptor sequencer: 1 RD per cycle per PC, no per-sector request |
| Clock | 1 GHz | HBM CK/2 = 976.6 MHz (DFI 1:2), so tCCD_S is exactly 1 cycle; CDC to the 1.2 GHz consumer at the landing FIFO |
| Command buses | 1 or 4 shared per stack | own column slot per PC; per channel, a row slot that the 2 PCs take on alternate cycles (TDM), with the decision registered one cycle ahead |
| Refresh | REFab | REFpb, stream-aware, strict (`REF_MODE=1`); `REF_MODE=0` gives REFab |
| Return | per-PC return RAM | 256 b per PC per cycle into a landing FIFO of CRED = 32 sectors |

On the landing FIFO size:
- CRED = 24 gives 0.843 TB/s, which is too small.
- CRED = 64 gives no gain over 32.
- The highest occupancy seen was 18 sectors.

Both modules default to `ENABLE=0`, which ties every output to 0. Nothing instantiates them, and no r14 or pinned file changed.

**SS screens.**
- The screened slice is one channel with `NCH=1`: 2 PCs plus the row slot. Setup is checked at WC with 60 ps uncertainty; hold is checked at WC and BC.
- **r6 at 1.024 ns (976.6 MHz, its operating clock): PASS** (`physical-ss-ck2-r6-PASS.json`).
  - Setup WNS +19.0 ps, hold met, DRC 0, no slew, cap or fanout violations.
  - Fmax 995 MHz.
  - Routed cell area 2,491 µm².
- **r6 at 0.833 ns (1.2 GHz): NOT MET** (`physical-ss-r6-NOT_MET.json`).
  - Setup WNS −4.7 ps over 8 endpoints, Fmax 1.194 GHz.
  - Hold met, DRC 0.
  - Routed cell area 2,612 µm².
  - Worst path: bank-group tRRD_L flag → ACT eligibility → registered row one-hot.
- Earlier revisions are kept as failure history. They are r1/r2 at −5.7 ns/−0.30 ns (serial argmin, then the arbiter loop), r3/r4 stopped at about −0.1 ns, r5 at −6.4 ps, and r7 at −52.9 ps. r7 added registered zero flags, which made timing worse, so the design reverted to r6.

**Area.**
- Per stack (16 slices): 0.040 mm² routed at CK/2, or 0.033 mm² from TT synthesis (2,036 µm² per slice).
- Per die (4 stacks): 0.159 mm².
- Landing FIFOs add 32 × 256 b of flip-flops per PC: 0.111 mm² per stack, or 0.44 mm² per die, at the model-r3 FF constant. The read multiplexers are not priced. Alternatively, the FIFOs can reuse the existing per-PC 64×512 return RAM.

## 3. Bench (`rtl-bench-r6.json`, `logs-r6/`)

**What `tb_hbm_stream_bw.sv` checks.**
- A picosecond checker checks every ACT, PRE, PREab, REFab, REFpb and RD against tRCD, tRP, tRAS, tRC, tRTP, tCCD_S/L, tRRD_S/L, tFAW, tRFC, tRFCpb, tRREFD and the row-slot rule.
- Refresh is checked to be never overdue, and each bank is refreshed once per round.
- Data comes from a backing array that is filled through the bench's own copy of the address map.
- The in-order consumer compares every sector against the source function.

**Negative controls.** All three fail as they should: tRCD +1 ns, one flipped bit, and tREFIpb −2 ns.

**Where it ran.** The r6 campaign ran on ot-epyc1tb with sources byte-identical to this commit. `logs/`, `logs-r2/` and `rtl-bench-r1/r2.json` hold the earlier r1/r2 RTL runs, which are superseded.

## Limits

**Not modelled:**
- the real PHY and analog behaviour: DFI training and retraining, periodic ZQ and VREF calibration, read DBI and ECC;
- thermal behaviour: a hot stack doubles the refresh rate (tREFI/2), which halves the REFpb slack;
- throttling;
- KV write turnaround, and other host traffic.

**Assumed:**
- the REFpb order rule, taken from the repo's encoding;
- tRREFD;
- the row slot;
- a 7.8125 Gb/s pin rate (1.0 TB/s), not the 1.2 TB/s parts.

**Bench simplifications:**
- the consumer shares the controller clock, so the CDC FIFO is not simulated;
- the 1.2 GHz SS screen misses by 4.7 ps;
- adopting this needs the consumer to give the advance hint of at least 261 cycles.
