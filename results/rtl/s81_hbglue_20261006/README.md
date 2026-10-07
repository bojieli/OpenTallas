# Native S81 head-bundle glue

`ot_dsrom_head_bundle_glue` extracts the unchanged broadcast, systolic lane skew,
B-root demultiplexing and two-stage argmax tree from `ot_dsrom_head_bundle`.
The numerical elements and original bundle are unchanged. The small exact bench
compares native glue cycle by cycle against the original glue with deterministic
traffic stubs at the numerical element boundary. It is not a head numerical test.
The enabled hierarchical configuration passes 1200 cycles / 590 valid results;
demux, tie-rule and skew mutations fail. An unsupported SK=9 configuration fails
elaboration. `USE_HARD_DELAY8=0` remains the default.

The two flat full routes failed FF hold. All failing paths were short lane-skew,
broadcast or result data paths. A 15 ps hold-repair margin successor hit the
flow's maximum buffer count at CTS. These immutable failures accompany the actual
structural successor: 56 paired-lane `ot_s81_head_delay8x32` elements, each 32 bits
wide and eight cycles deep. They replace 14,336 skew flops without adding cycles.
The broadcast, demux and result tree remain in the parent.

The delay element is fully routed at 0.833 ns, SS setup uncertainty 60 ps and FF
hold uncertainty 25 ps: SS setup +327.654 ps, FF hold +1.510 ps; zero DRC,
antenna, slew, capacitance and fanout violations. Its 17.187 x 17.187 um LEF and
actual extracted SS/FF timing models are in
`physical/s81_die_views/hbglue/ot_s81_head_delay8x32/`. The exporter independently
reloaded final ODB/SDC/SPEF and reproduced the reported corner slacks.

This is conditional standalone closure: every external input and output is timed
at 166.6 ps with the runner's 3.898 fF output load. Those values are not a supplied
S81 source/capture contract. The hierarchical parent and die remain unqualified
until their own actual timing checks pass.

The die's `dsfd_hbglue` placeholder has additional transport interfaces absent
from the native numerical bundle: xai/xa 283 bits, xbi/xb 266 bits, cci/cc 15 bits,
si/so 2 bits, ri/ro 66 bits. Payload conversion, row/go decoding, chain advancement
and return arbitration/backpressure must come from the S81 generator owner.
No arbitrary encoding or drop-in replacement is claimed here.
