# The ROM read service in RTL

**Checklist item:** W8.5
**Status:** the read path from a deployment-named ROM object through bank and
region addressing, repair translation, region masking, and the sense interface
to the operand bus is implemented and correlated on two simulators. Every
retained simulator case passes and the source-current campaign reports
**`status: pass`**. <!-- figure: "pass" src="results/rtl/rom_service_campaign.json#status" name="ROM service campaign status, report header" -->
This closes the bounded control/addressing correlation described below; W8.5
remains partial because there is no ROM array or macro in the block.
**Evidence class:** `public_open_tool_rtl_simulation` (functional). The
previously recorded open-PDK control view predates the descriptor-bound RTL and
is not source-current evidence for this revision; §7 states that boundary.
**Product scope:** the Qwen chip sets replay an **executed** read stream; the
DeepSeek wafer set is **derived from the compiled plan**. Whether the wafer
deployment's program runs in the ABI 3.0 sequencer RTL is a separate question
about a separate block, answered by `correlated_cases` in
`results/rtl/abi3_deployment_campaign.json` — see §4
**Primary artifacts:**
`results/rtl/rom_service_campaign.json`,
`testdata/compiler/rom_service/*/rom_service_vectors.json`; the historical,
non-source-current `results/rtl/rom_service_physical.json` is discussed only to
prevent its earlier result from being applied to this RTL.

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
| object plan | `notes.rom_plan.regions`, independently paired by descriptor-table index | which region an object belongs to, its byte offset inside it, its size, and which shard-table entries that region owns |
| object descriptor | the exact admitted 128-byte `MEMORY_OBJECT` wire record, plus its external descriptor-table index | whether the ABI header, type/version/lengths, reserved fields, reflected CRC32C, ROM class, read-only immutable permissions and alignment are valid; and the independently declared size, base, node and tile/bank |
| shard | `RomShard` records in `notes.rom_plan.regions[].shards` | the placement resource `(node, reticle, tile, bank)`, the region byte offset the shard starts at, its length, and its address inside the resource |
| repair | `notes.rom_plan.repair_map.entries` | which logical row is served by which spare |
| region mask | runtime health input | which regions are masked off, one bit per region |
| quarantine list | runtime health input | which placement resources are withdrawn. It is a short comparator list rather than a bit per resource: a bitmap costs one flip-flop per placement resource and a wafer plan has 9,300 of them, which is nine thousand flops in a read path to record a single withdrawn tile. The trade runs the other way at chip scale — the Qwen plan places on 14 placement resources, so a bitmap would be 14 bits where the eight-slot list is eight 32-bit comparands and their valid bits — and the list is chosen for the plan that cannot afford the alternative, not because it is always smaller |

The generator (`tools/build_rom_service_vectors.py`) cross-checks each value
against the other place it appears rather than trusting it once — a region's
base address against its first shard, an object's descriptor base address
against its offset inside its region, every shard coordinate against the repair
map's bank inventory, and every region's shard list against the requirement that
it tile the region without gap or overlap. It emits the exact bytes from the
deployment's already-admitted descriptor table, not a Python-prejoined
replacement. The RTL then repeats the boundary independently: it validates the
wire record at configuration and, before any sense request, compares its
base/node/tile-or-bank with the plan entry's first shard. It refuses rather than
repairs.

## 3. What the correlation compares

Two independently written checkers replay the same images through the same RTL:
`rtl/test/tb_rom_service.sv` under Icarus and
`rtl/test/rom_service_harness.cpp` under Verilator, with different
back-pressure patterns on the operand bus and the sense port. Neither reads the
other's code. Per request they require exact agreement on:

- completion status: served, **masked**, or **refused**;
- refusal class: unplaced ROM object, out of range, shard gap, quarantined
  resource, activated column repair, zero length, or descriptor/plan mismatch;
- configuration admission of each exact 128-byte placed-object record: ABI
  header and payload shape, reserved fields, ROM/read-only semantics, declared
  alignment and reflected CRC32C, with the external descriptor-table index and
  size independently matched to the plan entry;
