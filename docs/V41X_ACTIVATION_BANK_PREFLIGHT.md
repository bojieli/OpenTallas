# V4.1 full-shape ME and HE activation-bank preflight

The adopted full-shape program has a second throughput constraint beyond the
ME and HE multipliers: both adapters copy their input from vector memory into
local activation storage before starting their arithmetic engines.  These
copies are serialized with each adapter's command.  This note states the
observed RTL schedule and a banked storage boundary; it makes no chip-rate
claim.

## Exact one-position LOAD counts

The corrected TP4 `wo_a` program uses two separate, no-`splitj` ME operations
per die.  Each has 1,024 output rows and a 4,096-element BF16 activation
group.  At the current four 32-bit VM read ports, the ME adapter takes
`4096/4 = 1,024` issue cycles per group, or **2,048 per layer** before its
load-drain cycles.  The prior single grouped descriptor issued eight loads,
or 8,192 cycles, and addressed outside the local 8,192-element ACC vector.
The corrected two-op image and its exact computation still need the full-shape
core/emitter gate; the stand-alone bank test exercises the input sequence.

Each hyper-connection projection reads 2,560 chunks of eight FP32 elements,
one chunk per cycle, before issuing the HCP command.  Thus the HE LOAD is
**2,560 cycles per projection** and there are two projections per layer.  The
HCP's modelled 2,048-lane configuration needs only 240 ideal MAC cycles for
24 rows x 20,480 terms.  The current core uses 64 HCP lanes (HW=8), so a
full-shape numerical gate at that setting does not validate the modelled rate.
Actual exposure of either LOAD requires a stage replay because HE mixes and
some ME work can overlap other engines.

## Banked SRAM boundary

`ot_hdc_v41x_me_xbank` stores BF16 elements in 64 independent banks for
MG=8.  Bank `b` holds indices `b + 64*r`.  It has one 16-bit read and write
per bank and position each cycle.  The tile's `rq_q` and `rq_plg` select a
segment, and a shallow segment broadcast maps the 64 bank outputs to the
lanes.  The read takes the same one registered cycle as the adapter's former
`xr[0]`; the tile's RL=2 need not change.  With KMAX=5,120 the depth is 80
words per bank, or 10 KiB per position.  MTP with six positions needs 60 KiB
at this boundary, with each position's banks local to its MAC lanes.

`ot_hdc_v41x_he_xslice` is a local 128-bit by 80-word SRAM slice for eight
HCP lanes at the design HW=256 and PMAX=8.  A full HCP has 32 slices in each
of eight term banks, or 256 slices and 320 KiB of BF16 activation storage.
The read is one registered cycle and retains HCP ML=2.  The slices must be
placed next to the associated eight MAC lanes: exposing the entire
32,768-bit operand as a single die-level port recreates the pin/routing
problem.  HW=8 uses a different, deeper image and remains the first
full-shape numerical profile until an HW=256 weight-bank image is generated.

The two ME `wo_a` groups can be loaded once each through the existing four
VM ports, as the corrected no-`splitj` program does.  The stand-alone xbank
also has a separate 64-element BF16 preload port.  Four 512-bit logical VM
reads per cycle can supply 64 FP32 elements, which round once to BF16 before
the xbank writes one element in each bank.  This loads each 4,096-element
group in 64 cycles, **128 issue cycles per layer**, plus VM and converter
fill/drain.  The four VM banks can return words in physical bank order.  The
xbank stores them in that order and uses a two-bit base-word rotation at its
registered read boundary.  The wide test uses rotation 2, avoiding a full
2,048-bit combinational ingress reorder.  The 64-element VM ingress and BF16
converter are not connected to the core yet.  Changing the adapter's `G`
parameter alone would also
change result-write geometry and is not an implementation of this proposal.
To hide one HE LOAD within a 240-cycle 2,048-lane dot requires at
least eleven eight-element chunks per cycle (88 FP32 VM elements, 352 bytes
per cycle), or a coherent producer-side BF16 shadow buffer populated before
the HCP command.  No such VM path is implemented yet.

## Gates and claim limits

`tools/rtl_v41x_activation_bank_campaign.py` checks the 64-bank ME memory and
the 128-bit HE slice with BF16 data from the source-pinned 200K layer-0
golden shard.  It checks both ME groups, all 8,192 BF16 readbacks, the exact
2,048-cycle four-port LOAD count, the 128-cycle proposed wide preload,
skewed per-chain tile requests, and 8,000
HE slice readbacks.  These are memory-order and one-cycle read gates.  They do
not exercise the ME/HCP arithmetic, whole layer, or multi-die execution.

ASAP7 representative slice routes are run as **standard-cell memory**
characterisations because the currently pinned platform does not provide a
matching 16x80 or 128x80 SRAM macro view.  Their area and timing cannot be
extrapolated to a foundry SRAM macro or to the full lane array.  A macro LEF,
liberty, and pin contract are required before claiming full HCP/ME physical
closure.  Before placement, synthesis maps the 16x80 ME slice to 6,933 cells,
861.9 µm² and -462 ps setup slack at 0.92 ns.  The 128x80 HE slice maps to
6,960 µm² with -9,546 ps setup slack.  These negative standard-cell results
are physical evidence that an SRAM macro is necessary, not a routed clock
claim; routed records will supersede them when the runs finish.
