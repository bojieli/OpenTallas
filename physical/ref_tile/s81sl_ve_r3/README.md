# s81sl_ve_r3 -- ot_s81sl_ve r3, SAFE-DESIGN rebuild (S81-SLICE3-VE, 10-19)

Element: the Engram-mix sub-leaf of one DV beat (ot_s81sl_ve, rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv + ve-local FP
units ot_s81sl_ve_fp.sv). History: route s81sl_ve-b571a8c2c NEEDS_RTL (TT -338 tree issue depth, FF -25 shift-line
hold) -> r2 78ad1399f (streaming tree, ring delay lines; gate WARN: util 31 %, one merged reset sync 2,320 loads,
1,230 non-clock roots > 32 loads, Codex native census on the r2 GRT). One failed route = structural rebuild: r3.
Parallel variant: s81sl_ve_r2s (r2 RTL at util 0.50, branch claude/s81-ve-r2s-1019) -- diagnostic, item 3 FAIL.

## SAFE-DESIGN checklist (owner 10-19), r3
| # | item | result |
|---|------|--------|
| 1 | pins registered; reset landed 2 stages | PASS: every input lands in a pin flop, every output is a flop (pin_regs opt-out with reason); kit reset_landing 2 stages, then ot_rst_relay 2 sync + 1 kept relay stage |
| 2 | reach <= 405 um | PASS: 293.76 um square outline; reset relay copies per region (r2 reset reach 532 um) |
| 3 | fanout <= ~32 (kept copies, survive Yosys) | FIXED: 18 kept reset region copies, each <= 26 reset loads, reset ONLY on valid / control state (FP unit results reset-free: ot_s81sl_ve_fp.sv, 4 / 5 reset flops a unit vs 38 / 39); reset valid delay lines removed (unit valid_out chaining, same cycle); ring row selects = one-hot register copies per 8-bit slice (16 loads a bit; r2 wptr 760-870); pack low-quad hold enable 24 kept copies x 16 bits (r2 379); one kept operand register per multiplier decode (mh a/b, mk a/b, mw a, key line; r2 merged decodes 52-78) and one kept gate copy per add lane (r2 264). Copies are (* keep *) wires -> ot_keep_regs.tcl keeps the driving flops in any (incl. $paramod) module; check at the gate: no textbook high_fanout reset WARN, flop count >= RTL copies. WAIVED (reason): cut-register fanout INSIDE the f12 FP datapath (mul select/shift 101-107, add LZ shift 60, mantissa rows ~24-40): arithmetic of the shared, standalone-qualified f12 units, local to one unit; r2 gate reg->reg TT +90 ps |
| 4 | depth <= ~600 ps / ~20 levels | PASS/WAIVED: tree issue encoder gone (r2); worst stage = shared f12 LAT-4 adder k1->k3 602 ps, 15 levels (r2 gate +90 ps TT); LAT 5 would change the 129 / 44 calendars (unpriced), so kept |
| 5 | storage | PASS: no runtime-indexed flop array; D >= 3 lines are rings (rows = plain registers, one-hot AND-OR read), largest ring 832 b < 2 kb |
| 6 | floorplan | PASS: outline from synthesis area (r2 41,013 um2 -> 41,500 estimated) at util 0.50, 293.76^2 (1:1), no macros, one std band; pins W 489 / E 806 on full faces (< 6/um) |
| 7 | clock | single local root beside the register mass (r2: spread 30.5 / 30.9 ps TT / FF); io_hold_margin 0.03; parent matches the boundary by compensation / landing |
| 8 | schedule | PASS: static, no backpressure; reduce first-in -> last partial 129 cyc (GAP 0), add 44 cyc (bench-reported, unchanged); reset release +1 edge (relay stage) = one-time after reset, nothing on the token path |

## Literal outputs (130 TIELO in the r2 native census) -- semantic qualification
- o_y[32l+15:32l] (8 lanes x 16 = 128 bits): the contract's BF16-in-FP32-word encoding (golden y = bf16 in the upper
  half, lower half zero; tools/s81_dv/ve_golden.py y.mem) -- the zero half IS the specified value, not a stub.
- p_hh[31], p_kk[31]: sign of a sum of squares. x*x has sign a^a = 0; the f12 add of two non-negative operands is
  non-negative; every zero result is canonical +0 and overflow returns +0 with err -> fault. Synthesis proved the bit
  constant; the bench compares all 32 bits against the golden.

## Benches (Verilator 5.050 via ot-run, every unreset register powered up RANDOM: --x-initial unique, rand+reset 2)
slve_exact (GAP 0), GAP 1, GAP 2 seed 5, seed 3 PASS bit-exact; MUT 1 (key -> 1.0), MUT 2 (tree association), MUT 3
(slice-1 ring row select one row late) REJECTED. Witnesses: results/rtl/s81_ve_r3_1019/.
