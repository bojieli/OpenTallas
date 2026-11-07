# DIE-HBM-82-RF 11-06 RX bm3_rest no-macro forms: lock-step bench
HBM-GAPS-8 run_bm3.sh (gold ot_pdie_serdes__fs + declared shift; tb_bm3.sv / ot_pdie_serdes__bm3fs.sv from epyc5 /srv/opentallas-scratch3/claude/hbm-gaps-8/rxsp), 9000 edges.
- sr = OT_RXBM3_FLOPDLY: ft1/fd7 and ft2/fd2 PASS
- fc = OT_RXBM3_SRAM_SPLIT+OT_RXBM3_FLOPC: ft1/fd7 and ft2/fd2 PASS
- mutA (word delay DD-1 stages): FAIL at cycle 110 (caught); mutC (cw delay DC-1): FAIL at 110 (caught)
Note: the SR forms equal the pointer-SRAM forms cycle-exactly once 63 cycles have passed since reset; they differ only in pre-lock stale words, which cannot reach any port (outputs gated by os/fs).
