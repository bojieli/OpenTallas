# HBM-NEXT-UNITS-SUDMA2: SU.VOP row II, wide ARGMAX.LOCAL, programme-column row code

Lane HBM-NEXT-UNITS-SUDMA2, 2026-10-19, branch `claude/hbm-next-units-sudma2-1019`. Next-release work, not a release gate.
It follows `../sudma/README.md` (SU_DMA, 01:41), which measured SU.VOP II 44/72 and ARGMAX.LOCAL II 169 against prices of 7 and 6.

All benches ran on the fleet (ot-epyc4 = `regular-crane`; ot-epyc5) with Verilator 5.050 (`verilator.txt` in each folder).
They use `tools/hbm_next/hnx_sudma_bench.sh` from a `git archive` bundle of `f76f44b19` (stages w0 to w3, aw), `0ce18a1a7` (stage p)
and the synth script `tools/hbm_next/hnx_sudma2_synth.sh` (Yosys + ASAP7, area in um²).

## Measured row II against the price

| Record | cycles(N), first command to last write | Measured II | Before (SU_DMA) | Price | Verdict |
|---|---|---:|---:|---:|---|
| SU.VOP `AB`, n = 7,168 (nv = 14), split write phase | N1 152, N2 180, N3 208, N4 236, N6 292 | **28** | 44 | 7 | EXACT. Store write port no longer binds; VM fill bandwidth binds. |
| SU.VOP `ABC`, split write phase | N1 180, N4 348, N6 460 | **56** | 72 | 7 | EXACT. Same binding. |
| SU.VOP, wsplit 0 (d4g schedule on the hnx top) | `ab_n1` 160, `ab_n4` 292, `abc_n1` 216 | 44 / 72 | = stage s0 | | EXACT. These are the d4g cycles and writes, bit for bit. |
| ARGMAX.LOCAL, DS n = 1,347 (169 sectors), wide reader | P1 67, P6 177 (edges G to done) | **22** | 169 | 6 | EXACT on 3 seeds. Slice read bandwidth (8 banks) binds. |

### SU.VOP split store write phase (`wsplit`)

**Mechanism.** Each pinned store bank still has one write port. The new RTL time-shares it in a fixed phase, so the lane result no longer costs its own write edges.
- The fill writes the HI = 0 store groups on even bank-write edges and the HI = 1 groups on odd edges.
- The compiler puts each lane-write edge W on a fill-HI0 edge. HI = 1 banks commit the lane result at W, while the fill is on HI0. `ot_hnx_su_wsplit` defers the HI = 0 banks' result to W + 1, while the fill is on HI1. No queue, no ready: a collision faults (`st_conflict`, `clash`).
- Files: `rtl/hbm_next/su/ot_hnx_su_wsplit.sv` (one per pinned bank) and the forks `ot_hnx_su_pgslice.sv`, `ot_hnx_su_quarter.sv`, `ot_hnx_su_top.sv`. The `wsplit` parameter is 0 for the d4g behaviour.
- The compiler is `tools/hbm_next/su_rows_compile.py --wsplit 1`. Its schedule is II = 2·k·nv512, where k is the number of per-row VM operands. Before the change it was (2k + 1)·nv512 + 2.

**Why it stops at 2·k·nv and not at the price of 7.**
- The fill is now the only thing on the store write port. The 32 VM read ports deliver one 512-word vector every 2 edges.
- Reaching 7 would need about 4x the VM-to-SU fill bandwidth (k·nv / 4 edges a row), or a fill bypass straight into the lane operand.
- That is a VM/SU datapath change. It is not proposed, because the SU is not the bottleneck (about 157k busy of a 1.28M P = 6 verify).
- CMTP should price SU.VOP rows at II = 2·k·nv512.

**Area.**
- `ot_hnx_su_wsplit`: 17.99 um², 87 cells (`synth/area.txt`).
- One per pinned bank: 512 banks give about 0.009 mm² for the SU.

