# V4.1 floorplan resource inventory

The machine-readable input is `results/floorplan/v41_resource_inventory.json`.
It pins source bytes at commit `8f6925ba` and distinguishes executable RTL,
physical macro views, a validated local bank witness, and the analytical die
ledger. These are **not interchangeable inventories**.

## What can be allocated now

The existing die has one core tile, four 32-PC behavioural HBM endpoints,
four per-stack arbiters, one collective engine/DMA, one package controller,
and one three-port router. Full mode selects 30-bit addresses, 21-bit counts,
2048-bit instructions and a four-word collective output. Default lane widths
remain narrow; `FULL_SHAPE` does not instantiate the analytical lane totals.
The selected deployed configuration must override defaults deliberately.

With FULL_SHAPE=1 and other default depths, tile-declared ROM allocations total
179,109,888 bytes and its VM/QE-window SRAM allocations total 2,654,208 bytes.
These omit internal engine stores, queues, packed staging and any port-driven
replication. They are behavioural allocations, **not the 2.714 GB deployed ROM
capacity or complete SRAM bill of materials**. The single behavioural constant
ROM has many simultaneous reads; it cannot be allocated as one single-read macro.

A validated local bank witness uses eight FP8 and eight paired-FP4
`ot_rom_8192x274_m8` views, each 125.712 x 119.340 um. Sixteen macros alone occupy
240,039.52 um2, excluding MACs, selection, registers, spacing and channels. It
provides the tested 8 x 264-bit operand mapping; replication into a die requires
complete tensor placement, not division of total bytes by bit density.

The macro catalog supplies actual view dimensions, capacities and timing.
Dimensions are view geometry, not foundry-qualified silicon claims. The
VM/ME physical owner is checking placement legality, power connectivity and
pin access for the corresponding SRAM views.

## Why the old floorplan cannot certify this implementation

The analytical ledger reserves 805.785 of 815 mm2 (9.215 mm2 left) using
width-scaled logic, assumptions and memory density. It contains eight
collectives, two controllers and four routers; die RTL contains one each.
Its m=2 resource schedule does not equal the default implemented configuration.
Its SRAM figures and nominal ROM capacity need reconciliation with exact banks,
ports and complete integer expert ownership. The current integer owner candidate
has only 4,914,107.7 bytes minimum per-die headroom after spill and is explicitly
not an executable physical placement.

Do not turn the old residual area into a routing-margin claim. Root must bind
one engine profile, every tensor image, macro count and transfer contract to the
same placement. Missing bindings are listed explicitly in the JSON. No
unverified replication count, engine dimension or achieved frequency is invented.

## Functional placement regions

Use the connectivity owner's region IDs: `ROM_MAC`, `VM`, `ATTENTION`,
`HBM_SERVICE`, `INDEX`, `COLLECTIVE`. Place ROM operands beside consumers;
reserve HBM shoreline only with a matching physical endpoint interface. The
interface graph supplies exact widths and cadence. The inventory supplies
counts and memory geometry; neither alone proves fit or token latency.

## Integer ROM-capacity check

Run `python3 tools/v41_floorplan_rom_capacity.py` to regenerate
`results/floorplan/v41_rom_capacity.json`. The adopted mean requirement is
rounded up to **2,714,287,357 bytes**. This is not the worst-stage requirement.

Using only the committed **predictive ASAP7 macro view geometry**, without
process scaling:

| Capacity-only allocation | Integer macro count | Macro area (mm2) |
|---|---:|---:|
| 16384 x 266, all bits available | 4,983 | 141.356 |
| 8192 x 274, all bits available | 9,674 | 145.134 |
| 8192 x 274, 264 useful bits/word | 10,041 | 150.640 |
| 8192 x 274, 272 useful bits/word | 9,746 | 146.214 |
| Repeat observed sixteen-macro/two-matrix occupancy | 13,552 | 203.313 |

The arbitrary-mixture fractional density lower bound is 141.341 mm2. The
first row is an integer homogeneous allocation, not a global integer optimum,
and its macro minimum TT period is 1024.5 ps: it fails the 920 ps target before
wire, capture-register or setup costs. The 8192 x 274 view has minimum period
775.1 ps, but that alone does not close its complete read path.

**ROM capacity alone does not rule out an 815 mm2 envelope in this predictive
library.** This does not establish a usable complete die or even an exact
rectangular bank placement. The witness-repetition row preserves measured
local occupancy but is only a scenario; different matrices, tensor placement,
port demands and expert boundaries may incur different overhead.

The earlier 300.689 mm2 ROM ledger uses an **analytical N5 density model**.
We explicitly do not subtract that figure and insert a predictive ASAP7 macro
area into its total. There is no qualified process conversion or technology
identity justifying that substitution. Likewise, spare bits in the local
witness are not proven ECC; the actual witness has no ECC image generation.
Complete expert binpacking, all tensor formats, bank-selection logic,
registers, interconnect, halos, compute and the other die resources remain
mandatory acceptance gates.
