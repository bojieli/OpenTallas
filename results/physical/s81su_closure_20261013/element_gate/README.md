# S81 SU tiles: functional + throughput half of the element gate (2026-10-13, `[s81su-price]`)

`table.json` is the record; `build_table.py` regenerates it from committed files only, `source_match.py` writes `source_match.json` (sha256 of every RTL source of each routed kit at its routed commit against the gate commit).

**Result: no SU tile is qualified.** Physical closure is not judged here.

## Price (immutable, nothing derived or re-priced)

`results/arch/token_path_20261009/ds_rom.json` @ `00888ffb6`, `nodes[id=L<n>.<op>].cycles`. This is the source behind `budget.json` (@ `70bd064b2`) `/rom/ds_rom/classes[cls=su]`, 116,151.3 cycles a token. The budget's `QUALIFIED` on `dsfd_su_t_*` is the name rule `^(dsfd_su_t_|ot_s81_hc_)` with ratio null: it was never a measurement of the hierarchical slab.

| SU job | priced node(s) | price (cycles) | priced shape |
|---|---|---|---|
| QN | attn.q_quant | 288.0 | su_norm q, N 256, D 1,280, RMSNorm then FP8 quant |
| KV | attn.kv_rope_qdq | 283.0 | su_norm kv, N 512, D 512, RMSNorm, RoPE, FP8 QDQ (off the critical path) |
| QB | attn.z_quant | 80.0 | su_qbank NB 32, 2 beats (2,048 values) |
| SW | ffn.quant2 | 191.0 | su_swiglu W 1,024, 4 vectors, first input to last code |
| SE | attn.max + exp + den + sink | 795.3 (T 640), 691.2 (T 128) | softmax H 16, scores in to den at the lanes |
| SO | attn.normalize | 244.9 | softmax H 16, first P.V vector in to last o out |
| GQ, GK | none | none | gain loads have no token-path node, so no price exists |

SE is the sum of four listed nodes that the one job spans; each node is quoted in `table.json`. `ffn.swiglu` (3.0) and `ffn.route_w` (5.9) are separate nodes "covered by ffn.quant2" and are not added to the SW price.

The price nodes run from the vector-memory read to the result landing at its consumer and include the old hub transport (hub in 33, out 23, wire 9 + 9 on the norm rows).

## Measured (production shape)

Combined full gate of the hierarchical slab `dsfd_sp_su_h` @ `b132ae0da` (main `69c124e5d`), `tools/s81_suhc/su_gate.py run --hier --shape full`: QN_N 256, KV_N 512, QB_NB 32, SW_W 1,024, SM_H 16, SM_LPH 16, S_RD 16, S_WR 16. These are the routed tiles' parameters. Record: `../smt_qualification/full_gate/run_full_dpi_m{0,1,5}_a0_h.json` @ `47c89defd`. m0 PASS 0/1,722 rows on all three runs, 3,146 cycles; m1 and m5 FAIL.

The record carries per-job start and done stamps. A job's cycles run from the core accepting the command to `c_done_v` after the last result row is written, with a behavioural VM of read latency 10 and no die transport. That is a lower bound of the priced node.

| job | flat master | hierarchical slab | price | ratio | 1.10 gate |
|---|---|---|---|---|---|
| QN | 229 | 301 | 288.0 | 1.045 | pass (15 cycles of margin for die transport) |
| KV | 225 | 357 | 283.0 | 1.261 | FAIL |
| QB | 65 | 166 | 80.0 | 2.075 | FAIL |
| SW | 201 | 352 | 191.0 | 1.843 | FAIL |
| SE T 640 | 275 | 466 | 795.3 | 0.586 | pass |
| SE T 128 | 196 | 386 | 691.2 | 0.558 | pass |
| SO | 112 | 303 | 244.9 | 1.237 | FAIL |