**Bench.** `rtl/hbm_next/su/tb/tb_hnx_su_rows_ws.sv`, a fork of `tb_hnx_su_rows` with the same independent NumPy golden.
- What is checked: every LG write (edge, quarter, port, sector, mask, data), the per-edge lane write count, zero DUT/rowx faults, and that every expectation is consumed.
- Positive cases (`wsplit/w0/verdict_w0.txt`), all PASS: `AB` at N = 1, 2, 3, 4, 6; `ABC` at N = 1, 4, 6; and wsplit 0 on the d4g vectors `ab_n1`, `ab_n4`, `abc_n1`.
- Fail witnesses, all committed:

| Witness | What it breaks | Result | Log |
|---|---|---|---|
| `ws_ab_n4_fw11` | schedule parity: lane writes on the wrong phase | FAIL, 1,742 errors | `wsplit/w0/run_w0_ws_ab_n4_fw11.log` |
| WMUT 1 | deferral dropped | FAIL, 942 errors | `wsplit/w1/` |
| WMUT 2 | the HI = 1 half deferred instead of HI = 0 | FAIL, 1,710 errors | `wsplit/w2/` |
| WMUT 3 | deferred address not captured | FAIL, 1,792 errors | `wsplit/w3/` |

### Wide ARGMAX.LOCAL (`ot_hnx_argmax_wide_rows`)

**Mechanism.** The reader takes one beat of up to WS = 8 consecutive sectors per edge.
- Sectors cs to cs + 7 sit on the 8 distinct banks of the SW slice, so a beat is one read per bank: the slice's full read bandwidth.
- The closed engine `ot_hgi_argmax18_m` runs at LP = 64 lanes. This is a parameter change only. The lower-index tie tree keeps `numpy.argmax` semantics.
- Row read period = max(ceil(ns / 8), PMIN). PMIN = 6.

**Why PMIN = 6.** A 5-edge period re-uses the hub write-tag slot too early.
- The PMIN 5 run FAULTS the hub on seeds 1 and 2 (rows 4, n 64). Witness: `argmax/pmin5_witness/`, bundle `6ca25c769`.
- `f76f44b19` sets PMIN to 6.

**The remaining gap to the price of 6.** 1,347 words need 22 beats on one slice. The price would need a row spread over about 4 slices; that is a compiler/VM placement question.

**Area.**
- The wide reader is 29,764 um², 220,524 cells.
- The 8-lane reader is 4,342 um².
- The difference is +0.025 mm² per instance.

**Bench.** `rtl/hbm_next/argmax/tb/tb_hnx_argmax_wide.sv` with vectors from `tools/hbm_next/hnx_argmax_wide_vectors.py` (seeds 0 to 2). Verdicts are in `argmax/verdict_aw.txt`.
- MUT 0 PASS on 3 seeds. The 4 faults are the deliberately illegal records.
- WS 1, PMIN 1 on the ORIGINAL vectors PASS. That is the original reader, edge for edge (`aw_mo_so.log`).
- Mutants, all FAIL on every seed:
  - MUT 1: A row stride;
  - MUT 2: O row stride;
  - MUT 3: id offset taken from row 0;
  - MUT 4: beat bank rotation dropped;
  - MUT 5: last-beat sector mask dropped.

### Row code as a programme column (next-list item 1 of SU_DMA)

**Mechanism.** The 20-bit row code moves into the spare top bits of column 9.
- The quarter line grows from SB 2422 to 2442 b, with the same 10 columns.
- `su_rows_compile.py` emits `prog_rc.mem`. The d4g compiler `su_programme_compile.py --line-bits 9768 --partition 4` builds the dictionaries.
- The d4g producers `ot_hbm_su_programme_part` (PIPE 2) are unchanged and run lockstep against the monolithic producer and the golden.

**Results** (`progcol/verdict_p.txt`):
- `ws_ab_n6` PASS: 296 edges, 52 macros (49 for the monolithic producer).
- `ws_abc_n6` PASS: 464 edges, 64 macros (60 monolithic).
- The template, pcoff and phase mutants FAIL, as they do in d4g.
- `rcdrop` (the image compiled without the row code, checked against a golden with it) FAILS.

**Not done.** `sfu_programme_store_r10` is a CRITICAL prefix, so no tile was gated or submitted for this item.

## Not done (next list, in risk order)