- request-time binding of descriptor base/node/tile-or-bank to the plan's first
  shard, including an explicit valid-CRC wrong-base negative request that must
  complete with zero sense beats;
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

This campaign retains no executed DeepSeek read stream. The governed token lane
does complete one prefill plus three decode transactions from a 32-token
prefix, matching the oracle and HBM on all four generated tokens under
`results/abi3/accelerator_tokens/`; that functional run does not retain a ROM
read stream, so it cannot be substituted for one here. This set is therefore
deliberately rebuilt as plan-derived evidence. Its requests come from the compiled plan's own
read unit — a region *slot* is what one iteration of a compressed loop reads —
and from **every shard boundary the plan declares**, each crossed by one
request. That is derived evidence about addressing, and the artifact says so
rather than letting it read as an executed stream.

It is also the set that exercises what the Qwen chip cannot: **88** of its **228** regions are distributed across more than one placement resource, one across **1,281** of them, so the shard walk is the thing being tested rather than a degenerate single-entry lookup. <!-- figure: 88 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.distributed_region_count" name="DeepSeek wafer distributed regions, ROM service" --> <!-- figure: 228 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.region_count" name="DeepSeek wafer regions, ROM service" --> <!-- figure: 1,281 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.max_shards_in_one_region" name="DeepSeek wafer largest region shard count, ROM service" -->
**9,172** of the plan's **9,300** placement resources are entered by a served read; the 128 that are not are the 127 owned only by the deliberately masked expert bank plus the one deliberately quarantined tile, and that is checked arithmetically rather than asserted. <!-- figure: 9,172 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.totals.placement_resources_entered" name="DeepSeek wafer resources entered, ROM service" --> <!-- figure: 9,300 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.resource_count" name="DeepSeek wafer placement resources, ROM service" -->

**This set is still not evidence that the wafer product runs.** It is derived
rather than executed because no read trace from the successful governed token
lane is retained by this campaign. Separately,
`results/rtl/abi3_deployment_campaign.json` (checklist W8.8) answers a sharper
question about a *different* block: whether the ABI 3.0 microsequencer executes
a shipped deployment's **program**. That campaign's `correlated_cases` field is
the authority on which shipped deployments the sequencer RTL reproduces, and
nothing in this document may be read as adding to it. Its entries are
transcribed exhaustively below:

| # | `correlated_cases` entry |
|---|---|
| 0 | `qwen3-8b-rom-single-chip/prefill` <!-- figure: "qwen3-8b-rom-single-chip/prefill" src="results/rtl/abi3_deployment_campaign.json#correlated_cases[0]" name="deployment co-simulation correlated case 0" --> |
| 1 | `qwen3-8b-rom-single-chip/decode` <!-- figure: "qwen3-8b-rom-single-chip/decode" src="results/rtl/abi3_deployment_campaign.json#correlated_cases[1]" name="deployment co-simulation correlated case 1" --> |
| 2 | `qwen3-8b-hbm-single-chip/prefill` <!-- figure: "qwen3-8b-hbm-single-chip/prefill" src="results/rtl/abi3_deployment_campaign.json#correlated_cases[2]" name="deployment co-simulation correlated case 2" --> |
| 3 | `qwen3-8b-hbm-single-chip/decode` <!-- figure: "qwen3-8b-hbm-single-chip/decode" src="results/rtl/abi3_deployment_campaign.json#correlated_cases[3]" name="deployment co-simulation correlated case 3" --> |
| 4 | `deepseek-v4-flash-rom-wafer/prefill` <!-- figure: "deepseek-v4-flash-rom-wafer/prefill" src="results/rtl/abi3_deployment_campaign.json#correlated_cases[4]" name="deployment co-simulation correlated case 4" --> |
| 5 | `deepseek-v4-flash-rom-wafer/decode` <!-- figure: "deepseek-v4-flash-rom-wafer/decode" src="results/rtl/abi3_deployment_campaign.json#correlated_cases[5]" name="deployment co-simulation correlated case 5" --> |
| 6 | `deepseek-v4-flash-hbm-cluster/prefill` <!-- figure: "deepseek-v4-flash-hbm-cluster/prefill" src="results/rtl/abi3_deployment_campaign.json#correlated_cases[6]" name="deployment co-simulation correlated case 6" --> |
| 7 | `deepseek-v4-flash-hbm-cluster/decode` <!-- figure: "deepseek-v4-flash-hbm-cluster/decode" src="results/rtl/abi3_deployment_campaign.json#correlated_cases[7]" name="deployment co-simulation correlated case 7" --> |

