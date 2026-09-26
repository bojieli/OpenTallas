# Memory compilers, memory self-test and repair (ASAP7)

This is the tape-out workstream "Memory compilers" and "Memory self-test and
repair" of `docs/TOKEN_PIPELINE_OPTIMIZATION_PLAN.md` section 6, for all three
architectures (HBM comparator, Qwen3-8B ROM reticle, DeepSeek-V4.1-Flash ROM
array).

**Evidence class.** ASAP7 is a *predictive* PDK. The macros are abstract
views (LEF, Liberty, Verilog) generated from an analytical model. The model
is built on this repository's own DRC-clean ASAP7 bitcell layouts and on
ASAP7 standard-cell delays, and it is calibrated to one published 7 nm SRAM
macro. There is no transistor layout of any macro periphery and no SPICE of
a macro. Nothing here is a foundry N7 number or silicon. Every constant the
model uses is written into each macro's datasheet (`<name>.json`) with a
grade: *measured*, *published*, *calibrated* or *assumed*.

## What exists

| Item | Where |
|---|---|
| SRAM compiler (1RW, 1R1W, 2RW; words × bits, column mux, banks, spare rows, spare IO columns) | `tools/mem_compiler/sram_gen.py` |
| Via-programmed NOR mask-ROM compiler and per-instance personalisation | `tools/mem_compiler/rom_gen.py` |
| Shared view writers (LEF, NLDM Liberty, blackbox) and the behavioural model with the physical array, repair steering and fault model | `tools/mem_compiler/views.py`, `behav.py` |
| ASAP7 inputs: measured bitcells, the standard-cell calibration frozen from the pinned ORFS image, published and assumed constants | `tools/mem_compiler/asap7.py`, `asap7_calibration.json` |
| SECDED code and the ROM signature (CRC-32) | `tools/mem_compiler/ecc.py` |
| Macro library: 16 macros with LEF, TT/SS/FF liberty, behavioural and blackbox views, datasheet, index with view hashes | `physical/asap7_memory_macros/` (config `configs/memories/asap7_macros.json`, build `tools/mem_compiler/build_library.py`) |
| Memory map of the three architectures onto the macros | `tools/mem_compiler/memory_plan.py` → `results/memory/memory_plan.json` |
| ROM defect tolerance, SECDED against spare rows | `tools/mem_compiler/rom_repair_eval.py` → `results/memory/rom_repair_evaluation.json` |
| MBIST: shared March controller, BIRA repair analysis, SRAM and ROM collars, SECDED decoder | `rtl/dft/ot_mbist_ctrl.sv`, `ot_mbist_bira.sv`, `ot_mbist_sram_collar.sv`, `ot_mbist_rom_collar.sv`, `ot_rom_secded_dec.sv` |
| Fault campaign (Verilator) | `tools/rtl_mbist_campaign.py` → `results/rtl/mbist_campaign.json` |
| Qwen decode-core memory subsystem built from the macros, with MBIST | `rtl/hdc/ot_hdc_memsys.sv`; `tools/rtl_hdc_decode_campaign.py --memory-macros` → `results/rtl/hdc_decode_campaign_memory_macros.json` |
| Hard-macro route of an SRAM, a ROM and the BIST on ASAP7 | `rtl/dft/ot_mbist_macro_testtop.sv` → `results/physical_abi3/asap7/mbist_macro_testtop/` |
| Tests | `tests/test_mem_compiler.py`, `tests/test_mem_compiler_mbist.py` |

### Using the views (full-chip integration)

`physical/asap7_memory_macros/index.json` lists every macro with its size,
density, clock-to-output and fmax per corner, and the SHA-256 of each view.
The layout of each macro directory:

- `<name>/<name>.lef` is the abstract. Signal pins are on M4 at the left and
  right edges. VDD and VSS are full-width M4 straps, which the ASAP7 macro PDN
  grid reaches with M4–M5 vias. There are OBS rectangles on M1–M4.
- `<name>/<name>_{tt,ss,ff}.lib` are the three liberty corners.
- `<name>/<name>_bb.v` is the synthesis blackbox.
- `<name>/<name>.v` is the simulation model.

The physical flow routes these macros with:

