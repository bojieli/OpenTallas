# Whole-SU SRAM programme producer

`ot_hbm_su_programme` is an actual host-configured hardware producer at the existing
whole-SU 4 x 2422-bit command boundary. It uses the target SRAM macro functional
model for all programme storage. The testbench's golden image is used only by the
comparator. There is no DPI, DUT readmemh, behavioral DUT programme array, runtime
credit, arbitration, or demand-based issue.

The lowering tool partitions each command into 256-bit columns. Each column has
an independent dictionary of exactly the distinct words appearing in that column.
A fixed-cycle edge-index table contains 16-bit dictionary indices for all columns.
Sixteen indices share a 256-bit SRAM word. Each dictionary has its own physical
read port; no multiported behavioral memory or replicated implicit port is used.
Unused bits in the last column are zero. The exact compiler image is recoverable
without interpreting an instruction or changing its schedule.

Run `python3 tools/hbm_static/su_programme_compile.py PROG_MEM OUT` to produce
`config.mem`, `expected.mem`, `manifest.json`, and a component testbench. Append a
precompiled VM calendar using `--extra-mem CAL_MEM --extra-bits 64`; these bits
appear immediately above bit 9687 and use the same execution epoch. The manifest
pins the original image and lowering/RTL/memory sources and records capacity.
Changing latency or command layout requires regenerating the compiler image.

Use `.EDGES(manifest.edges)`, `.LINE_BITS(manifest.line_bits)`, and
`.DICT_BANKS('{...manifest.dictionary_banks...})`, and `.MACROS(manifest.total_macros)` at elaboration. Capacity is a
physical compile-time property. A different programme can be loaded only if its
column dictionaries and edge table fit that elaborated capacity. Rerunning the
lowerer chooses the required capacities; physical implementation must accommodate
them before deployment.

Before execution, host configuration writes one 256-bit macro word per edge.
`config.mem` is `{bank[15:0], row[7:0], data[255:0]}`; row bit 7 is zero and the
hardware row port is seven bits. Banks first enumerate each index group's SRAMs,
then each column's dictionary SRAMs. Configuration is only accepted while idle.
Unknown bank writes, writes while busy, invalid length, or a start while busy set
a sticky fault until reset. SRAM contents survive reset. Host provisioning must
load all generated transactions before start; simulation power-up zeros are not
an initialization mechanism or silicon guarantee.

Start sampled at edge S launches a deterministic PC. The index SRAM reads line 0
at S+1, dictionary SRAMs read at S+2, and the registered output presents command 0
with `valid` after S+3. A connected sequential consumer samples it at S+4.
`edge_index` counts 0 through `length-1` without gaps. `done` is asserted with the
last presented command; the following edge clears valid and command. Restart is
supported without reloading SRAM. No fault or external signal stretches normal
execution. The compiler/integration epoch must account for these startup edges;
all relative scheduled command cycles remain identical.

The current 7111-edge, 9688-bit image uses 168 index macros and 133 dictionary
macros: 301 x 128 x 256 = 9,863,168 allocated bits, versus 68,891,368 bits in the
uncompressed image. Each execution edge reads three index words and 38 template
words. These are declared logical bandwidth and macro counts, not routed area,
timing, clock, or power measurements. The registered boundary adds four cycles
from start to first downstream sample (0.0563% of 7111 edges if paid once).

`su_programme_run.sh OUT` builds the generated bench, checks every bit on every
edge, checks the startup latency, tail, done timing, and a full replay after
restart. Three negative runs change template data, the first descriptor address,
or the expected schedule phase. Each must fail the exact comparison. Run heavy
build/simulation through ot-run with staged sources and preserve its actual exit.

This component does not establish whole-SU native qualification. Integration must
connect its command output to the actual top, supply real VM/LG service and its
compiled calendars, and pass numerical/memory/relay checks using this producer.
The standalone bench can use external expected programme words. Physical mapping
here means explicit instantiation of target SRAM models; placement, routing,
clock delivery, TT setup, FF hold, and DRC gates remain unproven.

Every macro has a distinct `clk_macro[MACROS-1:0]` input wired directly to that
physical SRAM instance. `clk` drives controller, boundary and bank-select flops.
The manifest records the exact index-group and dictionary-column root mapping.
Benches tie all these ports to one logical clock; physical integration must
provide coherent compensated clocks preserving the declared read-edge timing.
This interface alone does not prove clock tree insertion or skew closure.