Every listed entry is checked against that artifact index by index on every
prose-figure run, so a named entry cannot silently move or disappear. A newly
appended artifact entry still requires an explicit documentation audit. An
earlier revision
of this document said the wafer deployment was *not* among them, and named the
`A3_STATE_SLOTS` trap that stopped it after eight retirements. That was true
when it was written and false by the time it was read: amendments A22-A24 lifted
the trap and the case now correlates. Nothing refused the stale sentence, which
is why the list is now transcribed in full and pinned by index rather than
paraphrased.

**What entries 4 and 5 do and do not license here.** They say the sequencer RTL
reproduces the wafer deployment's *program*. They say nothing about the ROM
reads in this document: the `deepseek_wafer` vector set is still built from the
compiled plan's read unit and from the shard boundaries the plan declares, not
recorded from an execution, and no part of it becomes `executed` because that
campaign passes. Two blocks, two questions; this document is deliberately unable
to answer the other one, in either direction.

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
- **A bounded descriptor check, not whole-deployment admission.** Each placed
  object's exact `MEMORY_OBJECT` record is checked here, including its CRC and
  the fields that can authorize a ROM read. The block still does not consume a
  descriptor-table envelope, `OPERATOR`, `TENSOR_VIEW`, program header,
  signature, or instruction stream. Resolving a view into the contiguous byte
  range presented on this block's request port remains outside this boundary.
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

### 6b. Two numbers about the same set that are not the same number

The Qwen chip set produces two refusal counts that sit close together, describe
overlapping things, and have already been quoted for one another once. They are
different cuts of the same set of refused requests, and the campaign now
publishes the whole table they are both margins of
(`correlation.vector_sets.<set>.origin_composition`) rather than only the two
margins.

Every one of these is a refusal with fault class 1, `ROM_FAULT_UNPLACED_OBJECT`:

| Count | What it is | Where it comes from |
|---|---|---|
| **114** <!-- figure: 114 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.origin_composition.refusals.classes.unplaced_rom_object.total" name="Qwen chip class-1 refusals, all origins" --> | *every* class-1 refusal in the set, whatever provoked it | the class margin, also published as `totals.fault_classes["1"]` |
| **111** <!-- figure: 111 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.origin_composition.refusals.classes.unplaced_rom_object.by_origin.executed" name="Qwen chip class-1 refusals from the executed stream" --> | only those provoked by a read the functional device actually issued | the executed-origin cell, also published as `totals.refusals_by_origin.executed` |
| **2** <!-- figure: 2 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.origin_composition.refusals.classes.unplaced_rom_object.by_origin.negative_unplaced" name="Qwen chip class-1 refusals from constructed unplaced probes" --> | deliberately constructed `negative_unplaced` probes: a ROM object the plan does not place | the vector generator, not the device |
| **1** <!-- figure: 1 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.origin_composition.refusals.classes.unplaced_rom_object.by_origin.negative_unknown" name="Qwen chip class-1 refusal from the unknown-object probe" --> | the `negative_unknown` probe: object id `0xDEADBEEF`, which is in no table at all | the vector generator, not the device |

111 + 2 + 1 = 114. The `negative_zero` probe is **not** in that sum, and this is
the mistake worth naming, because it is the one an earlier reading made: a
zero-length read is refused with class 6, `ROM_FAULT_ZERO_LENGTH`, not class 1.