1. **Reducer row class**: red a/b/dst scratch and RF tag stride per row, for norm-style SU.VOP rows. Without it, each row's scratch words go into the image, and only the red column dictionary grows.
2. **SFU chain row stepping** (`ot_hgi_sfu_core_split3`, `sfu_lg_pair_tap_leaf*`): the address step per `start_loops` iteration.
3. **FUSED.QDQ rows** (`hb_quant_*`, n/32) and position-addressed **DMA.LOAD** rows. Neither has been measured yet.
4. **Gate the touched hnx tiles** with hnx kits: the `ot_hnx_su_pgslice` + `wsplit` slice and `ot_hnx_argmax_wide_rows`. Report the SU parent and the programme store as CRITICAL; report only.
5. **CMTP re-price**:

| Family | II to price |
|---|---|
| SU.VOP | 2·k·nv512 (`wsplit`) |
| ARGMAX.LOCAL | max(ceil(ns / 8), 6) = 22 for DS |
| DMA.KVWB_DS | 8, plus 28 per wrap (unchanged) |


## Step 2 (SUDMA2 restart, 10-19 03:40+): reducer row class, SFU chain row step, FUSED.QDQ rows

Branch `claude/hbm-next-units-sudma3-1019`. All on the fleet with Verilator 5.050, stages `r`, `f`, `q` of
`tools/hbm_next/hnx_sudma_bench.sh` from `git archive` bundles (`1ec36302d` r, `6ed5f2031` f, `77ad24fe7` q). Evidence:
`red_rows/`, `sfu_rows/`, `qdq_rows/` (verdict file, every run log, fail witnesses, `programme.json` / `meta.json`).

