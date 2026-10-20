# qfd_dv_s5_btab (QW-SLICE6 10-19, Q.STA.SLICE.2) -- the station's BTAB copy, beside station region 0

RTL `rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv` module `qfd_dv_s5_btab`: copy 0 of the qfd_dv_vm BF16 table (4 banks x
ot_sram_1r1w_128x256_m1_r2c2, written 4 words an edge by a table write of kind 2) + the 2-edge capture / bank select.
Why it left the VM: the closed stnrgc regions take bt_q through their PIN_IN register and wait BT_LAT 1 extra edge (the
whole budget of the bt_word -> bt_q round trip). Region 0 issues bt_re / bt_word; with the copy inside suvm (r_su,
~1.3 mm away) the loop would cross two landings (+6) and break the closed BT_LAT 1. Beside r0 the loop is local: answer 2
edges after bt_re exactly as qfd_dv_vm (0 added edges); regions 1..7 receive their bt_q slice landed +3 = their own +3
region offset. The SU copy (copy 1) stays in qfd_dv_s5_vm; both copies see the same tw_* writes.
Kits: `qfd_dv_s5_btab` (main, 172.8 x 239.76: one abutted N-S 4-stack, capture channel W, full-width std-cell band S, tw on E) and
`qfd_dv_s5_btabb` (parallel fallback, 267.84 x 172.8: 2 x 2, two abutted stacks with read pins facing a centre capture channel, tw on W, bt_q on S).

SAFE-DESIGN checklist (owner 10-19):
1. Pins: bt_re / bt_word / tw_* go straight into the macros' own input registers (and the t1_bank flop); bt_q = capture
   flop btcap + a 4:1 bank select by flop t2_bank (2 levels). No reset port (pure data path; valids live in the station).
   Waived flow pin registers: one would add an edge to the closed BT_LAT 1 round trip.
2. Reach: PASS -- leaf <= 285 um; parent places it beside station region 0.
3. Fanout: t2_bank selects 256 bits (x4) -- synthesis buffers; bank-select copies may be needed if the gate flags it.
4. Depth: PASS -- capture -> 4:1 mux -> pin.
5. Storage: PASS -- 4 x 128x256 SRAM macros (128 kb); 1 kb capture flops.
6. Floorplan: macros on the lattice (at_exact abutted stacks, pitch 41.088), >= 20 um channels on pin faces, a
   full-width std-cell band; aspect 1.39 (main) / 1.55 (fallback); gate1 FAIL fill 30% (outline too big) -> outlines shrunk to fill ~39% / ~35%, faces pin-bound (fill_reason).
7. Clock: single centre-fed root (~1.0k flops + 4 macro clocks), io_hold_margin 0.03.
8. Schedule: static, 0 added edges.

Gate history: gate2 (single abutted 4-stack, 172.8 x 239.76) FAIL -- trial GRT overflow 6,142 on M4 over the stack (tw data from
the E face must reach the wd_in pins on the macros' W edge: no horizontal capacity across the stack at layer cap M5) and TT
pin-flop spread 83.1 ps. Structural redesign: the 2 x 2 arrangement (two abutted stacks, read pins facing a centre capture
channel, write pins outward) -- qfd_dv_s5_btabb (gate2 WARN: GRT 0, spread 61.6/55.1) is now the MAIN candidate; this kit
qfd_dv_s5_btab is re-cut as its relaxed parallel fallback (280.8 x 194.4, 43.2-um capture channel, bt_q on N).