| Count | What it is | Where it comes from |
|---|---|---|
| **1** <!-- figure: 1 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.origin_composition.refusals.classes.zero_length.by_origin.negative_zero" name="Qwen chip zero-length refusal" --> | the `negative_zero` probe: a read of length zero, refused with class 6, `ROM_FAULT_ZERO_LENGTH`, and the only class-6 refusal in the set | a different class, and no part of the 114 |

Only the **111** is a statement about the shipped Qwen deployment: it is 111 of the **265** executed reads replayed. <!-- figure: 265 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.origin_composition.requests.origins.executed" name="Qwen executed reads replayed, ROM service doc" -->

That is the finding about `compiler/backends/rom` described above. The 114 is a
property of the *vector set*, three of whose members the generator wrote in
order to prove the refusal path works. Quoting 114 as the executed figure
overstates the finding by three requests that no model ever issued.

The campaign builds that table from the per-request index and then requires the
two published margins to be *its* margins — every class total and every origin
total, and the grand total against `totals.faults`. A disagreement is recorded
in `origin_composition.disagreements` and fails the campaign. That is the thing
that should have refused the confusion the first time and did not exist.

The same treatment is now given to the other two margins a vector set
publishes, because they are the same construction and were equally unchecked:
`totals.masked_by_origin` against the masked completions in the index, and
`requests.by_origin` against the requests in it. That second one matters here
directly — **265** is the denominator this section uses to bound the 111, and
until this revision it was a number no tool had ever compared against the
requests the set actually contains.

### 6c. The configuration boundary needed four fail-closed reasons

Every table in this block is written over one configuration channel that carries
a 32-bit slot index, and every write then indexed its table with that value
**truncated** to the table's address width. A slot index past the end of a table
therefore landed on a legal entry of the same table, and nothing said so.

The quarantine list made this dangerous rather than merely wrong. Quarantine
used to be a bit per placement resource, so an out-of-range index withdrew the
wrong resource — bad, but fail-*closed* for the resource it hit. As a list, the
loader assigns slots by a counter, so an overflow folds onto slot 0 and
**forgets** an already-recorded withdrawal: the read that follows is served from
a tile that was taken out of service. Legal values, no trap, nothing refused,
wrong answer, and the answer is weights from a resource the health input said
not to use.

The block now decides at full width whether the slot exists and **drops** the
write if it does not. The same check covers the two indices an object entry
*carries* rather than is addressed by — its `region_id`, which selects the mask
bit, and its shard range, which bounds the shard search — because those were
truncated in exactly the same way.

One scalar cannot distinguish that capacity error from three other ways a load
must fail. The service therefore latches four sticky reason bits in
`cfg_error_flags`; the legacy scalar `cfg_error` is their OR. After loading the
compiled plan and every real wire descriptor, both checkers require the scalar
and all four bits to be zero. The bench then issues these four isolated rejected
writes:

| Sticky bit | Deliberate write | What accepting it would corrupt |
|---|---|---|
| slot/select | quarantine slot `QUARANTINE_ENTRIES`, one beyond the table, naming resource 0 | slot 0 through index truncation, overwriting an entry where present or otherwise creating a resource-0 withdrawal |
| malformed descriptor | a real `MEMORY_OBJECT` record with only its stored CRC bit flipped | the synthetic object's populated table slot |
| descriptor/plan mismatch | the same valid record and plan entry with a deliberately wrong external descriptor-table ID | the synthetic object's populated table slot |
| malformed plan entry | a zero-byte shard written over populated shard slot 0 | the first real shard |

Both checkers require the final reason vector to be `4'hf`, the scalar to be
one, and the run's marker to be reproduced unchanged. The marker makes every
probe externally load bearing: each rejected write targets data that later
requests use, so accepting any one of them changes a completion instead of
merely setting the expected diagnostic.

The slot/select probe's load-bearing effect was also made to fail directly.
Reinstating the fold in a scratch copy of the RTL — accepting the out-of-range
write and truncating its slot index, which is what the block did before this
revision — and replaying the unchanged images under Icarus makes **all three**
sets fail, each at the first request that reads from placement resource 0 and
each with the same signature, a served read turning into a refusal:

