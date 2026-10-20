# qfd_dv_slice_tload (QW-F16PROG4 10-19): slice PRIVATE_CALR table-ROM load path (standalone gate vehicle)

RTL rtl/qwen_dv/qfd_dv_slice_tload.sv (9-bit request face + real qfd_dv_table_rom_loader #(BTAB_COMPACT 1, WE_COPIES 34)
with four ot_rom_4096x266_m8 masks + VM table-write join). In the die it sits inside qfd_dv_slice2 (PRIVATE_CALR=1,
face variants qfd_dv_slice2_{w,e}c); this kit gates its depth/timing standalone (kit pin regs on = the slice's stream
register and VM capture). Fallback (PARALLEL): qfd_dv_slice_tload_b (ROMs 2x2, 388.8 x 259.2).
Bench: results/arch/qwen_calendar_integration_1019/f16_tload (all36 x all4 edge-exact, VM readback, collision, MUT1-5 FAIL).

SAFE-DESIGN CHECKLIST
1 Pins: PASS -- request face register + reset 2 stages in RTL; kit pin regs on every data pin.
2 Reach: PASS -- longest W->E path ~300 um < 405.
3 Fanout: PASS -- join select from 34 kept tw_we copies (32 data bits each + kind + addr), unique-ID kept modules.
4 Depth: OPEN -> this gate (ROM -> capture register; 2:1 join mux).
5 Storage: PASS -- tables in 4 ROM macros (4,358,144 b); flops are pipeline registers only.
6 Floorplan: ROMs on the 43.2 lattice (x 129.6, y 43.2 + 86.4 k); W/E ROM pin faces 4.2/um; 302.4 x 432 (1.4:1); pin/macro-limited util.
7 Clock: single root; spread by --cts gate; io_hold_margin 0.03.
8 Schedule: static exclusive table-write window (no waiter); collision = fault, both writes suppressed;
  prices in tools/qwen_static_schedule/f16_calr_edges.py (first write 5 edges after the face request edge).
