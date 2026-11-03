# S81 svc memory fit (MEM v2, DIE-S81-51/MEM, 2026-11-03)

This packet right-sizes the v1 class port (`s81_svc_memory_closure_1103`, T7 12605dc2) for the 15 svc types. The v1 port put 32 x 256x256_m2 and 34 x 32x64 masters into each type. Here every capture child and both staging instances are rebound to masters sized to the rows and bits they actually use. The children are port-identical, so the bound changes only in 5 module names per type (`fit_v2` in `tools/die_plan/s81_svc_memory_closure.py`, which is idempotent). Control logic and cycles are unchanged.

| memory | v1 (per type) | v2 (per type) | why |
|---|---|---|---|
| LAND 640x256 x 3 writers | 12 x 256x256_m2_r2c2, 85,166 um2 | 12 x **160x256_m1_r0c0** (new), 43,552 um2 | 4 row banks x 3 writers each use 160 of 256 rows. Rows 160..255 are never written (ch_row < 640) and read their zero start; v2 returns that 0 through a registered row-range flag. |
| staging 8 lanes x 160x265 | 16 x 256x256_m2_r2c2, 113,555 um2 | 8 x **160x265_m1_r0c0** (new), 30,932 um2 | One master per lane instead of 2 x 256-bit stripes (`ot_hdc_v41x_attn_staging_fit`). It applies only at DEPTH<=160 and ROWW==265; other parameters keep the original striping. |
| PMEM 2 banks x 512 bits x 256 | 4 x 256x256_m2_r2c2, 28,389 um2 | 4 x **256x256_m1_r0c0** (new), 15,327 um2 | Same banking. The 2:1 column mux and the repair rows/columns are dropped (no-repair rule 10-25). |
| PVQ 8 x 2120 | 34 x 32x64_m1, 18,782 um2 | 17 x 32x128_m1_r0c0 (existing view), 18,193 um2 | Pairs of 64-bit banks share the read enable and both addresses. The per-bit mask keeps each pair independent. |
| **total new** | **66 inst, 245,881 um2** | **41 inst, 108,004 um2 (-56%)** | |

TT clk->q: 160x265 is 338 ps (v1 256x256_m2 was 405-441), 160x256 is 380, 256x256_m1 is 417 (+12 ps against v1), and 32x128 is 270. The staging read cone gets about 67-100 ps better, so it needs no extra read cycle.

**Gate** (`run.sh`; Verilator 5.050, two-state zero start, 833 ps, 20,000 random edges):
- Each v2 child is checked against the v1 child it replaces, on the same stimulus, every edge.
- Staging is checked against both native SRAM_MACRO=0 and the v1 SRAM_MACRO=1 form, whenever rd_addr < DEPTH.
- Stimulus covers out-of-range LAND reads (oob 1108, wrap 3222), one-sided PVQ pair masks, and 10% out-of-range staging addresses.
- Result: positive `FIT_PASS`, and 5/5 independent mutants FAIL (LAND mask dropped, LAND range off by one, PMEM bank address, PVQ pair half, staging lane swap).

The v1 children were gated against the native T7 bound (LAND/PMEM/PVQ cuts, STAGE gate). EQ to native follows by composition.

**Macro views**: `tools/mem_compiler/build_s81_svc_fit_1103.py` (sram_gen + aligned-v2 outline rules, like the r0c0 64x512 builder) writes `physical/asap7_memory_macros_v2/ot_sram_1r1w_{160x256,160x265,256x256}_m1_r0c0`.

**Apply**: `python3 tools/die_plan/s81_svc_memory_closure.py --kit-rtl <kit rtl dir> --closed-dir results/rtl/s81_svc_memory_fit_1103` (`--form v2` is now the default; `--form v1` gives the 12605dc2 port). The packet `closed/` holds the 15 v2 bounds. `closure.json` keeps the kit-bound `before_sha256`, so it is reused only on the same kit bound; `make_v2_packet.py` rebuilds it from the v1 packet.

**Glue macros already in every svc type** (25, never placed by the plan; owner sources, unchanged here):
- 13 x 1024x256_m2_r2c2 in `dsdv_idx_rg3_nq_native`, 160,124 um2: 2 lf (LFD 256 deep), 8 h0/h1 (rows <= 767), iq (512 x 35), mq (124-deep ring x 23), sq (256 x 39).
- 8 x 16x340_p192 CDC FIFOs in `ot_s81ph_ctrl_pcr` (wide pin pitch, SAFE item 6), 92,234 um2.
- 4 x 32x64 in `dsdv_sm_so_target`, 2,210 um2.

None of them can merge: each is its own 1R1W stream with concurrent read and write addresses, or a separate clock crossing, so merging would need more ports. Only the idx set can be right-sized: 256x256_m1 x2, 768x256_m2 x8, 512x36_m2, 256x40, 128x24 = 87.3k um2 (-72.8k). That is a separate EQ-gated source event in `dsdv_idx_rg3_nq_native` (the h-row and mq-ring bounds need proof) and is not done here.

**Pilots** (`pilot.sh`, intel1): `svc_hi_dsdv_svc_rs__t1` (rs class, 13 types) and `svc_hi_dsdv_svc_pvso_entry__t1` (pvso class, 2 types). Both pass GEN_LINT (rtl_check, memory_bits and pins_vs_plan all PASS) and KIT_PREFLIGHT, with SYNTH_MEMORY_MAX_BITS 16384. Receipts are in `pilot/`.