| Set | First failing request | Symptom |
|---|---|---|
| `qwen_chip` | 2 | `status: 2 expected 0` |
| `qwen_chip_degraded` | 2 | `status: 2 expected 0` |
| `deepseek_wafer` | 128 | `status: 2 expected 0` |

Each set's shard table places exactly one shard on resource 0, and every set
reaches it. The slot guard is therefore load bearing on all three and not
decoration. That experiment is a one-off run against a deliberately broken
scratch copy, so it is reported here and not committed as an artifact; what the
committed campaign checks is the zero pre-probe reason vector, the final `4'hf`,
the scalar OR, and the unchanged marker.

### 6d. A 64-bit range check that a 64-bit offset could wrap past

`req_byte_offset` is a 64-bit field the **requester** supplies; the object's
size comes from the compiled plan. The bounds test was
`(r_offset + r_length) > r_size` evaluated at 64 bits, and a 64-bit sum wraps.
An offset within 4 GiB of `2**64` makes that sum small, so the test passes, and
`region_byte` — the same addition again — wraps to the same small value and
lands in the middle of the object. The read is then served normally: beats on
the operand bus, `ROM_STATUS_OK`, a completion no consumer would question, and
weights the request did not ask for. Legal values, no trap, nothing refused,
wrong answer.

The two sides of the comparison were never equivalent here. The reference model
in `tools/build_rom_service_vectors.py` computes `offset + length >
entry.size_bytes` in Python, in arbitrary precision, and never wrapped. It is
the RTL that was inexact, and the fix makes the RTL exact — the comparison is
now carried out at 65 bits — rather than teaching the reference to wrap.

Every vector set now contains one `negative_range_wrap` request at byte offset
`2**64 - 32` with length 64. The mathematical end is `2**64 + 32`, while the
old 64-bit expression produced 32. Both checkers require fault class 2,
`ROM_FAULT_OUT_OF_RANGE`, with zero sense beats and zero operand bytes. Thus the
carry bit that distinguishes the fixed expression from the old one is exercised
once per set, not inferred from ordinary offsets.

### 6e. The old evidence never put a `MEMORY_OBJECT` record into the RTL

The earlier object image was a 256-bit convenience entry assembled in Python by
joining fields from `notes.rom_plan` and the descriptor. The RTL saw only that
already-joined result. It could not independently reject a bad ABI header,
reserved field, CRC, permission, storage or integrity class, alignment, external
descriptor-table ID, or size; more importantly, it could not tell whether the
descriptor and plan independently named the same placement. Passing that image
therefore established the Python join, not admission of the wire record that a
loader would actually supply.

The configuration interface now receives three separate things: the compact
plan entry, its external descriptor-table ID, and the exact 1,024-bit
`MEMORY_OBJECT` record. It checks `TA3D`, type 1, version 1.0, the 128/64-byte
record and payload lengths, header and payload reserved fields, reflected
CRC32C with bytes 48–51 zeroed, ROM plus CRC-and-ECC storage semantics, exact
`READ | IMMUTABLE` permissions, the base against its declared alignment, and
the shipped header ownership/replica fields. The descriptor ID and size must
equal the independently loaded plan entry. The descriptor's base, node and
tile-or-bank are retained separately; before sensing, the first shard must name
the same region, start at region offset zero, contain the object's start, and
agree on base, node and tile-or-bank. Selected shards must remain in that
region.

There is one directed request-time discriminator per set. Synthetic object
`0xfffffffe` copies a real plan entry but shifts the descriptor base by one
declared alignment unit and recomputes a valid CRC. It therefore passes record
format and CRC validation and can fail only when the independently retained
descriptor is bound to the plan's first shard. Both checkers require fault class
7, `ROM_FAULT_DESCRIPTOR_PLAN`, and zero sense beats. The synthetic record is a
negative probe. The Qwen plan retains **16** exact placed-object records. <!-- figure: 16 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.plan.memory_object_wire_records.count" name="Qwen exact MEMORY_OBJECT records" -->
Those records are the bytes admitted from its shipped descriptor table.
The DeepSeek plan likewise retains **312** exact placed-object records. <!-- figure: 312 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.plan.memory_object_wire_records.count" name="DeepSeek exact MEMORY_OBJECT records" -->

