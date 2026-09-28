# V4.1 VM to ME physical neighborhood gate

This is a prospective physical acceptance contract. It does not claim a
token-rate improvement or die closure. The earlier 2,048-bit top-pin VM cut
missed setup by 1.584 ns at 0.92 ns and remains a separate negative record.

## Source and function

- VM read/write slice: `ot_v41_vm_bank4_macro_pipe` at `e1a679ca`, four
  512-bit bank words per issue cycle, physical bank order, rotation tag.
  The three-group slice is 384 KiB in 48 analytic 512×128 1R1W macros.
  Functional latency is four cycles from read issue to `rd_out_v`; one
  four-word beat per cycle is accepted after fill.
- Conversion: `ot_hdc_v41x_fp32_bf16_preload64_pipe2` at ME source
  `5f11f91a`, 2,048-bit FP32 input and 1,024-bit BF16 output, two register
  stages, one beat per cycle. Input is the bank-major four-word payload;
  logical ACC base 74,272 has rotation 2.
- Shared activation store: `ot_hdc_v41x_me_xbank_macro_inreg_readreg` at ME
  source `5f11f91a`, with **MP=1** for the exact wo_a checkpoint gate:
  eight analytic 128×256 1R1W macros, one 1,024-bit preload write and one
  1,024-bit selected operand read per cycle. Its RL5 adapter adds one
  registered multicast stage and one local alignment stage. The earlier
  16-macro, 2,048-bit MP=2 physical cut is a separate two-position candidate;
  the checkpoint test has not proved position 1.
- Representative local multicast: four observable 1,024-bit registered
  consumers placed around one shared MP=1 store. Synthesis must retain all
  4,096 sink data flops and the four full-width payload paths. This gate says
  nothing about a 41-consumer cluster until composed and routed.

## Floorplan and timing boundary

The first neighborhood must place the VM producer registers adjacent to
the four VM banks, the converter between VM and store, the eight MP=1 store macros
as a cluster, and the four consumer registers around that cluster. A
1,100×1,100 µm pilot die is an upper-bound envelope, not a priced die area.
The 48 VM macros occupy 0.248191 mm² and eight store macros occupy 0.031133
mm² before halos, cells, clock and power. The complete 2 MiB VM would use
256 VM macros and 1.323687 mm² of macro outline, so a 48-macro route must
not be called full-capacity closure.

All local register-to-register paths, SRAM data and address arcs, setup and
hold are timed at 0.92 ns. Only primary I/O timing is false-pathed; all
high-width service paths remain internal. External pins supply stimulus and
observe full-width registered sinks, but are not interpreted as a die/package
wire. The previous isolated min/max arrival assumption of 0.35/0.50 ns is
superseded by actual registered producer-to-consumer placement in this gate.
Two clock-related fill cycles from converter and the selected RL5 alignment
remain explicit in the token schedule; one beat/cycle may be credited only
after the neighborhood itself sustains that service.

The route must report preserved macro count and sink-flop count, pin-fit,
clock-tree and skew, extracted setup and hold, max slew/cap/fanout, DRC,
antenna, and macro power-grid connectivity. A digest-only output is not
sufficient evidence that all four consumers survived synthesis. Macro
instances and data paths must remain connected in the final netlist.

The ME checkpoint gate at `5f11f91a` is a source-pinned first-16 RL5 pass;
full 2,048-row replay and the integrated pipelined VM-to-RL5 exact replay
are separate functional prerequisites. No rate credit follows from this
contract alone.
