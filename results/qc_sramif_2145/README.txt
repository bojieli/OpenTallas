ROW_WRITE_RELAY structural candidate (default OFF), +0 cycles.
Existing global write-control relay stage is replicated per SRAM row before the existing MIF landing stage.
This removes the measured cross-tap u_twpw -> row u_we family; data/read arithmetic and ports unchanged.
Shared stage becomes dead under ROW_WRITE_RELAY and optimizes away; +24 BTAB/+27 PROG control FF.
Miter tb_row.sv compares MIF1 shared versus MIF1 row relays at the SAME edge against real generated SRAM models.
run_miter.sh expects source.sv=qfd_dv_s5_vm8x.sv and macro128.v/macro256.v from corresponding standard physical/asap7_memory_macros paths.
Nominal: 20000 cycles, 0 btab/prog/fault mismatches, ~19449/18811 nonzero read comparisons.
Mutant: invert PROG low-row local write-enable relay input; 19704 PROG mismatches caught.
Physical NOT RUN. B3 predecessor is FAIL: prog row skew26.5>20, I508.3>~450; btab TT tap window21.4>20.
Viewed predecessor prog_b3_band.png: regular macro rows and face-local data relays, open row channels, shared scalar write stage still cross-tap.
This source candidate does not claim residual macro skew or insertion is solved; actual candidate placement/row clock review required.