This closes the descriptor/plan evidence hole for this block's bounded read
boundary. It is not admission of the whole descriptor table or program: no
table envelope, `OPERATOR`, `TENSOR_VIEW`, signature, instruction, or
view-to-range resolution is consumed here.

### 6f. The campaign is source-current and passes without relaxing provenance

Read the artifact's `status` before anything else in this section: it is
**`pass`**. <!-- figure: "pass" src="results/rtl/rom_service_campaign.json#status" name="ROM service campaign status, RTL report" --> Every retained simulator case passes — three vector sets on
two simulators, each reproducing its set's marker exactly and with the same
non-null semantic-check count in both simulators:

| Set | Requests | Refusals | Checks per simulator |
|---|---:|---:|---:|
| `qwen_chip` | **351** <!-- figure: 351 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.requests.count" name="Qwen nominal ROM requests" --> | **119** <!-- figure: 119 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.totals.faults" name="Qwen nominal ROM refusals" --> | **3,539** <!-- figure: 3,539 src="results/rtl/rom_service_campaign.json#cases[2].checks" name="Qwen nominal Icarus check count" --> |
| `qwen_chip_degraded` | **365** <!-- figure: 365 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.requests.count" name="Qwen degraded ROM requests" --> | **170** <!-- figure: 170 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.totals.faults" name="Qwen degraded ROM refusals" --> | **3,679** <!-- figure: 3,679 src="results/rtl/rom_service_campaign.json#cases[4].checks" name="Qwen degraded Icarus check count" --> |
| `deepseek_wafer` | **10,835** <!-- figure: 10,835 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.requests.count" name="DeepSeek wafer ROM requests" --> | **15** <!-- figure: 15 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.totals.faults" name="DeepSeek wafer ROM refusals" --> | **108,379** <!-- figure: 108,379 src="results/rtl/rom_service_campaign.json#cases[0].checks" name="DeepSeek wafer Icarus check count" --> |

All three campaign-level executed-stream
problem maps are empty: source drift, missing required pins, and input/integrity
problems.

A vector set that replays an **executed** read stream records the SHA-256 of
the complete runtime boundary the functional device was built from,
including admission, decoding, memory, numeric helpers, and every registered
engine. The campaign re-hashes the entire recorded map, requires an irreducible
critical-source minimum, re-hashes the repo-relative capability and workload
inputs, and requires successful deployment admission, a device-verified
**399**-range checkpoint-map identity <!-- figure: 399 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.executed_source.checkpoint_binding.authenticated_range_count" name="Qwen authenticated checkpoint ranges, ROM service" -->, zero device failure, and
**0** ROM read events omitted as inexpressible byte ranges <!-- figure: 0 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.executed_source.events_not_expressible_as_contiguous_ranges" name="Qwen unexpressible ROM reads, ROM service report" --> <!-- figure: 0 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.executed_source.events_not_expressible_as_contiguous_ranges" name="Qwen degraded unexpressible ROM reads, ROM service report" -->. Both Qwen sets were re-executed through
that path against deployment `274e4b…` <!-- figure: "274e4b…" src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.deployment.deployment_sha256" name="Qwen nominal deployment, ROM service report" --> (nominal) or the verified degraded
rebuild `ee47f8…` <!-- figure: "ee47f8…" src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip_degraded.deployment.deployment_sha256" name="Qwen degraded deployment, ROM service report" -->; no recorded hash was edited into agreement.