| Record | Mechanism | cycles(N) | Measured row II | Price | Verdict |
|---|---|---|---:|---:|---|
| SU norm-style row reduction (m = 128 lane partials a quarter, 10 chains + tree + export, cross-quarter sum on reducer 0, RF broadcast + 4 RF sector drains a row) | NEW `ot_hnx_su_rowr` (reducer / RF row class) in front of the 4 d4g qcores | N1 266, N2 409, N3 552, N4 695, N6 981 | **143** = m + 15 (reducer 0's command slot: 128 + 9 tree + 1 export + 4 cross + 1 export) | (inside SU.VOP) | EXACT, abs = rel |
| SFU chain rows (IO calendar looped N x) | NEW `ot_hnx_sfu_rowstep` after the d4g store r10 (unchanged) | row arith starts exactly P apart | **P** (IO words a row; 0 bubble at the loop wrap) with P >= Pc + 3 | (FUSED / SU chain) | EXACT vs the unrolled image, 3 seeds |
| FUSED.QDQ_FP8 / FP4_E4M3 rows, e = 512 | compiler only: one programme range, row-strided src / dst, d4g `ot_hgi_qdq_program_static` | LG0: 59 / 75 / 91 / 107 / 139 (N 1/2/3/4/6); die split form (IO_REGS 1 LG 1 TSPLIT 1): 64 / 80 / 96 / 112 / 144 | **16** = e / 32 | n / 32 = 16 | EXACT; II = price; c1 59 / 64 vs priced ceil(n/32) + 8 = 24 |

### Reducer / RF row class (`rtl/hbm_next/su/ot_hnx_su_rowr.sv`)

- Steps the two command classes rowx leaves alone: `red_cmd` (a / b / dst scratch by the op's use, the EXPORT's RF word
  tag[7:0] when tag[8]) and the six `rf_rd_cmd` classes (RF word; class 5 must stay sector aligned). Row code extension
  rc2 = {RF row 4, reducer row 4} (8 b; column 9 spare bits: 2442 -> 2450 b a quarter line, still 10 columns);
  strides s_red (10 b scratch words), s_rf (8 b RF words). Row 0 = the d4g words; REG 1 like rowx (stays aligned).
  Faults: scratch carry out of 1,024, RF word carry out of 256, class 5 not sector aligned.
- Why it matters: rows OVERLAP (row r + 1's lane chains fill the command slots while row r's 10-edge-dependent tree,
  export and cross-quarter sum finish), which needs disjoint scratch / RF words a row. Dictionary words a quarter
  image: red 144 / rf 9 row-relative at every N vs 576 / 36 unrolled at N 4 (grows N x).
- Vehicle (`rtl/hbm_next/su/tb/tb_hnx_su_red_rows.sv`): the 4 d4g `ot_hbm_su_static_qcore` (RF replica + reducer,
  unchanged) behind 4 rowr, with the top's RF relay routes (RF_RELAY 8, same always blocks as `ot_hnx_su_top`); the
  slices are represented by their registered lane outputs `slice_x` and the drain bit on the compiler's edges.
  Checks every scalar (edge, quarter, tag, value), every class-1 broadcast word at `rf_bword`, every class-5 sector at
  `rf_dsec`, zero qcore / rowr faults. Compiler + golden: `tools/hbm_next/su_red_rows_compile.py` (hdc_golden add).
- PASS: N 1, 2, 3, 4, 6 (m 128), m 64 N 4 (435), seed 1 N 4, `--absolute` N 4 (rc2 = 0, strides 0: identical
  expectations and edges = the d4g qcore bit for bit). FAIL witnesses (all committed): MUT 1 dst stride (75 errors),
  MUT 2 export tag stride (75), MUT 3 RF read stride (63), MUT 4 a / b stride (75), `ovf` (s_red 400 -> rowr FAULT).
- II = m + 15 is the reducer-0 command slot (one command an edge). Rotating the cross-quarter sum over the four
  reducers by row (compiler only) would give m + 11.25; not done (< 3 %).

### SFU chain row step (`rtl/hbm_next/su/ot_hnx_sfu_rowstep.sv`)

- The d4g SFU programme store already loops [base, limit) N times with no bubble; this stage adds row x stride to the
  VM fields of the 471-b `io_word` (8 prefetch sectors by s_rd, 2 drain sectors by s_wr; local / scalar / lane fields
  and `compiler_control` untouched). Row index from the store's `io_ordinal`, incremental (one adder a stride).
  **Measured: the r10 store's io_ordinal LEADS io_word by one edge** (first run, bundle 1ec36302d, OLAG 0: exactly the
  last word of every row took the next row's offset) -> OLAG 1 delays it (fixed RTL above).
- Broadcast operands go in a prologue launch (P0 <= P words, ordinal restarts at 0 = unstepped); per-row operands share
  one sector stride a direction (rs_A = rs_B; otherwise the compiler unrolls). Programme (arithmetic) calendar started
  once a row by the body's arith-start bit; **measured minimum row period P = Pc + 3** (DP 0 / 1 / 2 fault the store's
  start-while-busy check, DP 3 passes; `f_m0_dp*.log`, outcome lines only).
- Vehicle (`tb_hnx_sfu_rows`): two d4g r10 stores in lockstep: A = row-0 image looped N x + rowstep, B = the unrolled
  absolute image + a pass-through rowstep; every edge A's (io_word, compiler_control) == B's, no fault, row arith
  starts exactly P apart, two rounds (reload, new N / P) prove the ordinal-0 restart. The SFU core consumes only these
  two buses, so equality is the core's behaviour bit for bit.
- PASS seeds 1, 2, 3. FAIL witnesses: MUT 1 drain stride (279 mismatching edges), MUT 2 prefetch stride (581), MUT 3
  early wrap (11), MUT 4 no ordinal-0 clear (581), BADSTRIDE s_rd[2:0] != 0 (row-step FAULT). Note: Verilator ends a
  `$finish` at the end of the time step, so the DP-sweep logs print a FAIL line after their RESTART line (classification
  runs only; the RESTART line is the result).

### FUSED.QDQ_* rows (compiler only; `tools/hbm_next/hnx_qdq_rows_vectors.py`, `rtl/hbm_next/qdq/tb/tb_hnx_qdq_rows.sv`)

- The d4g static QDQ issues one 32-element beat a cycle from a fixed programme; an N-row record is the N rows' beats in
  one range with row-strided src / dst (COMPACT record calendar: one word a row). Bench = the d4g `tb_hgi_qdq_static`
  (decoder + 8 real VM bank pipelines) with its beat-a-cycle issue assert, per-row golden (hdc_golden_v41 qdq_fp8 /
  qdq_fp4_e4m3), SRAM readback; the programme / record cross-check and the whole-run price bound are reported.
