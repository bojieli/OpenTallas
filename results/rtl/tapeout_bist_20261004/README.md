# S81 element memory BIST: ROM macros + KV SRAM (2026-10-04)

Vehicle `rtl/dft/v41/ot_v41_elem_mbist_top.sv`: one shared `ot_mbist_ctrl` tests
- the four `ot_rom_4096x274_m8` weight ROMs of one S81 q pair element (NB 2 x ping-pong), through ROM collars
  inserted by the generated successor `rtl/dft/v41/ot_v41_rom_elem_qp_mb_w10.sv`
  (`tools/dft/gen_elem_mbist.py` from the pinned `ot_v41_rom_elem_qp_w10.sv`; the element ICG is held open while
  the BIST runs): full address sweep folded into CRC-32 = `tools/mem_compiler/ecc.py` signature, compared with the
  personalisation's per-macro signature (no ECC: test-time content signature only);
- two KV staging banks `ot_sram_1r1w_256x256_m2_r2c2` (the S81 attention staging / compressed-KV fetch macro)
  through SRAM collars: March C-, BIRA, 2 spare rows + 2 spare columns, repair scan chain.

Bench `rtl/test/tb_v41_elem_mbist.sv`, campaign `tools/dft/elem_mbist_campaign.py` (Verilator 5.050, ot-epyc1tb),
record `record.json`. Verdict **PASS**:

| Check | Result |
|---|---|
| Functional exactness vs the pinned element (2 seeds, ~1.66 M cycles each, every cycle, outputs + walker state), before, DURING and after the BIST | PASS (0 mismatches; 21,545 cycles compared during BIST) |
| Clean BIST | pass, ROM 4/4 signatures match, KV 2/2 pass; **21,545 cycles = 17.95 us at 1.2 GHz** |
| KV banks read back after the (destructive) March | PASS (256 words x 2 banks) |
| ROM defects: missing via, extra via, wordline open, bitline short, decoder no-row / alias / multi-select (one per macro) | 7/7 detected, the faulty macro flagged, others pass |
| KV SRAM single faults: SA0/1, TF up/down, CFin/CFid/CFst, AF none/alias/multi, row, column | 12/12 detected and **repaired** (BIST pass) |
| KV 2 rows + 2 cols | repaired; 3 rows: unrepairable (fail) as expected |
| Mixed ROM + KV fault | ROM macro 1 fail, KV bank 0 repaired |

## 1.2 GHz timing of the BIST logic (`ot_v41_mbist_shell.sv`: controller + 4 ROM collars + 2 SRAM collars)

- With the original `ot_mbist_rom_collar` (bit-serial CRC loop) the routed shell FAILS: SS setup -3,598.8 ps
  (226 MHz), worst path `sig -> sig` through the 274-bit fold; 10,503 um2 (`shell_loopcrc_FAIL/`).
- Successor `rtl/dft/ot_mbist_rom_collar_par.sv` writes the same CRC in matrix form (per-bit parity of constant
  masks). The element campaign re-run with it gives the identical signatures and verdict (`record.json`;
  the loop-form run is `record_loopcrc.json`). Its routed shell (`shell_par/`, generic sign-off recipe, false-path IO):
  **SS setup -515.8 ps (741 MHz), FF hold +10.1 ps -> does NOT close 1.2 GHz.** The ROM collars are no longer
  limiting; the worst path is inside the shared BIRA (`u_bist.u_bira.cm_r -> cm_pop_r`, the repair-analysis
  popcount). Std-cell area 9,728 um2 (74,233 cells) for 1 controller + 4 ROM collars + 2 SRAM collars, i.e. 40% of
  the q element's 24,101 um2 if all of it sat in one element (the controller/BIRA is shared per die in practice).
  Open: pipeline or multicycle the BIRA analysis (it runs between March passes, not at memory speed) and re-route;
  not tuned here (owner rule).
