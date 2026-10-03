# Two-clock crossing (3:4, 1.2 / 0.9 GHz): replay

Branch `claude/two-clock-rtl-20261003`. Each record below names the commit it was run from. Every run used a
clean, pinned worktree of that commit.

## What was built

- `rtl/common/ot_ratio_cdc_fifo.sv`: the successor of `rtl/chip/ot_chip_v41_ratio_fifo.sv`. The predecessor is
  untouched, and its failed evidence stays as it is.
  - The clocks are related: one PLL, a 3.6 GHz VCO divided by 3 and by 4
    (`results/physical_abi3/asap7/chip/v41_w18/clock_plan.json`). Because gcd(3,4) = 1, every divider phase gives
    the same set of edge spacings, {0..4} VCO ticks. The setup window is therefore 1 tick (277.8 ps), and hold is
    checked at the coincident edge.
  - The FIFO uses no synchronisers, no Gray code and no timing exceptions. Every arc that crosses the domain
    boundary is a flop-to-flop wire, so STA times it at 278 ps:
    - pointers;
    - DOWN/WAIT/RUN state;
    - each memory entry into a read-domain shadow register, captured every cycle.

    The read multiplexer then sees only read-domain flops. The predecessor's failure was the arc from `mem` through
    the multiplexer to `r_d`, at -75.59 ps on 64 pins.
  - Reset is a whole-FIFO DOWN -> WAIT -> RUN handshake with synchronous per-domain resets. Writes are never
    accepted during either side's reset, and a word from an earlier epoch is never replayed. Words still in flight
    at a reset are flushed on both sides.
  - Crossings between dies, which use different PLLs, are out of scope. They need an asynchronous FIFO.
- `rtl/hdc/ot_hdc_me_2clk.sv` together with `tools/qwen_two_clock_core_emit.py`: a default-off integration
  (`ME_CDC = 0`) into the Qwen3-8B ROM decode core.
  - The matrix engine (the ROM field side) moves to 1.2 GHz. The sequencer, the vector stream unit, the reducers
    and the VM stay at 0.9 GHz.
  - The command crossing (slow to fast) and the result crossing (fast to slow) both use `ot_ratio_cdc_fifo`.
  - A full result FIFO pauses the engine clock exactly, through the `ot_hdc_cg` ME_STALL mechanism.
  - The pinned `rtl/hdc/ot_hdc_core_vector_weight.sv` is not edited. The variant is emitted from it with exact
    anchors.

## Replay

```
# model: latency per phase, throughput per DEPTH, token price (imports tools/uarch_model.py, does not edit it)
python3 tools/two_clock_crossing_model.py --output crossing_model.json

# dual-clock Verilator crossing campaign: 60 runs, 2,000,000 words each, plus 6 mutants that must FAIL
python3 rtl/test/two_clock/run_campaign.py --workdir SCRATCH --output bench_campaign.json --words 2000000 --seeds 4

# ORFS, SS setup / FF hold with 60/25 ps; one nickname per run; persistent launcher
python3 tools/run_abi3_physical_persistent.py --persistent-workdir W --launch-receipt R.json \
  --view asap7 --top ot_ratio_cdc_fifo --source rtl/common/ot_ratio_cdc_fifo.sv --param W=64 --param DEPTH=4 \
  --param HOLD=2 --clock-port wclk --clock-period-ns 0.833 --clock-uncertainty-ns 0.06 \
  --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 \
  --stages synth,pnr --core-utilization 30 --place-density 0.5 --hold-margin-ns 0.01 --orfs-var ADDER_MAP_FILE= \
  --orfs-var SDC_FILE=/src/physical/two_clock/ratio_cdc_fifo_f2s.sdc --nickname-tag twoclk_cdc_f2s_w64_d4 \
  --purpose signoff_target --force --output physical.json
python3 tools/w18/corner_sta.py --orfs-dir W/orfs --output corner_sta.json
#   (s2f: SDC ratio_cdc_fifo_s2f.sdc, --clock-port rclk; W512: --param W=512)
#   launch receipts are kept in physical/*/launch_receipt.json

# split-clock exact gate of the Qwen ROM core (G4 / SU16, BF16 ROM, KV SRAM)
python3 rtl/test/two_clock/run_core_2clk.py --workdir SCRATCH --output qwen_core_gate.json --jobs 24
```

## Records

| File | Run from | Content |
|---|---|---|
| `crossing_model.json` | 56a9e899 | Latency and throughput model; token price |
| `bench_campaign.json` | 87fae5ac | 60 dual-clock runs, 120 M words, mutants |
| `physical/{f2s_w64_d4,s2f_w64_d4,f2s_w512_d4}/` | 9f22b185 | Routed ORFS record and SS/FF corner STA |
| `qwen_core_gate.json` | 901f3e2a | Split-clock exact gate of the Qwen ROM core, ot-agidock128, Verilator 5.050: **PASS** |
| `qwen_core_gate_FAIL_56a9e899.json` | 56a9e899 | Earlier gate, kept as failed evidence: 4,096 logit mismatches under split clocks (see below) |

The crossing campaign ran under the local Verilator 4.038. The core gate ran under Verilator 5.050 on
ot-agidock128, because the local host was 3x oversubscribed.

## Results

**Crossing: closes at sign-off.** The worst setup path is the cross-domain 278 ps window in each run (`sta_ss.log`).

