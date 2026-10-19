# HBM-MTP D1 / MTP-AREA: what P accumulator lanes cost in the SM matrix tile (2026-10-18)

This is a sizing study only. It used Yosys 0.68 with flattening and ABC mapping, the ASAP7 RVT TT library and a 0.833 ns target, with the same tool calls as `tools/run_abi3_physical.run_synthesis`. Everything ran on the fleet. There was no placement and no routing, and nothing here is bound into a die.

**Current tile (d4g GEN2).** The die has 16 instances of `ot_hbm_accel_smh_attn`. Each SM is 8 columns × 2 tiles × 2 leaves, so the die has **512 leaves**. Each leaf contains:
- an x store: 4 × 128x256 SRAM;
- the block-dot column `ot_hbm_accel_smh_bdc`: 2 × 32-term FP8/FP4 `bterm3`, then a LAT-7 FP32 ring with IL=8 rows, then a 2-input tree. That is 64 FP8 MACs;
- the BF16 column: tcl halves plus tct, which is 16 BF16 MACs.

**Mechanism.** The new code is `rtl/hbm_accel/sm/mtp_lanes/ot_hbm_sm_bdc_p.sv` (also `ot_hbm_sm_tcc_p`). It broadcasts one weight word to P lanes. Each lane is an unmodified copy of the production column, fed with its own activation pin flops. Weight pin flops, the E2M1 decode and the control pipes are identical across lanes, so the flattening synthesis shares them. Because the lanes are copies, each lane keeps the golden reduction order exactly. P=1 is the current tile.

**Bench.** The bench is `tb_hbm_sm_bdc_p.sv`, run on Verilator 5.050. It feeds random FP8/FP4/BF16 vectors (12 chunks × K16 × 8 rows) and checks that lane p equals an independent production single-lane column, cycle for cycle and bit for bit. It PASSES at P = 1, 2, 4, 6 and 8. The mutant (MUT=1, the last lane aliases lane 0's activation) is caught at P = 2 and P = 4.

| P | bdc cell µm² | bdc flops | tcc cell µm² | tcc flops | +die mm² bdc | +die mm² tcc | +die mm² x store | total +mm² | % of 641.8 mm² |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 7,181 | 10,667 | 16,428 | 26,980 | 0 | 0 | 0 | 0 | 0 |
| 2 | 13,583 | 19,336 | 32,133 | 52,076 | 7.3 | 18.0 | 8.0 | 33.3 | 5.2 |
| 4 | 26,405 | 36,672 | 63,521 | 102,266 | 22.0 | 53.9 | 23.9 | 99.8 | 15.6 |
| 6 | 39,201 | 54,008 | (est.) | (running) | 36.7 | 89.9 (est.) | 39.9 | 166.4 | 25.9 |
| 8 | 52,005 | 71,344 | (est.) | (running) | 51.3 | 125.8 (est.) | 55.8 | 232.9 | 36.3 |

- **Cost per added lane.** In the block-dot column each added lane costs **6,404 µm² and 8,668 flops**, which is 0.89 of a full column. About 2,000 flops of weight and control logic are shared. The BF16 column costs **15,700 µm² and 25,095 flops** per lane, which is 0.96 of a column. Both costs are exactly linear in P.
- **Die translation.** I converted cell area to die area as added mm² = Δ cell area / util × 512 leaves. The util is **0.447**, which is the production bdc's synthesised area (7,161 µm²) divided by its closed outline (`smh_bdc_ref_p50`, 112.32 × 142.56 µm). I applied the same util to tcc; that is an assumption. The x-store column assumes every lane gets its own copy of the 128-row x store, costing 15.6k µm² of SRAM per leaf, or 7.97 mm² per added lane across the die.
- **Cheapest option.** If only FP8/FP4 matvecs get P lanes (bdc only, with the BF16 column kept at one lane for attention), P=6 costs **36.7 mm² of logic plus 39.9 mm² of x store, about 77 mm² or 12% of the die**.
- **Timing (TT, synthesis netlist, unbuffered).**
  - In bdc the worst path is the same lane-independent high-fanout net at every P (WNS −2.85 at both P=1 and P=8). The closed P=1 tile meets timing after routing, so P-lanes add no new logic depth.
  - In tcc the worst path is the shared valid/first flop fanning out to every lane: 1.1 ns at P=1, 2.2 at P=2 and 4.3 at P=4 (unbuffered).
  - **1.2 GHz is plausible** if the broadcast (weight word plus control) goes through a registered per-lane-group fan-out tree. That adds about +1 cycle of latency at P ≥ 4, because P lanes widen the leaf about P×.
- **Port implications.**
  - Activation write and read bandwidth grows P×: the x write beat (2,048 b) and the per-leaf x read (788 b/cycle) are both multiplied by P. For a fixed-cycle load, the VM→SM activation feed is P× too. Activations are small relative to the weight stream, but the 2,048-b x-write beat per SM must either be P× wider or take P× more beats.
  - Results grow P×: there are P × 32 b per row per chunk on the leaf gather (one word per column today).
  - The HBM weight bandwidth, the weight path and the PHY are unchanged.

Records:
- `summary.json`
- `synth/<unit>_{base,p1..p8}/{area.json,stat.txt,setup_path.rpt}`
- `bench/run_p*_m*.log`

tcc P=6 and P=8 syntheses were still running on ot-epyc4 under `/srv/opentallas-scratch/claude/mtp_area_1018/synth/` (see `pending_results.txt`).