The ignored deployment bundle is consumed when the vector is generated and is
not a retained campaign input. Its ABI deployment SHA-256 is the durable
content-addressed boundary: it binds the instruction body, descriptor table,
object source map, topology, capability digest, and ROM plan. The campaign
therefore establishes correlation for exactly that named deployment identity;
it does not assert that an arbitrary present or future `build/` directory still
contains the same bundle.

The `deepseek_wafer` set is unaffected: it is derived from the compiled plan and
records no executed source. It is refreshed to deployment `fa9077…` <!-- figure: "fa9077…" src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.deployment.deployment_sha256" name="DeepSeek deployment, ROM service report" --> and keeps a
**0**-byte checkpoint window <!-- figure: 0 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.deepseek_wafer.window.real_bytes" name="DeepSeek authenticated bytes, ROM service report" --> because this plan-only generator did not activate
the DeepSeek checkpoint and therefore did not authenticate its source ranges.

## 7. Physical view

`results/rtl/rom_service_physical.json` is retained as a historical artifact,
not as evidence for the descriptor-bound RTL in this report. It was produced
before the service accepted and validated the 1,024-bit `MEMORY_OBJECT` record,
kept descriptor placement fields separately, exposed reason-coded
configuration failures, and added the request-time binding states. Its recorded
SHA-256 values for both `rtl/rom/ot_rom_pkg.sv` and
`rtl/rom/ot_rom_read_service.sv` no longer match those files. The physical flow
was **not rerun** for this repair.

Consequently, the historical artifact's own `status: pass`, cell count, area,
route, DRC and timing fields describe only its predecessor RTL. They establish
no synthesis, placement, routing, timing, area, or DRC closure for the current
descriptor-bound service and must not be quoted as though they do. There is no
current physical implementation result for this revision.

Even for the predecessor, the routed design contained **no ROM array**. Its
object, shard, repair and quarantine tables were flip-flops because that was the
storage the open flow could build, and the IHP SG13G2 result was a 130-nm
control proxy that could not be scaled to a leading node. Nothing from that
historical result enters the iso-node or roofline comparison. This revision
therefore makes no ROM macro, cell area, read-energy, sense-margin, wordline,
bitline, timing, manufacturability, defect-rate, or yield claim.

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

# vectors, then the two-simulator functional campaign used by this revision
make rom-service-vectors
make rom-service