| Instance | SS setup WNS | FF hold WNS | Area | Cells |
|---|---|---|---|---|
| f2s W64 D4 | +41.46 ps | +9.76 ps | 320.9 um2 | 2,591 |
| s2f W64 D4 | +33.62 ps | +7.78 ps | 320.5 um2 | 2,597 |
| f2s W512 D4 | +32.36 ps | +5.31 ps | 2,498.8 um2 | 19,472 |

For comparison, the predecessor (W64) measured -75.59 ps setup with 64 violating pins.

**Latency.** Each figure is from writer accept to consumer accept, with no backpressure. Model and bench agree.

| Direction | Ticks | Destination cycles (min / mean / max) | Model charges (`CDC_W18`) |
|---|---|---|---|
| Fast -> slow | {5,6,7,8} | 1.25 / 1.625 / 2.00 slow | 4 slow cycles |
| Slow -> fast | {4,5,6} | 1.33 / 1.667 / 2.00 fast | 5 fast cycles |

The predecessor's sparse latency was 3.00 / 3.38 / 3.75 slow cycles fast->slow and 3.67 / 4.00 / 4.34 fast cycles
slow->fast.

**Throughput** is 0.900 words/ns (the slow-clock ceiling) in both directions at DEPTH 4 and DEPTH 8, and 0.600
words/ns at DEPTH 2.

**Dual-clock bench: PASS.**
- 60 runs and 120 M words: sparse, saturate, random stalls, backpressure bursts, and resets in flight. The reset
  runs covered 1-5-cycle resets on either side, 174785 resets in total.
- No word was lost, duplicated or reordered, and no word from an earlier epoch was replayed.
- No write was accepted while `wrst_n` was low, and `r_v` never rose while `rrst_n` was low.
- All 6 protocol mutants are detected:
  - reader peer gate removed;
  - write-reset gate removed;
  - HOLD rule removed;
  - seen-not-RUN rule removed;
  - wrong slot read;
  - WAIT state ignores the peer.

**Token price** (`crossing_model.json`):
- The worst-case 2/2 latency replaces the 4/5 charge. V4.1 ROM case (b) goes from 3,369.6 to 3,391.6 tok/s
  (+0.65%), and the W10 product (LAT 7) from 2,786.8 to 2,801.8 (+0.54%).
- Zero CDC would bound these at 3,410.3 and 2,814.6.
- The Qwen3-8B ROM model has no split-clock term, so its price is the RTL measurement below.

**Qwen ROM integration** (reduced G4 / SU16 core, BF16 ROM, KV SRAM): split clocks are bit-exact against the ISA
golden.
- Checked: every logit, the whole VM and the whole KV, in two runs:
  - the single decode step;
  - all 18 steps of the 16-prompt + 3-generated run, plus the generated ids against the torch oracle.
- This holds in all 3 fclk divider phases, with 0 dual-clock read-after-write collisions.
- `ME_CDC=0` is cycle-identical to the pinned core: 24,024 and 432,752 cycles.

| Configuration | Single step | 18-step run |
|---|---|---|
| All 0.9 GHz (pinned core) | 26,695.6 ns | 480,875.6 ns |
| Split: engine 1.2 GHz, rest 0.9 GHz (`ME_CDC=1`) | 21,460.0 ns (-19.6%) | 386,626.7 ns (-19.6%) |
| All 1.2 GHz (pinned core; reference only, the serial chain does not close at 1.2 GHz) | 20,021.7 ns | 360,656.7 ns |
| Diagnostic, single-clock row chase kept (`ME_CDC_SAFE_CHASE=0`; exact here but not proven rate-safe) | 20,971.1 ns | 377,754.4 ns |

- **Same-clock cost of the crossings:** with `ME_CDC=1` and both clocks equal, a single step takes 614 more slow
  cycles than the pinned core (24,638 against 24,024). Of these:
  - 118 cycles are crossing latency (24,142 cycles with `ME_CDC_SAFE_CHASE=0`);
  - 496 cycles are the rate-safe chase.

**Failure history**, kept as evidence:
- A local development build sized the command word one AW short. It faulted and was never recorded.
- Gate 56a9e899 (`qwen_core_gate_FAIL_56a9e899.json`) is exact with equal clocks but has 4,096 logit mismatches
  under split clocks. Cause: the result-FIFO stall paused the engine clock but not the fast-domain read-response
  registers, so a held edge delivered the next word. That breaks the ME_STALL supply contract.
- Fix in 744ab23f: every engine read enable is ANDed with the clock enable.

## Next steps

**Qwen ROM**
1. Apply the same `u_me` -> `ot_hdc_me_2clk` substitution to the W12 emitter's core (`ot_qwen_me_spine_w12`). The
   host-composed tile fabric moves to fclk.
2. At full shape a result entry is (G>>SMIN) x 553 bits, about 53 kbit. Narrow it to the port groups that write, or
   use the 4/3-widened slow port. Price the FIFO area at that width (W512 is 2,499 um2 for 4 entries).
3. Add the split-domain term to the Qwen ROM model.
4. Replace the conservative engine chase with a row-granular, rate-safe chase. The diagnostic shows up to 2.3%.

**DeepSeek V4.1 ROM**

Archimedes owns the parent integration. The steps are:
1. Swap `ot_chip_v41_ratio_fifo` for `ot_ratio_cdc_fifo` at the 7 historical port classes.
2. Set `CDC_W18` to 2/2.
3. Close the parent with related-clock SS/FF timing.