```bash
python3 tools/run_abi3_physical.py ... --stages pnr \
    --macro-view NAME=physical/asap7_memory_macros/NAME --macro-place-halo 2 2
```

That option emits `ADDITIONAL_LEFS`, `ADDITIONAL_LIBS`, `SYNTH_BLACKBOXES`
and `GDS_ALLOW_EMPTY` into the ORFS `config.mk`. These are the same mechanisms
ORFS uses for its own `fakeram7_*` macros. Like `fakeram7`, the views have no
GDS.

## 1. SRAM compiler

**Approach.** The compiler is FakeRAM2.0-style: the flow gets an abstract
plus timing, and no transistor layout is drawn. The ORFS image ships ASAP7
`fakeram7_*` macros from FakeRAM2.0, whose own configuration file says
*"SAMPLE INPUT FILE; VALUES NOT REALISTIC"*. For example, `fakeram7_256x32`
has a flat 218 ps clock-to-output for every load and slew.

Every number here is derived instead:

- **Array.** The 6T thin cell measured DRC-clean in ASAP7
  (`results/asap7_physical/bitcell_density`) is 108 × 216 nm = 0.023328 µm².
  One more row adds 0.108 µm to a bitline; one more column adds 0.216 µm to a
  wordline. The 1R1W and 2RW cells are 1.4× and 2.0× that area. These two
  ratios are *assumed*; only the 6T was drawn.
- **Periphery.**
  - Row decoder and wordline-driver strip: width grows with log2(rows).
  - Column strip (precharge, column mux, sense amplifiers, write drivers,
    output latches): height grows with log2(mux).
  - Spare-row address comparators and spare-IO steering multiplexers.
  - Bank control.
- **Calibration.** One free dimension, the fixed height of the column strip,
  is solved so that a 512 × 512 array (2,048 × 128, mux 4) reaches the
  efficiency of the published 7 nm macro. That macro is Yokoyama et al.,
  *A 29.2 Mb/mm² Ultra High Density SRAM Macro using 7nm FinFET Technology*,
  IEEE VLSI Circuits 2020 (doi:10.1109/VLSICircuits18222.2020.9162985): one
  512 × 512 array at 29.2 Mb/mm². On TSMC's published 0.027 µm² N7 HD cell
  (`configs/hardware/technology.json` `nodes.N7`), that density means the
  array fills 0.788 of the macro.
- **Timing.**
  - FO4 delay, inverter drive and flop setup, hold and clock-to-Q per corner
    are extracted from the ASAP7 RVT liberty inside the pinned ORFS image by
    `asap7.py --calibrate`: TT 0.70 V / 25 °C, SS 0.63 V / 100 °C,
    FF 0.77 V / 0 °C. FO4 is 18.3 / 23.6 / 14.8 ps.
  - Wordline and bitline RC come from ASAP7's `setRC.tcl`, as an Elmore delay
    plus the charge time of the bitline swing.
  - The cell read current (20 µA TT), the junction load per cell (0.045 fF),
    the sense swing (100 mV) and the FO4 depth of each periphery stage are
    *assumed*. They are listed in every datasheet.
- **Views.**
  - Liberty is NLDM in ps / fF / fJ / nW: 5 × 5 delay, transition and
    constraint tables per corner, `min_period`, and read energy on the clock
    pin. Leakage uses `power.static_leakage_w_per_mm2.sram_array` from
    `technology.json`.
  - A macro whose pins do not fit its edge is stretched, and the datasheet
    records the stretch.
- **Behavioural model.**
  - It holds the *physical* array, spare rows and spare IO columns included,
    with the bits interleaved by the column mux: data bit *b* at column
    select *s* is physical column *b·mux + s*.
  - Repair is applied as the hard macro would apply it: `rr_en/rr_addr` per
    spare row (a row-address comparator) and `cr_en/cr_sel` per spare IO
    column (IO steering).
  - Under `+define+OT_MEM_FAULTS` it adds the fault model used by the MBIST
    campaign: stuck-at, transition, CFin/CFid/CFst coupling, three
    address-decoder faults, and wordline and bitline faults.

**Results** (`physical/asap7_memory_macros/index.json`; "r2c2" = 2 spare
rows + 2 spare IO columns):

