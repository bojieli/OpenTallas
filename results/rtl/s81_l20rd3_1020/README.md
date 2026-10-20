# S81-L20RD3 (10-20): paired index reader dsdv_idx_rg2 -- gather fail-closed fix, V5.050 receipts

Source: claude/s81-l20rd3-1020 @524d4b586 (rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv; sha256 in receipts/*/build.log).

## Root cause of bench2 gather2048 P3 FAIL (Codex packet 55cfb1dcb)
1. RTL FAIL-OPEN (rg2 and the record dsdv_idx_rg): a gather slot was flagged late only when a COMPLETE buffer held an
   OLDER word, so an OWNED word whose keys had not reached the assembler at its slot was emitted EMPTY with in-band
   fault 0 (seed1 word 104 / seed2 word 10); the following slot then set the sticky fault -> 921 / 1015 errors.
   Fix: a gather slot is certified only when the assembler frontier gfr (items arrive in word order) is past it or the
   reader is drained; an uncertified slot not taken is LATE. MUT 7 = record rule: reproduces 921 / 1015 with nopen 1.
2. Gather at P = 3 is over the reader's internal gather rate, NOT the HBM: with the bench HBM at 2x (CKH 450 ps) gather
   P3 still fails at the identical words (921 / 1015) -> reader-internal bound (pair engine / walker run-ahead), as the
   record reader (P3 FAIL / P4 PASS, S81-IDXRD). Operating point of record stays P3 scan / P4 gather (compiled P).

## Receipts (Verilator 5.050, SRAM_MACRO 1)
- b3 IDXRD_CAMPAIGN PASS: scan P3 small / open6 / L2 43,691 / L20 87,382 (2 seeds, 16,879 hdr->last); gather P4 NB2048
  (3 seeds, 5,813) + NB256 P3; closed_* (gather P3 x2 seeds, T0 700, late scan, late gather) FAIL with nopen 0.
- h450 (HBM 2x) diagnostic: gather P3 / P2 and L20 P2 still FAIL fail-closed (nopen 0).
- Mutants: m1 (lane) / m3 (scale) / m4 (part-1 late) / m6 (om) FAIL; m2 (rk leak) slice_err 2448; m5 (slice rsp) 32;
  m7 (record late rule) closed_* BAD = fail-open witness.
- Native census (native_textbook.json, synth-only recipe results/rtl/s81_l20rd2_1020/native): PASS, 0 refusals,
  hf max <= 32, depth 460.1 ps / 14 levels, 14,507 FF, 45 macro pins.
