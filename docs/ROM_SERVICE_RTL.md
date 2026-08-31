# The ROM read service in RTL

**Checklist item:** W8.5
**Status:** the read path from a deployment-named ROM object through bank and
region addressing, repair translation, region masking and the sense interface to
the operand bus is implemented and correlated on two simulators. **There is no
ROM array in it.**
**Evidence class:** `public_open_tool_rtl_simulation` (functional), plus a
separate open-PDK physical view that carries its own boundary
**Product scope:** the Qwen chip sets replay an **executed** read stream; the
DeepSeek wafer set is **derived from the compiled plan**. Whether the wafer
deployment's program runs in the ABI 3.0 sequencer RTL is a separate question
about a separate block, answered by `correlated_cases` in
`results/rtl/abi3_deployment_campaign.json` — see §4
**Primary artifacts:**
`results/rtl/rom_service_campaign.json`,
`results/rtl/rom_service_physical.json`,
`testdata/compiler/rom_service/*/rom_service_vectors.json`

---

## 1. What this block is, and the one sentence that bounds it

Weights read from an immutable array rather than fetched from DRAM is the whole
architectural difference this program is arguing about. `ot_rom_read_service`
is the block that turns a deployment's *name* for a weight into a physical
access:

> given `(object_id, byte_offset, byte_length)` — which placement resource,
> which row inside it, which sense granule of that row, in what order, and is
> this read allowed to happen at all?

**It contains no ROM array.** The array sits behind a sense request/response
interface and is supplied by whatever the block is integrated with — in the
campaign a behavioural window of authenticated checkpoint bytes, in a product a
foundry macro. So this establishes addressing, ordering, masking, repair
translation and operand alignment. It establishes **nothing** about ROM cell
area, read energy, sense margin, wordline or bitline delay, retention or defect
rate. A read path without a real macro behind it is a control claim, and those
two are constantly confused in work like this.

The sense granule width (`ROM_SENSE_BYTES = 64`) is a **declared parameter of
this block**, not a macro property read out of any collateral in this
repository. Row activations and sense accesses are therefore *counted* here and
never converted into an energy. The row buffer is one open row for the whole
array rather than one per bank, which is exact for ascending reads with one
outstanding sense access and an upper bound for a pattern that alternates
between placement resources — worth saying because activations are the one
quantity here an energy model could reach for.

## 2. Where every table comes from

Nothing in the vector sets is hand written. Each table is read back out of a
real ABI 3.0 ROM deployment built by `compiler/backends/rom`:

| Table | Producer | What it decides |
|---|---|---|
| object | `MEMORY_OBJECT` descriptors with `storage_class = ROM`, joined to `notes.rom_plan.regions` | which region an object belongs to, its byte offset inside it, its size, and which shard-table entries that region owns |
| shard | `RomShard` records in `notes.rom_plan.regions[].shards` | the placement resource `(node, reticle, tile, bank)`, the region byte offset the shard starts at, its length, and its address inside the resource |
| repair | `notes.rom_plan.repair_map.entries` | which logical row is served by which spare |
| region mask | runtime health input | which regions are masked off, one bit per region |
| quarantine list | runtime health input | which placement resources are withdrawn. It is a short comparator list rather than a bit per resource: a wafer plan has 9,300 of them and a flip-flop each would be nine thousand flops in a read path to record a handful of withdrawn tiles |

The generator (`tools/build_rom_service_vectors.py`) cross-checks each value
against the other place it appears rather than trusting it once — a region's
base address against its first shard, an object's descriptor base address
against its offset inside its region, every shard coordinate against the repair
map's bank inventory, and every region's shard list against the requirement that
it tile the region without gap or overlap. It refuses rather than repairs.

## 3. What the correlation compares

Two independently written checkers replay the same images through the same RTL:
`rtl/test/tb_rom_service.sv` under Icarus and
`rtl/test/rom_service_harness.cpp` under Verilator, with different
back-pressure patterns on the operand bus and the sense port. Neither reads the
other's code. Per request they require exact agreement on:

- completion status: served, **masked**, or **refused**;
- refusal class: unplaced ROM object, out of range, shard gap, quarantined
  resource, activated column repair, zero length;
- sense-beat count and served-byte count;
- row-activation count, against a row buffer that persists across requests;
- the first and last beat record — placement resource, resource address, region
  byte offset, physical row *after* repair translation, sense granule, byte
  count and the activation bit;
- a 64-bit order-sensitive digest over **every** beat record of the request,
  which is how a hundred-megabyte read is compared without publishing its beat
  stream;
- a 64-bit digest over the operand-bus payload after the column mux.

Across the run they require the service's own counters to reconcile with the
sum of the per-request results, the array's independently kept activation and
sense counts to match, and the bytes and beats that actually crossed the operand
bus — counted by an observer in the testbench top, not by the service — to agree
as well.