| Macro | Size (µm) | Density (Mb/mm2) | Array efficiency | clk→Q TT / SS / FF (ps) | fmax TT / SS / FF (MHz) |
|---|---|---:|---:|---|---|
| `ot_sram_1rw_2048x128_m4` (calibration shape) | 118.8 × 65.6 | 33.6 | 0.785 | 506 / 648 / 416 | 2048 / 1594 / 2499 |
| `ot_sram_1rw_2048x128_m4_r2c2` | 122.9 × 66.2 | 32.2 | 0.752 | 535 / 685 / 439 | 1967 / 1532 / 2400 |
| `ot_sram_1r1w_1024x256_m2_r2c2` (KV) | 174.7 × 70.5 | 21.3 | 0.695 | 545 / 692 / 451 | 1897 / 1489 / 2297 |
| `ot_sram_1rw_256x64_m4_r2c2` | 66.3 × 17.8 | 13.9 | 0.323 | 336 / 436 / 272 | 3332 / 2563 / 4109 |
| `ot_sram_2rw_512x64_m4_r2c2` | 130.9 × 34.8 | 7.2 | 0.335 | 379 / 488 / 310 | 2899 / 2250 / 3545 |
| `ot_sram_1r1w_64x512_m1_r2c2` | 171.3 × 77.8 | 2.5 | 0.080 (pin-limited) | 366 / 460 / 306 | 2871 / 2282 / 3430 |

**Against published numbers.**

- **Density.** The calibration shape lands at 33.6 Mb/mm2 against the
  published 29.2 Mb/mm2, on the same 0.785 efficiency (0.788 before grid
  snapping). The whole 15% difference is the cell: ASAP7's DRC-measured
  0.0233 µm² thin cell against TSMC's 0.027 µm². So this is the same macro
  efficiency on a smaller cell, not a better periphery.
- **Small macros.** Their efficiency falls steeply: 0.32 at 16 kbit. This is
  the same shape the IHP SG13G2 foundry macros show
  (`results/spice/ihp_sg13g2_bitcell`). The analytical model's single
  `sram.array_efficiency` = 0.65 corresponds to macros of roughly 0.25 Mbit
  and up in this model.
- **Timing.** No ASAP7 SRAM timing is published. The ORFS `fakeram7_256x32`
  placeholder claims a 157 ps minimum period and a 218 ps clock-to-output. The
  compiled 256 × 64 (with spares) gives 300 ps and 336 ps at TT. The large
  macros run at about 2 GHz TT and 1.5 GHz SS, above the decode cores' 1 GHz
  target in every corner. The large macros' clock-to-output (0.5–0.7 ns at SS)
  is a real share of a 1 ns cycle, and it sets how much logic the core can
  put after a macro read.
