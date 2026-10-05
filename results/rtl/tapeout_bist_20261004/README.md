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

Area / 1.2 GHz timing of the BIST logic alone (`ot_v41_mbist_shell.sv`): see `shell_route.json` when present.
