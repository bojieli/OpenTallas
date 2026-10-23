# Actual two-slice structural negatives

All three independent NS2 seam builds ran with normal100GB admission and VJOBS1. VAR1 omits the table-request consumer path and fails table contents; VAR2 uses the old unequal request hop and fails the downstream consumer; VAR4 drops the stage bit and fails contents/fault checks. Each actual bench reports TLD_CHAIN FAIL and its admitted wrapper terminates0 after recognizing that failure. The wrapper also emits a harmless grep extra-argument diagnostic; the explicit FAIL lines, summary and actual simulation are preserved rather than relying on wrapper exit alone.

Complete objects remain in their original gold1 lanes codex-tld-neg{1,2,4}-2140-1022. Completed binaries and source receipts were copied into the matching primary ep9 cache directories to avoid rebuilding. This packet proves structural negative detection; full positive/seam suite remains in progress.
