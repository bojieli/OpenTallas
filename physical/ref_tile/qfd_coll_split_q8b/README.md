# qfd_coll_split_q8b -- Q leaf successor of q7 (QKO-COLL 10-21; q8a MAIN / q8b FALLBACK gated in parallel)

q7 verdict (closure qfd_coll_split_q7-q7-96c24d4ce, ot-epyc9): EARLY_FAIL_CONGESTION GRT-0232 after CTS hold repair
(+4075..12104 hold buffers): final M4 overflow 59; q7w (259.2 square, wider E band) gate already FAILED GRT ovf 60.
Classification (congestion-5/10/15.rpt): 100 % of overflow gcells are HORIZONTAL gcells with capacity 0 at x 40-80 and
160-200 = over the two abutted N-S macro stacks. The SRAMs block M1-M4 (LEF OBS), M6 is GRT-shadowed, so a 193-um
abutted stack is a wall with no horizontal crossing. The W/E pin flops are fixed at the face (io_flop_at_pins) and the
pins were clustered on 80/100 um of face (7 pins/um); the R0 W stack also faced its ~1060 SRAM pins (pins on the LEF W
edge) into the W pin strip. => macro channel (none through the stacks) + pin-face clustering; not util (27 % GRT usage).

Structural change (RTL, pins faces, clock, reset unchanged; zero cycles):
- W stack mirrored MY: SRAM pins face the centre fold logic, not the W pin strip.
- each stack cut into groups by two horizontal >= 20 um channels (abutted N-S inside a group: abutted_stack rule).
- each W/E 128-bit bus pinned over 32 um (4 pins/um) centred on its stack channel: the face pin flops cross the stack
  straight through the channel.
- outline enlarged to the 35 % fill floor (no squeeze).

## SAFE-DESIGN checklist
1 Pins: RTL registers every pin (pin_regs opt-out reason unchanged); W/E buses 4 pins/um aligned to channels -- PASS
2 Reach: tile <= 294 um per side; no registered hop > 405 um by construction -- PASS(geom), gate textbook re-checks
3 Fanout: RTL unchanged from q7 (census r4 max 32; gate native_census re-checks) -- PASS
4 Depth: native LAT7 adder 288 ps / 9 levels -- PASS(model)
5 Storage: 12 SRAM macros on the track lattice, std-cell rows in every cut channel and both pin strips -- PASS
6 Floorplan: fill 35 % (macro-bound, WARN), cut channels >= 20 um, pin strips >= 20 um -- WARN fill only
7 Clock: same balanced symmetric spine (OT_SPINE SYM/SAFE_BALANCE/MACRO_LEAF); q7 measured 33.7/34.6 TT/FF -- PASS(prior)
8 Reset/schedule: r4 reset (one face leaf + 2 relays), static schedule, zero added edges -- PASS
Benches: unchanged RTL; q7 bench5b witnesses (gold unit 13 / prod 4 PASS, 6 mutants FAIL incl RERR) carried in job.json.
