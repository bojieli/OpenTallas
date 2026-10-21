# Completion FIFO bit slices: bounded validation

Production AW4 and AW2 each pass 5,143 same-cycle data+status checks over three asynchronous reset epochs (3,015 writer / 2,153 reader cycles), with no added cycle. Every slice control output is checked against slice zero. Original ot_link_afifo remains unmodified, and the wrapper keeps 64 distinct instances. A one-bit output rotation mutant fails 5,126 checks. Verilator 5.050 receipts are committed.

Mapped ASAP7 TT Liberty area: 557.61210 -> 2712.57984 (+2154.96774). Cells 4419 -> 20929 (+16510); flops1073 ->4160 (+3087). Storage bits stay1024. These are isolated mapped measurements; integrated clock/layout/census are still owed. The standalone unmodified W1/AW4 native census passes max30; copying source instances into a full tile is not a qualification.

Read pointer fanout is removed by real independent FIFO instances, not buffers, masks or changing the reviewed FIFO. The remaining canonical CDC source proof must resolve per-slice data qualification before an actual kit can be accepted. Full root simulation is unnecessary for this mechanism.