# and, separately from producing it, check that the recorded artifact is still
# evidence about the tree it sits in
PYTHONPATH=. python3 tools/rtl_rom_service_campaign.py --verify
```

`--verify` runs no simulator. It re-hashes every file the current
`results/rtl/rom_service_campaign.json` names in its own `source_sha256`,
including the executed stream's capability and workload inputs, and fails if
any has moved. That check did not exist until this revision, and the
first thing it found was the artifact committed at `518260f`, which disagreed
with **eleven** of the thirty-nine files it named — including the RTL under test
and both checkers — `rtl/rom/ot_rom_read_service.sv`,
`rtl/test/rom_service_top.sv`, `rtl/test/tb_rom_service.sv`,
`rtl/test/rom_service_harness.cpp`, `tools/build_rom_service_vectors.py`, and
all three vector sets' `rom_service_vectors.json` and `rom_meta.hex`. The only
visible symptom was a check count eight lower than the testbench committed
beside it produced. That eight is the historical gap at `518260f`; the current
counts are recorded directly in the table in §6f and are not reconstructed by
adding later checks to it.

Most campaign tools in this repository write a `source_sha256` block
(`grep -rl source_sha256 tools/`). Two of them read one back —
`tools/rtl_static.py` and `tools/rtl_campaign.py` — and both only *print* the
recorded digests into a Markdown report; neither re-hashes the files to see
whether they still hash that way. So no campaign artifact in this repository
except this one has its recorded provenance checked against the tree it is
committed into, and the same staleness is possible in every one of them. That
is a finding this track reports and does not own; the count of affected
artifacts is not stated here because nothing in this repository computes it.

The executed sets need the authenticated Qwen checkpoint passed explicitly as
`--checkpoint-root`; the Make recipe does so. Without it device activation
fails closed rather than publishing an executed stream whose inputs were not
authenticated. The plan-derived DeepSeek set deliberately omits the root and
therefore publishes a zero-byte real-data window.

The physical command is intentionally absent from this reproduction record.
`make rom-service-physical` was not run for the descriptor-bound repair, and the
older physical JSON is not source-current evidence (§7).

## 9. The boundary, stated once

**What the ROM read service RTL establishes.** For three vector sets built from
real ABI 3.0 ROM deployments, two independently written checkers on two
simulators agree, request by request, on: which placement resource and which
physical row after repair translation each sense granule comes from, in what
order, how many rows are activated, how many bytes reach the operand bus and
after what column alignment, and which reads are refused and with which class.
At configuration, the service validates each placed object's exact 128-byte
`MEMORY_OBJECT` record and binds its external descriptor ID and size to the plan;
at request time it binds the retained descriptor placement to the first shard.
Each set separately exercises a valid-CRC descriptor/plan disagreement and a
64-bit extent whose mathematical end carries into bit 64; both refuse with zero
sense beats.
Across each run the service's own counters, the array's independent activation
and sense counts, and an observer's count of what actually crossed the operand
bus all reconcile. Both simulators print the same marker, derived from a
reference decode written from the compiled ROM region plan and not from the RTL.

**What it does not establish, and cannot.**

- **That the product runs.** This is one block. Whether the ABI 3.0 sequencer
  executes a shipped deployment's program is a different question about a
  different block, and `correlated_cases` in
  `results/rtl/abi3_deployment_campaign.json` is its only authority. Every
  entry §4 transcribes is checked directly against that artifact, and even the
  wafer entries are about that block's execution of a program, not about the
  reads described here.
- **Anything physical about this RTL or a ROM.** The current descriptor-bound
  RTL has no source-current synthesis, placement, route, timing, area or DRC
  result. The retained physical artifact predates it and was not rerun (§7).
  There is also no array in the RTL under test — no ROM macro or cell area, no
  read energy, no sense margin, no wordline or bitline delay, no retention, and
  no defect or yield rate. The sense granule is a declared parameter of this
  block. Row activations are counted and never priced.
- **That the wafer product's reads are these reads.** The `deepseek_wafer` set
  is derived from the compiled plan, not recorded from an execution. Only the
  Qwen chip sets replay reads a functional device actually issued, and of the
  Qwen chip set's class-1 refusals only **111** are a statement about the shipped deployment (§6b). <!-- figure: 111 src="results/rtl/rom_service_campaign.json#correlation.vector_sets.qwen_chip.origin_composition.refusals.classes.unplaced_rom_object.by_origin.executed" name="Qwen executed-origin class-1 refusals, boundary section" -->
- **Whole descriptor-table or program admission, or view/operator
  resolution.** This block validates the one `MEMORY_OBJECT` record associated
  with each configured plan object. It does not consume the descriptor-table
  envelope, `OPERATOR`, `TENSOR_VIEW`, program header, signature, or instruction
  stream, and it does not derive a contiguous request from a view.
- **That the quarantine list is deep enough.** No published set withdraws more
  than one placement resource, so the list-depth refusal is a guard on a bound
  nothing here approaches. What *is* exercised is the service's refusal of four
  distinct malformed configuration writes per run, with reason vector `4'hf`,
  checked independently by both checkers (§6c).
- **That the whole address space was replayed.** Each set replays real requests
  to a published beat budget and covers the rest with single-granule probes at
  every boundary. What was dropped for budget, and the largest thing dropped,
  are published.
- **That the bytes are the model's bytes, outside the window.** Operand data is
  compared against authenticated checkpoint bytes only for the granules in the
  published window. Elsewhere what is checked is conveyance and ordering.
- **That the ignored deployment bundle was revalidated by the retained
  campaign.** Vector generation admitted and executed the exact Qwen deployment
  identities it records; the retained RTL campaign consumes only their derived
  vectors. The content-addressed deployment digest is the boundary, not the
  mutable contents of a local `build/` directory (§6f).