The flat master column (`results/rtl/s81_suhc_su_gate_20261011/run_full_dpi_m0_a0.json`) is context only, not a price. The reduced gate (0/269, 2,246 cycles) is S_RD 2, SM_H 2, SW_W 64: not production shape, not usable for throughput.

**Where the extra cycles are.** Not instrumented per stage; the flat to hierarchical deltas are QB +101, SW +151, KV +132, SO +191, QN +72, SE +190. From the stream's design notes the added latency is:
- every job: the control tile's accounting rung, the spine relay stations to the job's stop (TK order QN, KV, QB, SW, SM, so SM is the farthest) and the registered return chain;
- QB and SW: the tap assembles a pass before the engines start, and the engines are time-shared (swe runs one lane pipeline over 8 lanes, 8 cycles a beat; qbe one slot);
- SW: the two SRAM wait lines and the 4-pass output chain, then the quant stop;
- KV and QN: one time-shared multiplier a lane in the norm engines and the split reduce tree (qnh then qnr); KV adds the RoPE tail and the QDQ stop;
- SO: operand rows relayed SRL + 2 stations past smt to the divide engines, then the write-back chain.

A per-stage split needs job-phase stamps in `tb_s81_su_master` (tap in, engine first in, engine last out, last write).

## Source match

For every routed kit except QNT CB32, all RTL files in the kit's source list are byte-identical at the routed commit and at the gate commit `b132ae0da` (`source_match.json`). The closed physical variants checked here (smt hb1 and hb2, swe spx and gfix) change no RTL. QNT CB16/CB32 (`c904b01fb`) changes `ot_s81_su_qn.sv` and `dsfd_su_t_qn.sv`; its own record (`results/rtl/s81su_qnt_cb_c904b01fb_20261013/final` @ `70ac518d7`) is a lockstep against the `69c124e5d` tap on the routed bytes (sha256 `e33c4f5e...`), all 4,305 output bits every cycle, 18,670 checks, 0 added cycles, MUT 6 FAIL.

Two gaps apply to every tile, so none meets "passing bench + failing mutant on the same source bytes":
1. **The gate never compiles the routed tops.** `dsfd_sp_su_h` instantiates `ot_s81_su_*` directly. The `dsfd_su_t_*` wrappers (`dsfd_su_t_{sm,sw,qn,kv}.sv`, `dsfd_su_tiles.sv`) are not in the build. Their fixed parameters equal the slab's full-shape values by inspection only.
2. **Every committed gate is `--fp dpi`.** Six FP primitive files in the routed source lists (`ot_hdc_fastfp.sv`, `ot_hdc_fp32_f12.sv`, `ot_hdc_fp32_mul_lat.sv`, `ot_hdc_fp32_add_lat.sv`, `ot_hdc_prefix.sv`, `ot_dsrom_fp32_add_l6.sv`) are replaced by DPI models. The control tile has none of them.

Mutants live in the control tile and adapter (1, 2), the QN and KV taps (4, reduced gate only), smd (5) and the QNT control bank (6). The other tiles have no mutant of their own; the composition gate's mutants stand for them.

`rtl_fp_gate.json`, when present, is this agent's `--fp rtl` run of the same gate on the `b132ae0da` bytes.

## Per tile

See `table.json` `tiles[]`: routed kit and commit, byte equality, evidence path, the jobs the tile serves with measured, price and ratio, verdict and what is missing. The assignment of the five SM masters to SE or SO follows their roles in the stream log (sml, smc, smr on SE; smd on SO; smt on both) and is not instrumented.

| tiles | limiting job | ratio | throughput |
|---|---|---|---|
| qnt (cb32), qne, qnh, qnr | QN | 1.045 | within 1.10 at the slab pins |
| sml, smc, smr | SE | 0.586 | within 1.10 |
| smt, smd | SO | 1.237 | FAIL |
| kve, kvp, kvr | KV | 1.261 | FAIL |
| swe | SW | 1.843 | FAIL |
| ctl | QB (it sequences every job) | 2.075 | FAIL |
