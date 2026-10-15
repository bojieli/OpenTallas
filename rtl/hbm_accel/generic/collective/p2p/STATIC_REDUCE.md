# Fixed-calendar collective arithmetic component

`ot_hgi_coll_reduce_static` provides real 16-lane binary32 addition with 16
resident vector tags. It has one control clock, 16 state clocks and 16 native
adder clocks. These clocks represent independently delivered phases of one
logical domain. There is no ready signal, credit, queue, or dynamic issue.

The compiler reserves every operation:

- `load_v/load_tag`: sample `in_flit[511:0]` into an empty tag at this edge.
- `add_read/read_tag` at R: register the tagged accumulator and current incoming
  operand. `add_issue` must equal the preceding edge's `add_read`. It uses the
  cached tag, with no separate issue tag or added issue stage. Sixteen real
  `ot_hgi_coll_pring_static_add_lane` units at LAT8 write back at issue + 8.
  The next dependent read is legal at issue + 9, after writeback.
- `pub_read/pub_tag_a/pub_tag_b/pub_bf16/pub_meta/pub_release` at R: register
  the two state vectors and publication metadata. `pub_issue` at R + 1 emits
  registered `out_v/out_flit`. FP32 publication carries A; BF16 publication
  rounds A and B independently to nearest even, packing A into bits 255:0 and
  B into bits 511:256. The high 33 bits are the cached metadata. Release clears
  A at actual publication; BF16 also clears B.
- `in_v` must equal `load_v | add_read`. Simultaneous load and add-read faults.
  The caller owns incoming frame identity checks; this engine uses its payload.
- `clear` discards resident state only with empty pending/read/publication
  pipelines. Sticky faults clear only on reset.

The state leaf contains 16 x 32 accumulator bits and four registered 32-bit
read faces (640 flops). Sixteen independent native LAT8 add leaves have 676
flops each. The control root, including the registered 545-bit output, remains
below 15,000 sinks. The analytical sizing entry is
`hgi_collective_static_reduction_model()` in `tools/uarch_model.py`.

`fault_cause[7:0]` is sticky: bit 0 ingress presence; bit 1 read/issue
reservation; bit 2 missing or pending state; bit 3 resource/read/write conflict;
bit 4 occupied load; bit 5 illegal clear; bit 6 arithmetic valid alignment;
bit 7 unavailable writeback identity. Pending state is inspected before the
edge, so a read at its writeback edge faults. A load/writeback collision writes
the OR of both enabled payloads and faults, avoiding a hidden priority choice.
Invalid schedules still execute fixed commands; discard their results.

`run_reduce_static_bench.sh OUTPUT [normal|tag|bf16]` builds actual native RTL
with Verilator. C `f32add` is used only as the independent DPI golden. The main
vehicle checks 12 groups of 8 ranks, with 16 full 512-bit flits per quarter,
using the exact tree `((0+1)+(2+3))+((4+5)+(6+7))`. It checks every intermediate
publication, 1,344 FP32 vectors, plus a BF16 pair with even/odd rounding ties of
both signs. Negative scenarios cover missing/extra ingress, unavailable reads
and publication, missing issue reservations, occupied tags, read/load and
writeback collisions, pending publication, and illegal clear. Tag-writeback,
BF16 tie, and reduction schedule mutants fail the independent payload check.

This is a behavioral arithmetic component gate. Physical timing, physical
channel capacity, G96 integration, and end-to-end token throughput remain
unqualified. The native FP32 adder's existing nonfinite policy is unchanged;
the arithmetic workload uses finite normal values and cancellation cases.
