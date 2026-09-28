# Four-bank VM macro read service

[`ot_v41_vm_bank4_macro.sv`](../rtl/chip/ot_v41_vm_bank4_macro.sv) is an
independent full-width 1R1W memory module for the V4.1 activation preload.
It is not yet wired into the tile or die. With `DEPTH_GROUPS=16`, it has
four physical 512-bit banks. Each bank uses 16 depth groups of four
512×128 ASAP7 analytic SRAM macros, for 256 macros and 2 MiB of logical VM.
Each bank offers one 512-bit read and one 512-bit write per cycle. A four-word
read occupies all four read ports; GW4 writes occupy all four write ports.
Simultaneous same-word read/write raises `rw_collision_fault` and receives no
defined overlap credit in the performance model.

The read interface takes `rd_v` and a 15-bit **logical 512-bit word** base.
It fetches `base..base+3` in one issue cycle and returns four 512-bit words
in **physical bank order** after two registered cycles, with one beat/cycle
steady-state issue. `rd_out_rot=base[1:0]` tags the position of the first
logical word among the four bank outputs. For bank `b`, the requested logical
word is `base + ((b-base[1:0]) mod 4)`. Its row is that word address divided
by four, so the final banks carry into the next row when the base is rotated.
The macro read happens on one edge; a registered depth-group mux produces the
bank-order beat on the next edge. The input-registered ME xbank and two-stage
FP32→BF16 converter add their own latency after this interface.

Writes have four bank-fixed lanes, each with its own full logical word
address and 512-bit payload. Address low bits must match the lane number.
Out-of-range reads and writes, wrong-bank writes and same-word read/write are
flagged. The module suppresses invalid macro read and write enables, but the
caller must handle the fault outputs and order phases correctly.

The [`macro gate record`](../results/rtl/v41_vm_bank4_macro.json) pins the
standalone RTL and test. The test uses `DEPTH_GROUPS=3` (384 KiB, 48 macros),
which contains the checkpoint ACC base 74,272 FP32 elements (`word base=4642`,
rotation 2). It checks 24 pipelined four-word reads after writes, all four
bank payloads, rotations 2/3/0, a depth-group boundary, range and bank
faults, and a read/write collision. The full 2 MiB configuration is linted
and structurally parameterized but not yet physically routed or exercised in
the checkpoint operator. The selected ME converter/xbank pipeline and tile
controller must be connected and exact-gated before the 128-cycle preload
service can be credited to token rate.
