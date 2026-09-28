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
The neighborhood top at `c004b015` also registers ME read requests,
rotation and consumer enables before the store. This exposes the same
`rq_q` producer-to-store hold path that failed the local MP=1 cut and adds
one explicit request fill edge to any finite schedule.
Two clock-related fill cycles from converter and the selected RL5 alignment
remain explicit in the token schedule; one beat/cycle may be credited only
after the neighborhood itself sustains that service.

The route must report preserved macro count and sink-flop count, pin-fit,
clock-tree and skew, extracted setup and hold, max slew/cap/fanout, DRC,
antenna, and macro power-grid connectivity. A digest-only output is not
sufficient evidence that all four consumers survived synthesis. Macro
instances and data paths must remain connected in the final netlist.

Both selected SRAM views expose VDD and VSS power pins in their LEFs. PDN
generation must connect all 48 VM and eight MP=1 store instances and pass a
connectivity check; a completed routing database without macro power
connectivity does not pass. VM has one read and one write port per bank. The
four-word ME preload consumes the four reads together. The GW4 collective
consumes the four writes together during its blocking phase, so these two
operations require no extra macro ports. A concurrent core read or write
must be scheduled or arbitrated explicitly; the scoped wo_a checkpoint
gate does not prove such contention handling.

The MP=1 ME checkpoint gate at `c4591c26` passes all 2,048 wo_a rows
bit-exact at 131,349 cycles for two groups, with 128 four-word preload
issues and 131,108 weight-bank reads. It supplies the bank-major VM words
from its checkpoint fixture. The integrated pipelined VM-to-RL5 exact
first-16 replay at `02c03b8a` also passes 32 rows, checking all 512 VM
words and 128 preload beats. Corrected measurement-window records exclude
134 initialization/reset cycles and report 2,339 timed cycles, 14 more
than the 2,325-cycle standalone RL5 first-16 gate; this finite VM/drain
delta is scoped to that short run. The initial matching MP=1 eight-macro
placement missed setup by **676.67 ps** at 0.92 ns, with the worst path
from `pre_e_r[11]` through preload write selection to SRAM `wd_in[81]`.
The selected bank-local write stage fixes that setup cone functionally.
The pipe2 converter detailed route and this complete neighborhood route
are separate prerequisites. No rate credit follows from this contract.

The selected bank-local write-stage full integration at `70013419` passes
2,048/2,048 rows at 131,363 timed cycles, including 128 VM read issues
and all 512 returned words. Its standalone MP=1 physical cut still fails
CTS hold by 24.932 ps on `rq_q_r[45]` after 7,584 hold buffers, which is
why the registered producer in the neighborhood is required. The full
integration result did not contain that extra producer edge.