- **Wide shallow SRAMs are pin-limited.** A 64 × 512 macro (the banked vector
  memory's organisation) has more pins than a 28 µm edge can carry at a
  96 nm pin pitch, so its height is set by its pins.

## 2. ROM compiler (via-programmed NOR mask ROM)

**Macro.** The bitcell is the DRC-clean ASAP7 via-programmed NOR cell,
108 × 54 nm = 0.005832 µm² (0.25 of the 6T). One more row adds 0.108 µm: a
gate plus its programmable drain contact. One more column adds 0.054 µm.

- **Array.** It adds a row of substrate taps every 128 rows. The IHP 130 nm
  ROM route found a minimum-pitch array illegal without taps
  (`results/spice/ihp_sg13g2_rom_macro`).
- **Periphery.** Row decoder and wordline drivers, the column mux,
  single-ended sense amplifiers and output latches.
- **Timing.** Characterised with every via present, which gives the heaviest
  bitline and the most discharging columns.
- **Content independence.** The LEF, the Liberty and the behavioural model
  do not depend on the content: every cell has its transistor, and only the
  drain via differs. `tests/test_mem_compiler.py` checks that two different
  personalisations leave all views byte-identical.

**Personalisation.** Running `rom_gen.py personalise` on an image produces,
per instance:

- the **via map** (`<instance>.viamap.hex`): one bit per physical cell,
  1 = via present;
- its **SHA-256**;
- the **CRC-32 signature**, which the ROM BIST must reproduce from the array;
- with `--ecc secded`, SECDED encoding of every word;
- per image, a **content signature**: a CRC over the sorted instance
  signatures, plus the SHA-256 of the via-map set.

For the V4.1 universal die, the per-die content signature works like this.
Every die carries the same macros with the same views. Each die gets a
different via-map set, a different signature file and a different content
signature, and the BIST checks each die against its own set. The behavioural
model loads `+OT_ROM_DIR=<dir>/<INSTANCE>.viamap.hex`, so simulation reads
exactly the via mask.

**Results:**

| Macro | Size (µm) | Density (Mb/mm2) | Array efficiency | clk→Q TT / SS (ps) | fmax TT / SS / FF (MHz) |
|---|---|---:|---:|---|---|
| `ot_rom_8192x266_m8` (weights, SECDED 256+10) | 122.3 × 119.3 | 149.4 | 0.871 | 787 / 999 | 1298 / 1018 / 1576 |
| `ot_rom_16384x266_m16` | 237.2 × 119.6 | 153.6 | 0.896 | 1050 / 1280 | 976 / 799 / 1137 |
| `ot_rom_8192x274_m8` (Engram rows, 264+10) | 125.7 × 119.3 | 149.6 | 0.873 | 792 / 1004 | 1290 / 1013 / 1564 |
| `ot_rom_4096x266_m8` (program) | 121.8 × 62.9 | 142.2 | 0.829 | 586 / 739 | 1789 / 1414 / 2152 |
| `ot_rom_4096x72_m8` (constants, 64+8) | 38.0 × 62.9 | 123.3 | 0.719 | 514 / 667 | 2054 / 1575 / 2547 |
| `ot_rom_1024x72_m8` | 37.2 × 20.5 | 96.7 | 0.564 | 350 / 456 | 3167 / 2427 / 3922 |

**Against the analytical model** (`configs/hardware/technology.json` read
through `opentallas.roofline.Technology` at N7; stored per macro under
`analytical_model_comparison`), for `ot_rom_8192x266_m8`:

| Quantity | Analytical model | Compiled macro | Ratio |
|---|---:|---:|---:|
| ROM cell / 6T cell | 0.33 (`rom.cell_to_sram_cell_area_ratio`, ROMA) | 0.25 (ASAP7 measured) | — |
| Array efficiency | 0.52 (`rom.array_efficiency`) | 0.871 | — |
| Storage density | 58.4 Mb/mm2 | 149.4 Mb/mm2 | 2.56 |
| Read bandwidth density | 0.28 TB/s per mm2 (anchor: a 28 nm compute-in-ROM macro, scaled by bitcell area) | 2.96 TB/s per mm2 (33 B per 770 ps) | 10.5 |

**The disagreements, reported rather than resolved.**

1. **Density, 2.56×.** Three factors contribute:
   - the smaller measured ROM cell ratio: 0.25 against 0.33;
   - the ASAP7 6T cell being smaller than the N7 cell the model uses;
   - a periphery efficiency of 0.87 against the model's 0.52.

   The 0.87 is the macro-internal efficiency. With a synthesised
   standard-cell periphery routed around it, the IHP measurement gave
   0.12–0.31 (`results/spice/ihp_sg13g2_rom_macro/REPORT.md`). The compiled
   number assumes a custom periphery pitched to the array, as a production
   ROM compiler would draw it. Neither the constant nor the macro settles
   which boundary a real die sits on.
2. **Bandwidth, about 10×.** The model's anchor is a compute-in-memory macro
   whose rate is bounded by its MAC arithmetic, not by its array. The
   compiler reports the raw sweep rate: one 266-bit word per cycle at
   1.3 GHz. The model is therefore conservative on ROM read bandwidth for a
   plain sweep. This does not show that the datapath behind the ROM can
   consume it.

## 3. Memory BIST

`rtl/dft/ot_mbist_ctrl.sv` is **one shared controller** for N SRAM collars and
M ROM collars. A macro is selected by `t_sel` / `rom_sel`, and one macro is
tested at a time.

- **Programmable algorithm.** There are eight 16-bit march-element
  registers. Each holds enable, direction, 1–4 operations, and each operation
  as r0/r1/w0/w1 relative to the data background. A background mask selects
  solid, checkerboard, row stripe and column stripe; the collar computes the
  background from *physical* row and column. The reset default is **March
  C-**: ⇕(w0); ⇑(r0,w1); ⇑(r1,w0); ⇓(r0,w1); ⇓(r1,w0); ⇕(r0). March C- ends on
  ⇕(r0), so a tested SRAM holds zeros. The simulation models power up to zero
  for exactly that reason.
- **SRAM collar** (`ot_mbist_sram_collar.sv`, 1RW and 1R1W). The functional
  path is a combinational pass-through while the collar is not selected, so
  it adds zero cycles. It compares expected against read data one cycle
  after the read, and reports the failing-bit vector and the physical row. It
  also holds the macro's repair register.
- **ROM collar** (`ot_mbist_rom_collar.sv`). It sweeps every address and
  folds a whole word per clock into the CRC-32 of `ecc.py`, then compares the
  result with the expected signature from the personalisation.
- **Verification.** `tools/rtl_mbist_campaign.py` passes **74 of 74**
  scenarios. One controller tests `ot_sram_1rw_256x64_m4_r2c2`,
  `ot_sram_1r1w_512x128_m4_r2c2` and a personalised `ot_rom_1024x72_m8`.
  Every injected single fault is detected:

| Fault | Detected / injected |
|---|---|
| stuck-at 0 / 1 | 3/3, 2/2 |
| transition up / down | 2/2, 2/2 |
| coupling CFin / CFid / CFst (both transitions, aggressor above and below, same row other word) | 11/11, 10/10, 10/10 |
| address decoder: no row / alias / multi-select | 2/2, 2/2, 2/2 |
| wordline (row) / bitline (column) | 4/4, 4/4 |
| ROM: missing via, extra via, wordline, bitline | signature mismatch in each |

The SECDED decoder (`ot_rom_secded_dec.sv`) equals `ecc.py` on 2,848 vectors
for K = 64 and 36,313 vectors for K = 256. That covers every clean and
single-error codeword of the sampled words and every double error of one
word; single errors are corrected and double errors are flagged.

## 4. Repair

**SRAM.**

- **Spares.** Every macro can carry up to 8 spare rows and 8 spare IO
  columns. The library uses 2 + 2.
- **BIRA** (`ot_mbist_bira.sv`). The online analysis runs during the March:
  - it keeps a failure CAM of E = 6 entries {row, failing-IO mask};
  - a *must-repair column* rule gives a spare column to any column failing
    in more than R rows;
  - a CAM overflow is flagged unrepairable.

  On completion, an exhaustive search over the 2^E row subsets picks the
  allocation that uses the fewest spares. That allocation loads the collar's
  repair register, and the March is re-run to verify it.
- **Fuse map.** The repair register of every collar is one scan chain
  (`rep_shift_en/rep_si/rep_so`). Fuses are read out through it after test,
  and it is loaded from the fuse box at boot. The chain is
  `NSR + NSR·log2(rows) + NSC + NSC·log2(bits)` bits per macro, in that
  order.
- **Verified cases.** These were repaired and re-verified by simulation:
  - 2 spare rows;
  - 2 spare columns, both taken by the must-repair rule;
  - a must-repair row plus a must-repair column;
  - 1 row + 2 columns for sparse cells;
  - 2 rows + 2 columns on the 1R1W macro;
  - repair under random stalls;
  - a faulty spare left unused;
  - four backgrounds;
  - MATS+ loaded through the configuration port.

  Three bad rows, three bad columns, and five scattered cells are reported
  *unrepairable*. After repair every address reads clean through the
  functional port, and the repair registers survive a full rotation of the
  scan chain. The RTL's allocation equals the Python reference on every
  failure stream.
- **Known limit.** The BIRA does not test a spare before allocating it. A
  faulty spare that gets allocated fails verification, and the macro is
  reported unrepairable. One scenario records exactly this.

**ROM: ECC, not spare rows.** A ROM defect is a via defect (one wrong bit),
or a wordline or bitline open or short. A mask-ROM spare row cannot be
programmed after fabrication. ROM "row repair" is therefore a *patch row*:
SRAM or registers loaded at boot from off-die non-volatile storage, with a
per-die image. SECDED needs nothing per die; its check bits are vias in the
same mask.

`tools/mem_compiler/rom_repair_eval.py` computes Poisson die yield for three
capacities: the full Qwen3-8B weights (16.38 GB BF16, 62,491 macros of
8,192 × 266), the same at 4 bits per weight, and one V4.1 die (2.714 GB).
Defect densities are **assumed sweeps**: vias 1e-11 to 1e-7, wordlines 0 to
1e-7, bitlines 1e-7. The repository has no via-defect data. Die yield at a
via defect density of 1e-9:

| Die | Wordline defects | Unprotected | SECDED | 4 patch rows, no ECC | SECDED + 2 patch rows |
|---|---|---:|---:|---:|---:|
| Qwen3-8B BF16 | none | 3e-63 | 0.996 | 0.000 | 0.9998 |
| Qwen3-8B BF16 | 1e-7 per wordline | 6e-66 | 0.002 | 0.000 | 0.9998 |
| V4.1 one die | none | 4e-11 | 0.999 | 0.110 | 1.000 |
| V4.1 one die | 1e-7 per wordline | 2e-11 | 0.346 | 0.110 | 1.000 |

**Recommendation: SECDED on every ROM word, always.**

- **Cost.** (266,256) adds 3.9% check bits. A (72,64) code on narrow
  constants adds 12.5%.
- **Why it suffices for bitlines.** Column interleaving puts a bitline defect
  in at most one bit of each word, and SECDED corrects that.
- **Why spare rows alone fail.** They cannot repair a bitline, which leaves
  the die with no ECC exposed.
- **Where patch rows help.** Add 1–2 patch rows per macro only if wordline
  defects are expected; the table shows that is where SECDED alone breaks.
  They need a per-die NVM image of the replaced rows.

The Qwen memory subsystem below implements SECDED on the read path and counts
corrected and uncorrectable reads. The BIST signature covers the raw
codewords, so every defective via is seen at test even though functional reads
correct it.

## 5. Integration and the hard-macro route

**Qwen decode core** (`rtl/hdc/ot_hdc_memsys.sv`, selected in
`rtl/test/tb_hdc_core.sv` with `+define+OT_HDC_MEMSYS`):

| Memory | Behavioural array it replaces | Macros |
|---|---|---|
| program ROM | 4,096 × 1,024 | 4 × `ot_rom_4096x266_m8`, SECDED |
| constant ROM | 4,096 × 64 | 1 × `ot_rom_4096x72_m8`, SECDED |
| weight ROM | 49,152 × 1,024 (45,056 words used) | 6 × 4 `ot_rom_8192x266_m8`, SECDED |
| KV SRAM | 1,024 × 512, 4 read ports + 1 element write | 4 replicas (one per read port) × 2 `ot_sram_1r1w_1024x256_m2_r2c2`; writes go to every replica |
| vector memory | 4,096 × 32, 7 read + 6 write ports | standard-cell register file (no macro) |

- **Vector memory.** It is not a macro, and the measurement says why.
  Instrumenting the campaign shows up to **7 reads and 4 writes** in one
  cycle, 10 same-element read-during-write cycles per token, and 128
  same-bank write pairs under 4-way banking. No 1R1W or 2RW organisation
  keeps the schedule without stalls. A banked version with stalls exists on
  an unmerged branch (`rtl/hdc/ot_hdc_vmem_banked.sv`).
- **BIST in the wrapper.** One shared `ot_mbist_ctrl` drives 8 SRAM collars
  and 29 ROM collars. The ROM expected signatures are the per-instance CRCs
  that `personalise` wrote to `signatures.hex`. The campaign runs the BIST
  before the token twice (`memory_macros.bist` in the record):
  - **clean:** all 37 macros pass, in 299,219 BIST cycles;
  - **with a stuck-at-1 KV cell and a missing weight-ROM via:** the KV macro
    is reported *repaired* (status `10`) and re-verifies. The weight-ROM tile
    fails its signature (status `11`), so the die would be flagged. Its one
    bad bit is corrected by SECDED on the one functional read of that word.

  In both runs the token (1073), the 32,246 cycles and every logit, vector
  memory and KV comparison are unchanged.
- **Functional identity.** `results/rtl/hdc_decode_campaign_memory_macros.json`
  reproduces the default record's `single_step`, `end_to_end`,
  `scaling_8_groups` and `long_context` field for field: token 1073 at
  32,246 cycles, generated 1073 / 382 / 93, 8 lane groups, and 60-token
  context. It records zero SECDED events on the clean ROMs.
- **Simulator note.** The memory-macro build uses Verilator 5.050. Under the
  4.038 on `PATH`, the SECDED decoders inside this design raised spurious
  *corrected* flags on clean codewords: 1,347 per token, with the data itself
  unchanged. A standalone decoder test does not reproduce it, and 5.050
  counts zero.

**Hard-macro route** (`results/physical_abi3/asap7/mbist_macro_testtop/`):

- **Design.** `ot_mbist_macro_testtop` holds `ot_sram_1rw_256x64_m4_r2c2`
  and `ot_rom_1024x72_m8` as hard macros, their collars, the (72,64) SECDED
  decoder and the shared controller with its BIRA.
- **Flow.** It is routed through the pinned ORFS on ASAP7 with
  `--macro-view`. Both macros are placed from their LEF, and the PDN reaches
  their M4 straps.
- **1.0 ns target.** Detailed route is clean: **0 DRC**, 0 antenna, 0
  slew/cap/fanout violations. Hold is met. Setup is not: **455.6 MHz**,
  WNS −1.19 ns. The limiter is the **BIRA's one-cycle online update**
  (collar failure row → CAM match, per-column counts, must-repair popcount,
  CAM write), about 2.3 ns of logic. The macros are not the limiter.

- **2.4 ns test clock** (`pnr_2p4ns.json`). Setup closes with +0.146 ns of
  slack, hold is met, and DRC is 0. The flow still refuses acceptance for
  **8 max-slew violations**, so this is not a sign-off either.

Two routes to closure. One is to rerun with `--max-transition-ns` and a slew
margin. The other is a two-stage BIRA with an event FIFO and backpressure
into the controller's existing `hold`, which would also let BIST run at the
functional clock. The macros are placed and connected (PDN on their M4
straps, pins reached on M4) in both routes.

## Status per architecture

| Architecture | Memory compilers | Self-test and repair |
|---|---|---|
| **HBM comparator** (core + KV streamer; `results/memory/memory_plan.json` `hbm_comparator`) | Program and constant ROM, KV prefetch window (4 × `ot_sram_1r1w_256x256_m2_r2c2`) and KV tail (2 × `ot_sram_1r1w_128x256_m1_r2c2`) compiled: 11 macros. The flush and write-combine FIFOs and the vector memory are register files. **Open:** there is no HBM weight streamer on main, so its prefetch buffers are not mapped. The HBM3E PHY is external IP with an *assumed* 10 mm2 per stack (`technology.json` `hbm.hbm3e.phy_area_mm2_per_stack`); it has no view here. | The collars and controller apply unchanged to the KV window and tail macros (1R1W). They are **not yet instantiated** in `ot_hdc_kv_stream`. |
| **Qwen3-8B ROM reticle** | Reduced vehicle fully mapped and simulated: 37 macros. Full model at compiled density: 62,491 × `ot_rom_8192x266_m8` for BF16 weights (**1.12 reticles** of macro area, so BF16 Qwen3-8B does not fit one 815 mm2 reticle at ASAP7 density), or 15,623 macros (0.28 reticle) at 4 bits per weight (`full_scale_weight_rom`). | Integrated in `ot_hdc_memsys.sv`: MBIST with repair on the KV SRAM, signature BIST and SECDED on every ROM. Verified inside the decode campaign. |
| **DeepSeek-V4.1 ROM array** | Reduced vehicle mapped: 992 macros, including the 2-read weight ROM as two copies, the quantised ROM, the HC ROM, 384 Engram-table macros (274-bit rows = 264 B + SECDED) and the 5-read constant ROM as five copies. The vector memory (12 reads, 10 writes) is a register file. Full model: about 10,355 weight macros per die (0.185 reticle). **Open:** the ROM views are content-independent by construction, and per-die via maps come from `personalise`. | ROM signature and SECDED apply unchanged. A per-die content signature is produced by `personalise` (`content_signature`, `viamap_set_sha256`). **Not yet instantiated** in `ot_hdc_core_v41`'s test bench. |

The workstream is complete for the Qwen3-8B ROM reticle on the reduced
vehicle. It is not complete for the other two columns:

- the HBM weight streamer's buffers are not mapped, and the collars are not
  inserted into the KV streamer;
- the V4.1 BIST is not instantiated.

## Reproduction

```bash
python3 tools/mem_compiler/asap7.py --calibrate      # only when the ORFS image changes
python3 tools/mem_compiler/build_library.py          # physical/asap7_memory_macros/
python3 tools/mem_compiler/memory_plan.py            # results/memory/memory_plan.json
python3 tools/mem_compiler/rom_repair_eval.py        # results/memory/rom_repair_evaluation.json
python3 tools/rtl_mbist_campaign.py                  # results/rtl/mbist_campaign.json
python3 tools/rtl_hdc_decode_campaign.py             # default memories (bit-exact record)
python3 tools/rtl_hdc_decode_campaign.py --memory-macros
python3 -m pytest tests/test_mem_compiler.py tests/test_mem_compiler_mbist.py
```

## HBM comparator integration

**KV streamer buffers.** `rtl/hdc/kv/ot_hdc_kv_bufs.sv` builds the on-die
buffers of `ot_hdc_kv_stream` from compiled macros. Each macro sits behind an
`ot_mbist_sram_collar`, and one shared `ot_mbist_ctrl` covers all six
(March C-, repair analysis, spare rows and columns, one repair scan chain).

| Buffer | Organisation | Macros |
|---|---|---|
| prefetch window | 4 banks × 256 × 256 bits, shared read address, per-bank write | 4 × `ot_sram_1r1w_256x256_m2_r2c2` (172.8 × 41.0 µm, 2,632 / 2,086 MHz TT / SS) |
| tail (open K tiles) | 2 banks × 128 × 256 bits, 16-bit lane write mask | 2 × `ot_sram_1r1w_128x256_m1_r2c2` (94.8 × 41.0 µm, 2,979 / 2,298 MHz TT / SS) |

The lane mask expands to a bit mask at the collar. The macros' read-before-write
and hold-on-idle behaviour equals the behavioural arrays they replace.
`rtl/test/tb_hdc_core_hbm.sv` selects them with `+define+OT_HDC_KV_MACROS`.
In that mode the core, the streamer and the HBM model stay in reset while the
optional self-test (`+BIST`) runs and the golden tail tiles are written
through the buffers' test port. Every cycle count is therefore measured from
the same reset release as the default build.

`python3 tools/rtl_hdc_kv_stream_campaign.py --memory-macros` builds with
Verilator 5.050 and writes `results/rtl/hdc_kv_stream_campaign_memory_macros.json`.
It re-runs every core run of the default record: single step, long context,
end to end, prompt-60 from empty, the three 2-pseudo-channel runs and the
three fetch-lead runs. Each parsed run must equal the default record's field
for field. It then runs the self-test before the token twice: once clean, and
once with a stuck-at-1 cell in window bank 0. The clean run passes all six
macros in 12,850 BIST cycles. The faulty run reports bank 0 *repaired* (status `10`), and the token
run after it equals the default single step.

**HBM PHY.** `tools/mem_compiler/hbm_phy_gen.py` writes
`physical/asap7_memory_macros/ot_hbm3e_phy/`, a placement and connection
abstract for the licensed PHY and controller:

- **Footprint.** 12.0 mm along the die edge by 0.83 mm deep, which is 10 mm².
  Both numbers come from `configs/hardware/technology.json`:
  `hbm.hbm3e.stack_beachfront_mm` and `phy_area_mm2_per_stack`, and both are
  graded *assumed*.
- **Pins.** 9,209 controller-side signal pins on M5 along the core-facing
  edge. They are the request port and the 32 pseudo-channel response ports of
  `rtl/hdc/kv/ot_hdc_hbm_model.sv`, which is the functional and timing model
  of this macro.
- **Power.** VDD and VSS as M4 straps.
- **Liberty.** Boundary timing only, per corner, graded *assumed*.
- **Package side.** The package side (1,024 DQ per JEDEC JESD238 HBM3, 16
  channels × 2 pseudo-channels, plus CA, clocks and bumps) is not in the
  abstract.

The weight streamer (`rtl/hdc/hbm*`) is not on main yet, so its prefetch
buffers are not mapped.