The beat digest is a 64-bit Galois LFSR. It is linear, so it is a correlation
aid and not a cryptographic binding; the exact counts and the exact first and
last beat are checked beside it, and single-granule probe requests are checked
beat-exact by construction.

## 4. The three vector sets, and what each one is evidence of

### `qwen_chip` — an executed read stream

The Qwen ROM deployment is executed on `runtime.sim.device.Device` and **every
ROM-class read the engines perform** is recorded together with the byte range it
covers. Both accounting sites in the functional device are instrumented —
`runtime.sim.engine.EngineContext._account_read` and
`runtime.sim.engines.tensor._account_read` — and the recorded total is checked
against the device's own `rom.bytes_read` counter afterwards. A mismatch means a
third site exists, and the generator refuses rather than publishing a short
stream.

### `qwen_chip_degraded` — a repaired, masked and quarantined chip

The same deployment recompiled against a BIST defect list, so the repair map is
produced by the real planner (`plan_repair_map`) rather than written by hand,
plus a masked region and a quarantined placement resource applied as runtime
health inputs. This is where row redundancy, the masked-region path and the
fail-closed quarantine path are exercised on real reads.

Quarantine has to be a runtime input rather than a compiled one, because
`plan_rom_image` refuses to place a region on a quarantined resource at all —
so a deployment with a quarantined resource in its own plan cannot be built.

### `deepseek_wafer` — derived, not executed, and labelled so

The DeepSeek wafer lane had produced no tokens when this set was built
(checklist W6.4), so there is no executed read stream to record. It has since
produced one validated token from a 32-token prefix, filed raw and ungraded
under `results/abi3/accelerator_tokens/`; that is a single forward pass on the
golden model, not a recorded ROM read stream, and it does not change what this
set is. Its requests come from the compiled plan's own
read unit — a region *slot* is what one iteration of a compressed loop reads —
and from **every shard boundary the plan declares**, each crossed by one
request. That is derived evidence about addressing, and the artifact says so
rather than letting it read as an executed stream.

It is also the set that exercises what the Qwen chip cannot: **88** of its **228** regions are distributed across more than one placement resource, one across **1,281** of them, so the shard walk is the thing being tested rather than a degenerate single-entry lookup. <!-- figure: 88 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.distributed_region_count" name="DeepSeek wafer distributed regions, ROM service" --> <!-- figure: 228 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.region_count" name="DeepSeek wafer regions, ROM service" --> <!-- figure: 1,281 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.max_shards_in_one_region" name="DeepSeek wafer largest region shard count, ROM service" -->
**9,172** of the plan's **9,300** placement resources are entered by a served read; the 128 that are not are the 127 owned only by the deliberately masked expert bank plus the one deliberately quarantined tile, and that is checked arithmetically rather than asserted. <!-- figure: 9,172 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.totals.placement_resources_entered" name="DeepSeek wafer resources entered, ROM service" --> <!-- figure: 9,300 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.resource_count" name="DeepSeek wafer placement resources, ROM service" -->

**A second reason this set is not evidence that the wafer product runs.** It was
already derived rather than executed because that lane had produced no tokens
when it was built. Since `results/rtl/abi3_deployment_campaign.json` (checklist
W8.8) there is a second, sharper statement available, about a different block:
whether the ABI 3.0 microsequencer executes the wafer deployment's *program* at
all. That campaign's `correlated_cases` field is the authority on which shipped
deployments the sequencer RTL reproduces; as recorded at commit `518260f` it
named the two Qwen3-8B builds and not this one, which the RTL trapped after
eight retirements on a bound (`A3_STATE_SLOTS`) that nothing expressed at
admission.

Nothing in this document is retracted by that — the addressing evidence in this
set stands exactly as described, and it is about a different block. What it
forbids is the inference a reader would otherwise be entitled to make: that a
wafer part this service can address is a wafer part the rest of the RTL could
drive. Read the deployment campaign's own field for the current answer rather
than a copy of it here.

## 5. What is deliberately not implemented

- **Column redundancy is refused, not implemented.** A read reaching a resource
  with an activated column repair fails closed with its own class. A column
  redirect changes which physical bit lines are sensed and this block does not
  do it; refusing is the honest option and it cannot be mistaken for support.
- **The view-to-byte-range walk is not here.** Requests arrive as contiguous
  byte ranges. Deriving those ranges from a resolved tensor view belongs to the
  operand fetcher; the campaign derives them from the views the functional
  device actually resolved, and reports any read it could not express as
  contiguous ranges rather than dropping it silently.
- **No descriptor CRC, program header or admission check.** The tables arrive
  over the configuration channel already admitted.
