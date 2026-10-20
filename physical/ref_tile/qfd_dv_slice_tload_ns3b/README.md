# qfd_dv_slice_tload_ns3b (QW-TLOAD2 10-19, TOK.QW.BENCH.1.STORE)

Structural successor of tload ns/ns2 (gates FAIL: clock_rule TT/FF pin-flop spread 107.2/95.4 and 91.4/81.7 ps, ck on W
mid-height over N/S pin-bound faces; macro->reg -229/-218 ps ROM->validation). RTL qfd_dv_slice_tload CAPTURE_STAGE=1
(a775ac6d8, QW-PARENT-PICKUP3): ROM payload + metadata captured before 4 kept, independent validation groups; six local reset
leaves. Outline 388.8x259.2; ROM rows 43.2/172.8 (66.6 um centre channel holds the capture/validation register mass + spine). Parallel pair: qfd_dv_slice_tload_ns3 (388.8x216) / _ns3b (388.8x259.2).

SAFE-DESIGN checklist:
1 Pins: PASS -- pin_regs on (keep_pin_regs), RTL request face reg; reset_landing 2 stages; local reset leaves +1 cold release edge.
2 Reach: PASS (gate measures) -- W->E data path crosses 388.8 um < 405; stream W / joined out E aligned full-face ranges.
3 Fanout: PASS -- 4 uniqueparamod metadata groups x 8-9 kept enable copies, <=32 data bits per copy (WE_COPIES 34 kept selects).
4 Depth: fixed -- ROM capture register before validation removes the ROM->validation chain (ns: -229 ps); gate path_classes.
5 Storage: PASS -- 4 real 4096x266 ROM macros; new registers are fixed pipeline captures, not indexed storage.
6 Floorplan: PASS -- 2x2 ROM block on the 43.2 lattice, >=20 um channels + 5.4 um halo; s_data/tw_data 1024 b over 240.8 um = 4.25 pins/um (<=6); aspect 1.8/1.5;
  fill ~33-39% is pin-bound (2,211 signal pins on W/E), not area-bound (fill_reason).
7 Clock: fixed -- centre-fed spine (OT_SPINE_PORT ck, N face centre x~194) through the inter-row channel beside the register
  mass, one coherent root (~4.5k sinks); TT+FF pin-flop spread <=80 is the gate check; io_hold_margin 0.03.
8 Schedule: static, no credits/backpressure. Priced: +1 edge on first write/last write/done/busy-drain (first_age 5->6,
  88 slots), +1 cold reset-release edge; compiler table_write_window capture_stage=True (QW-GEN3 NOTICE).

Benches (job.json): rtl/test/qwen_dv/run_f16_tload_capture.sh -- fixture rebuilt from the committed compact manifest
(c63242, programme_store.py + table_rom_native_fixture.py); pass = default0 first_age5 + capture1 all36 x all4 12,672 edge-exact
slots + 149,640 VM readbacks + collision reject; mutants MUT1-5 + CAPTURE_MUT1/2 fail with committed 5.050 witnesses
(bench_witness/).
