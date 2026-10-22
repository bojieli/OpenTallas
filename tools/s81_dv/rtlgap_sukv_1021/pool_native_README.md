# Private pool native structural successors

The original mapped source is preserved. It failed the native limit of 32 with
2,247 violating roots and a maximum of 5,391 loads. The largest root is the
merged lane reset. Other named causes are final-adder and denominator-adder
valid publications, lane score selection, and exponential-table index bits.
The bounded original summary and mapped statistics are in
`results/rtl/s81_rtlgap_codex_2000/pool_native`.

`pool_native_source.py` generates two isolated, complete engineering source
files from the exact existing arithmetic sources. Production files and their
default parameters are unchanged. Each generated manifest pins every input.
These are RTL sources for ordinary synthesis, not mapped-netlist replacements.

Both successors keep sequential owners before optimization. Four independent
controller reset leaves each reset at most 24 control bits. Byte-sized held
payload groups and local mux helpers own enables and selects. Lane and SFU
reset leaves use two levels of individually kept cells. FP payload output
registers are unreset; their valid outputs remain reset. Every arithmetic
operation, rounding point, payload capture edge and issue edge is preserved.
MAIN uses eight-bit exponential-table output groups. The alternate uses
four-bit output groups; both capture their own table index on the original
nint edge and their output on the original table-product edge. The full
256-entry table comes from the original source, including its default zeros.

The deepest control reset path is six common clock edges, versus two lane
reset edges in the predecessor: four extra startup edges. Reset must be held
through six clock edges and commands must start after the release reaches all
leaves. No arithmetic job latency increase is proposed. Compiler and die owners
must price the reset startup before adoption. The current minimal bench waits
128 edges after reset release and does not prove a production reset calendar.

Each admitted job first runs the complete 512-feature L2 pool arithmetic with
256 real pair reads and 64 writes against the existing fixture and FP32
reference. The same executable then swaps actual KV operands as a causal
negative control. Only after both checks does it execute ordinary ORFS synthesis
and the unchanged mapped native census. No maximum-bits increase, fanout
allowance, mapped source override or flow buffer correction is used. Table
partitions are small immutable source case tables and use normal memory mapping.

Reach, clock placement, physical timing and the final native limit remain open.
No physical pool body, slot fit, CN/IK growth or production adoption is claimed
by a source or admitted job alone. Residual mapped violations require another
named source correction and a new immutable run.

The original census input hashes match all 13 inputs of the successor generator
exactly. The original mapped cone map resolves the 1,351-load anonymous OR3
root to the lane pin valid and role registers; its sinks include the score-1
capture flag and maximum-payload flops across lanes. The 760-load final-adder
valid reaches output payload flops across lanes. The 5,391-load reset also
reaches top controller busy and age flops. These are actual mapped endpoints,
not an inferred assignment of anonymous cells to an arithmetic unit. The
source repair prevents the shared owners and moves those payload consumers
into independent helper instances before synthesis.