- **Whole-decode-step replay.** A Qwen decode step reads about fifteen gigabytes
  and no open-tool simulator will replay that beat by beat. Each set replays
  real requests up to a published beat budget and covers the rest of the address
  space with single-granule probes at every object, region, row and placement
  resource boundary. Which requests were dropped for budget, and the largest one
  dropped, are published in the vector set.
- **Operand data against real bytes, everywhere.** Only the granules in the
  published window are checked against authenticated checkpoint bytes. Outside
  it the array returns a deterministic function of its own address, so what is
  checked there is conveyance and ordering, not weight content.

## 6. What the campaign found

**ROM-class objects that the ROM region plan does not place.** Both products
declare memory objects with `storage_class = ROM` whose source is a *generated*
table rather than a checkpoint segment — rotary coefficient tables, `arange`
and ring-index tables, scalar constants. They are not in `notes.rom_plan`, they
name no region, and their `MEMORY_OBJECT` descriptor carries
`bank_or_tile = 0xFFFF` with `base_address = 0`.

Their traffic is nevertheless counted as ROM traffic by `rom.bytes_read`, and
their bytes are reported separately from `planned_rom_bytes` in the build report
as *ROM generated*. So a ROM read service driven by the deployment descriptors
cannot address them: there is no bank to select a wordline in. The service
refuses them with `ROM_FAULT_UNPLACED_OBJECT`, and the campaign counts how many
of the real recorded reads that is.

This is a finding about `compiler/backends/rom`, which this track does not own.
It is stated here and reported rather than worked around: an addressing service
that invented a bank for `bank_or_tile = 0xFFFF` would have read a legal wrong
row, which is exactly the failure signature this program keeps finding.

### 6a. Two defects the campaign found in this RTL, and what they say about scale

Both were found by the DeepSeek wafer set and neither was visible on the Qwen
chip set, which is the whole reason the second product exists.

**The binary-search midpoint was computed twice.** The table index was written
as `(lo[IDX_W-1:0] + hi[IDX_W-1:0]) >> 1` while the bound update used
`(lo + hi) >> 1` at full width. The two agree until `lo + hi` reaches the table
depth. A sixteen-object chip plan never gets there; a three-hundred-and-twelve
object wafer plan does, and the search then compared one entry and moved its
bounds as though it had compared another. Legal values, no trap, and a served
read from a legal wrong row. It is now one `mid_next` wire with two consumers,
because the defect existed only because the same quantity was written twice.

**A refused read had already put bytes on the operand bus.** A request crossing
from a healthy placement resource into a quarantined one served the beats it
could before discovering the quarantine. The completion said FAULT, so a careful
consumer would discard — but a consumer cannot tell a partial weight from a
whole one, and the beats had also disturbed the row buffer, which would have
moved the next request's activation count. The service now walks the extent
twice: once to prove every resource it reaches is in service, and only then to
read. The reference implements the same two passes, and the campaign checks it
from outside: the array's own sense count must equal the sum of the per-request
beat counts, so a masked or refused request that touched the array at all would
fail.

## 7. Physical view

`tools/run_rom_service_physical.py` runs the full open flow — yosys through
OpenROAD floorplan, PDN, placement, clock tree, global route and TritonRoute
detailed route — against the exact installed IHP Open PDK v0.3.0 collateral, and
records whether it converged.

IHP SG13G2 is a 130-nm open foundry PDK. Nothing from that run may be scaled to
N6, N5, N7 or N4 by any feature-size, gate-pitch or density ratio;
`docs/OPEN_PDK_SELECTION.md` forbids it and `docs/METHODOLOGY.md` section 9
makes it a rule. No number from it enters the iso-node or roofline comparison.

Two further boundaries specific to this block: the routed design **contains no
ROM array**, so it is the cost of the control that reads a mask ROM and not the
cost of the mask ROM; and its object, shard and repair tables are flip-flops
because that is the only storage this open flow can build, so the area
over-counts them by an amount the run does not establish.

## 8. Reproducing

```bash
# one deployment per vector set (zero copy; no ROM image is written)
python3 tools/build_rom_deployment.py qwen3-8b \
    --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json --output build/abi3/qwen3-8b-rom
python3 tools/build_rom_deployment.py qwen3-8b \
    --ir build/ir-v3/qwen3-8b/kernel_ir.v3.json \
    --defects testdata/compiler/rom_service/qwen_bist_defects.json \
    --output build/abi3/qwen3-8b-rom-degraded
python3 tools/build_rom_deployment.py deepseek-v4-flash \
    --ir build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json \
    --output build/abi3/deepseek-v4-flash-rom

# vectors, then the two-simulator campaign
make rom-service-vectors
make rom-service
make rom-service-physical
```

The executed sets need the authenticated Qwen checkpoint reachable from the
deployment root; without it the generator still runs and publishes an empty
real-byte window rather than pretending otherwise.