- **II 16 = n / 32 = price** (rows back to back, every beat on its edge). **c1 59 (LG 0) / 64 (die split form) vs
  priced 24**: the fixed pipeline (issue +5, RL, decode DL 25, write commit) is ~43 / 48 edges, not 8. CMTP: c1 + 35 / +40
  a QDQ record (once a record, not a row).
- FAIL witnesses: programme without the row stride (`mstride_n4`, gold mismatch) on both forms; d4g MUT 1 sector map.
- DMA.LOAD position-addressed rows: NOT measured (no die-bound static load-record engine; the load path is the HBM
  service VM delivery) -> next list.

### CMTP re-price (this step)

| Family | Row II | c1 |
|---|---|---|
| SU.VOP with a per-row reduction (norm-style) | add max(m + 15, the VOP II) a row on reducer 0 (m = lane partials a quarter) | measured 266 at m 128 |
| SFU chain rows | P (IO words a row), P >= Pc + 3 | unchanged |
| FUSED.QDQ_* | n / 32 (= price) | 59 (die form 64), price 24 |

### Area and physical integration (synth `synth_step2/area.txt`, yosys 0.68 + ASAP7 RVT TT, `tools/hbm_next/hnx_sudma3_synth.sh`)

| Block | um² | cells | Count a die | Where it goes |
|---|---:|---:|---:|---|
| `ot_hnx_su_rowx` (REG 1: the whole 2,422-b line registered) | 1,517 | 8,608 | 4 (one a quarter) | the SU programme parent between the 10 column leaves and the slices (critical parent: report only) |
| `ot_hnx_su_rowr` | 123 | 1,044 | 4 | same place as rowx (red / rf fields, column 0) |
| `ot_hnx_sfu_rowstep` (REG 1: io_word + compiler_control registered) | 928 | 4,016 | 4 (one an SFU core) | the SFU core cluster's input pin stage (`io_r` / `ctl_r` of split2 absorb the register: then only the adders remain) |
| `ot_hnx_su_wsplit` + write mux | 18 | 87 | 512 | folded into the bank tile: `ot_hnx_su_bank6_ws` (kit `hnx_su_bank6_ws_1019`, gate below) |

Total < 0.02 mm² a die. None of the row stages is worth a standalone hard tile (pin-dominated, util < 30 %): they fold
into the neighbour that already registers the same bus.

### Gate (running at hand-off)

`hnx_su_bank6_ws_1019` (kit spec `physical/hbm_next/kits/hnx_su_bank6_ws_1019.json`; the gate tool hard-codes
`physical/ref_tile/`, so the generated kit sits at `physical/ref_tile/hnx_su_bank6_ws_1019/`): the d4g closed bank tile
outline 369.36 x 151.2 um and its 6 SRAM macros, W face +45 pins. `pre_route_gate --remote auto --cts` running on
ot-epyc7 (`ref_gate/hnx_su_bank6_ws_1019-20261019-040018`). Not on a critical prefix, but NOT submitted: a tile-level
wsplit bench (fork of `tools/hbm_static/su_bank_run.sh` with the wrapper + WMUT witnesses) is still to write; the
SU slice parent that instantiates it (`su_<Q><g>`, 1,797 x 2,825 um) is a critical parent: report only.

## Next (SUDMA2)

1. Collect the bank gate; report PNG + checklist to COORD-REVIEW-QUEUE [HBM-NEXT]; tile bench + witnesses, then submit.
2. DMA.LOAD position-addressed rows: the load path is the off-die HBM service (elastic boundary: `ot_hbm_svc_async_fifo`,
   loader service); a row record is a descriptor with a per-row HBM address (position x row bytes), no on-die row engine
   change. Measuring needs the HBM service bench (VEH / HBM lane), PRICED stays.
3. Fold rowx + rowr into the SU programme parent and rowstep into the SFU core pin stage (critical parents: report).
4. Optional: rotate the cross-quarter reduction over the 4 reducers by row (compiler only, II m + 15 -> m + 11.25).
