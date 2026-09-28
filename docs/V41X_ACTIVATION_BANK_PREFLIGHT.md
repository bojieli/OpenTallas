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

`ot_hdc_v41x_me_xbank_macro` groups the eight `b=8u+c` banks of one position
and one chain index `c` into one 128-bit SRAM word.  A tile request reads one
row per `(position,c)`; all lanes active on that chain index use that row,
including the 8/16/32/64-element segment cases.  This takes **16 one-read,
one-write macros** for the two-position ME adapter, since both positions
must be read on the same cycle.  The repository's analytical ASAP7
`ot_sram_1r1w_128x256_m1_r2c2` abstract has a bit write mask, so the legacy
four-element write writes one 16-bit slice without reading or rewriting the
other slices.  The 64-element ingress writes one full 128-bit word in each of
eight macros for the selected position.  The macro model checks the same
two groups, wide ingress, and 128,000 two-position segment readbacks.  Its
16 outlines sum to 62,265 µm² and carry 13,104 *internal* signal pins;
these counts are placement inputs, not die-level pins.  Local macro placement
near the MAC lanes and a routed macro-bearing tile remain necessary.

### Die-width replication constraint

The gate above is a 64-MAC `MG=8` slice.  The adopted MTP design-point
ledger (`results/arch/v41_die_assembly.json`) prices **83,328 BF16 MACs per
die** and **3.41 mm² total SRAM**.  Independent copies of this exact two-
position macro store for 83,328/64 = 1,302 slices would occupy about
**81.07 mm² of macro outlines** and provide 25.43 MiB of useful activation
storage.  The die ledger does not include that replication.  This is an
explicit area and routing mismatch, even though a single slice is exact.
An implementable die needs a small number of shared activation banks with
registered, physically local multicast to output-row MAC tiles, or a new
area/power budget.  For scale only, 16 and 32 copies of the current abstract
occupy 1.00 and 1.99 mm² respectively; each would drive roughly 81 or 41
64-MAC slices.  Neither fanout, wire energy, nor timing is validated yet.
The SRAM candidate is therefore a **bank and cluster boundary**, not an
instruction to replicate one bank per 64 MACs.
For the checkpoint-backed `wo_a` groups, output rows in a group share the
same 4,096-element activation and can issue the same `q/plg` schedule in
lockstep, so one SRAM read may feed a registered multicast tree.  That
lockstep and single-read condition is not established for compressor,
router, shared expert, multiple-user, or sparse-expert schedules; those may
require separate banks or a different issue schedule.  Each registered
multicast stage adds a fill/tail cycle and its weight-data path must be
delayed by the same amount before an exact arithmetic claim.

`ot_hdc_v41x_he_xslice` is a local 128-bit by 80-word SRAM slice for eight
HCP lanes at the design HW=256 and PMAX=8.  A full HCP has 32 slices in each
of eight term banks, or 256 slices and 320 KiB of BF16 activation storage.
The read is one registered cycle and retains HCP ML=2.  The slices must be
placed next to the associated eight MAC lanes: exposing the entire
32,768-bit operand as a single die-level port recreates the pin/routing
problem.  HW=8 uses a different, deeper image and remains the first
full-shape numerical profile until an HW=256 weight-bank image is generated.

`ot_hdc_v41x_he_xslice_macro` maps one such slice to one analytical 128x256
SRAM abstract, with bit-masked legacy writes and full-word preload.  Its
80-word real-data preload and 640 readbacks pass the macro simulation model.
At HW=256 and PMAX=8 the 256 slices would occupy about 0.996 mm² of these
macro outlines, before wiring and whitespace.  This is a floorplan estimate
for local memories, not a routed HCP or measured SRAM area.

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
the HCP command.  A stand-alone 128-bit whole-word HE slice variant passes a
real-data readback.  With four 512-bit VM words/cycle (64 FP32 elements, eight
chunks), each of the eight HCP term banks can write one local eight-lane slice
per cycle: 2,560 chunks take 320 issue cycles.  Eight VM words/cycle can write
two distinct slices per term bank and take 160 cycles.  Neither VM path is
integrated, and a whole-word write is required by the local SRAM macro.

## Gates and claim limits

`tools/rtl_v41x_activation_bank_campaign.py` checks the 64-bank ME memory and
the 128-bit HE slice with BF16 data from the source-pinned 200K layer-0
golden shard.  It checks both ME groups, all 8,192 BF16 readbacks, the exact
2,048-cycle four-port LOAD count, the 128-cycle proposed wide preload,
skewed per-chain tile requests, and 8,000 HE slice readbacks.  The HE
whole-word variant separately checks an 80-cycle preload and 640 readbacks.
These are memory-order and one-cycle read gates.  They do
not exercise the ME/HCP arithmetic, whole layer, or multi-die execution.

ASAP7 representative slice routes are run as **standard-cell memory**
characterisations.  Their area and timing cannot be extrapolated to a
foundry SRAM macro or to the full lane array.  The repository does have an
analytical 128x256 SRAM LEF/liberty/Verilog view, now used by the grouped ME
prototype; it has not been routed inside the ME tile.  The HCP slice now has
a local macro-backed simulation model, but still needs integration with the
full HCP and physical closure.  Before placement, synthesis
maps the 16x80 ME slice to 6,933 cells,
861.9 µm² and -462 ps setup slack at 0.92 ns.  The 128x80 HE slice maps to
6,960 µm² with -9,546 ps setup slack.  These negative standard-cell results
are physical evidence that an SRAM macro is necessary.  The 16x80
standard-cell ME slice subsequently routed with no DRC or antenna violation;
its routed Fmax is 1,633 MHz, but the combined run remains `NOT_MET` because
the separate pre-route static-timing stage reports -462 ps at 0.92 ns.
This tiny surrogate is not the complete ME tile or the grouped SRAM boundary.
The larger 128x80 HE standard-cell route remains in progress.
