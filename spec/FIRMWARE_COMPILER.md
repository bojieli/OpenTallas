# Firmware and compiler execution contract

**Document:** SPEC-FW 1.0

The compiler converts a pinned model checkpoint and physical defect/capability map
into a mask image description, deterministic schedules, test signatures, and a
deployment manifest. Firmware validates and activates those artifacts. Neither may
reinterpret a physically personalized ROM as another image.

## FW-1 Artifact set and ownership

One build produces:

| Artifact | Owner | Mutability | Required identity |
|---|---|---|---|
| source inventory | checkpoint profiler | immutable/pinned | repository, revision, index/config hashes, tensor hashes |
| canonical tensor map | image compiler | immutable | compiler version and source inventory hash |
| ROM personalization database | physical/mask flow | mask-programmed | canonical map and image SHA-256 |
| expected block CRC/MISR/KAT | image compiler | immutable manifest data | image SHA-256 |
| stage/layer partition | architecture compiler | immutable for image | image SHA-256 |
| active/shadow static schedules | schedule compiler | runtime loadable, manifest constrained | schedule/certificate hash and epoch |
| repair map | manufacturing/field diagnostic flow | runtime loadable while quiescent | device/image identity and generation |
| firmware binary/config | firmware build | updateable under product policy | ABI and build hash |
| deployment manifest | release process | immutable record | SHA-256; product signature later |

Large checkpoint payloads and mask databases need not be committed. Their pinned
hashes, small known-answer slices, tool versions, commands, and generated metadata
must be reproducible. The public repository may compile synthetic/sample payloads
through the exact layout path without claiming full-image manufacture.

## FW-2 Manifest and image identity

### FW-2.1 Image identity

The image identity is SHA-256 over a canonical, length-prefixed serialization of:

1. format/schema and ABI major/minor;
2. source repository/revision and config/index/tensor-inventory hashes;
3. model topology and canonical numeric profile;
4. every tensor role, logical shape, source/canonical dtype, scale/block metadata,
   byte count, and content hash;
5. stage layer partitions and physical region capacities;
6. canonical stripe/layout rules and per-region hashes;
7. expected ROM CRC32C blocks, MISRs, and numerical known-answer hashes;
8. required schedule certificate hashes and repair-compatibility policy;
9. compiler/build identifiers and normative parameter hashes.

Canonical serialization sorts map keys by UTF-8 byte order, encodes integers as
unsigned little-endian fixed-width fields declared by schema, rejects duplicate
keys/noncanonical numbers, and contains no timestamp, absolute path, hostname, or
random value. The 256 identity bits are mask/macro-visible and duplicated in the
release manifest.

### FW-2.2 Deployment manifest

The manifest contains:

- schema, image ID, human label, model role, source pins, and evidence class;
- compatible hardware/spec/ABI versions and required numeric profile;
- stage count/index, owned half-open layer interval, ROM regions, raw/usable bytes,
  HBM minimum, and maximum context/batch bounds;
- tensor/scale layout, activation stride, route limits, microprogram, and expected
  macro latency classes;
- schedule IDs, byte hashes, proof-certificate hashes, epoch length, credit/buffer
  bounds, and allowed quarantine sets;
- repair-map compatibility fields and minimum post-repair capacity/bandwidth;
- expected BIST CRC/MISR/KAT values and diagnostic localization map;
- compiler and checker versions, command-line parameters, input hashes, and build
  environment lock hash;
- SHA-256 identity and, only in a later product flow, owner signature/certificate.

An unsigned public manifest proves reproducibility/integrity binding, not owner
authenticity. Firmware rejects unknown required fields, incompatible major versions,
duplicate regions, overlap, integer overflow, out-of-range addresses, or identity
mismatch.

### FW-2.3 Immutability rules

Weights, scales, block CRCs, immutable microprogram regions, expected signatures,
and image identity are mask-programmed or ROM-macro contents. Firmware has no write
opcode for them. Runtime configuration names manifest objects; it does not patch
tensor bytes, scale layout, expert count, layer ownership, numeric interpretation,
or expected signatures.

Development behavioral ROM initialization is accepted only at elaboration and its
file hash must match the test manifest. A product-like synthesis rejects writable
memories in the weight hierarchy and development override signals.

## FW-3 Image compilation

### FW-3.1 Pipeline and model profiles

Compilation stages are deterministic:

1. verify pinned config/index/header/payload hashes and complete tensor coverage;
2. classify ordinary target, draft-only, resident-only, dense/shared, routed,
   scale, embedding/front-end, and diagnostic metadata;
3. validate model topology and numeric tensor shapes against the selected profile;
4. canonicalize dtype and nibble/byte/tile/scale ordering;
5. choose the frozen contiguous layer partition and check every local capacity;
6. stripe logical tensor blocks across service tiles/macros, preserving repair and
   CRC region constraints;
7. generate per-block CRC32C, full-region MISR, sample known-answer vectors, and
   image identity;
8. generate layer microprograms, schedules, certificates, capacity/performance
   metadata, and manifest;
9. independently reread emitted artifacts and reproduce every hash/check.

Frozen public-reference proxy partitions are Flash `[0,22),[22,43)`; Pro `[0,11)` followed by
ten-layer intervals through `[51,61)`; the eleven Kimi intervals recorded in the
architecture spec; and Qwen3-8B `[0,36)` on one stage. A partition change is an
image-version change even if logical logits remain equivalent.

Full Kimi U8-packed numerical execution is not implicitly treated as DeepSeek
MXFP4. It needs a separately defined/qualified numeric profile. Until then Kimi
compilation may emit capacity/control/schedule stress regions and clearly labeled
synthetic numeric data.

### FW-3.2 Legality and capacity

The compiler uses integers for byte/address/cycle bounds and checks addition,
multiplication, alignment, and unit conversion overflow. It rejects:

- missing, duplicated, overlapping, unexpected, or hash-mismatched tensors;
- a tensor dtype/shape/scale layout outside the numeric profile;
- any indivisible region larger than local ROM or HBM capacity;
- total raw/usable stage capacity, CRC/repair reserve, or alignment overflow;
- an expert/layer/top-k/context/stage identifier outside architectural fields;
- a route, buffer, credit, schedule, or macro-latency bound above hardware capability;
- an image whose degraded repair map cannot preserve all logical bytes and routes;
- a required tensor classified resident-only or draft-only without an explicit
  execution role.

Capacity reports list raw, integrity, repair, fragmentation, resident-only, draft,
ordinary target, and free bytes per physical stage. Aggregate bytes are never the
sole legality check.

### FW-3.3 Canonical striping

The stripe function is a versioned pure mapping from:

```text
{image_region, tensor_id, layer, expert/shared_id, output_row,
 reduction_block, element, scale_or_data}
```

to:

```text
{stage, reticle, tile, ROM_macro, logical_row, logical_column,
 nibble_or_byte_lane, scale_address, CRC_block}
```

Logical matrix blocks are assigned round-robin over ascending service tile ID,
then macro ID, while keeping one numeric block and its scale/CRC association
explicit. The physical repair translator acts after this logical mapping. Dense
and routed regions never alias. Padding is positive zero, included in CRC, and
must be zero in the emitted image.

The compiler emits inverse-map diagnostics and at least one known-answer block per
tensor/macro class. Independent checking reconstructs the logical tensor bytes from
the physical map and compares the canonical hash.

## FW-4 Schedule and repair compilation

### FW-4.1 Static schedule certificate

The schedule compiler takes the enabled resource graph, logical stripe map,
collective operation, payload/partial sizes, macro latency, slot count, link widths,
and buffer/credit limits. It emits active/shadow bank bytes and a certificate with:

- exact input hashes and topology/repair generation;
- source selection and expected-valid/type/sequence for every output/slot;
- complete route endpoints and terminal consumption;
- conflict proof per output/slot;
- route termination and no-cycle dependency proof;
- per-buffer occupancy trace and maximum bound;
- expected packet/flit/source counts for reduction groups;
- disabled/quarantined resource absence;
- epoch length, schedule CRC, certificate hash, and checker version.

The independent checker does not reuse the compiler's routing algorithm. It parses
only the emitted schedule/certificate and reconstructs conflicts, paths, sequence,
and occupancy. Hardware range/CRC checks are necessary but not sufficient for
schedule activation.

### FW-4.2 Repair compilation

Manufacturing diagnostics produce physical defect observations, not arbitrary
logical remaps. The repair compiler assigns characterized spare rows/columns,
validates injectivity, removes failed tiles/links/channels, recomputes available
capacity/bandwidth, and invokes stripe/schedule recompilation if permitted by the
image compatibility policy.

The repair map includes device/image identity, monotonic generation, every mapping
and quarantine, capacity delta, expected post-repair BIST, schedule compatibility,
tool/input hashes, and CRC32C. It activates only after hardware and firmware checks,
quiescence, shadow load, BIST, and atomic generation change. Failure retains the
old map or leaves the device in SAFE; it never partially activates.

## FW-5 Boot and operational firmware

### FW-5.1 Boot sequence

Firmware follows this fail-closed state machine:

1. read immutable device/stage/image identity and spec/ABI capabilities;
2. qualify AON/core clocks, reset generations, straps, and macro presence;
3. obtain the device-bound repair map and validate identity, generation, CRC, range,
   injectivity, capacity, and policy;
4. load repair shadow, invoke repair BIST, and atomically activate;
5. load the manifest-matched schedule/certificate into shadow and validate hardware
   CRC/ranges plus independent proof result;
6. run mandatory control, SRAM, NoC, HBM, link, ROM, numeric, and end-to-end BIST;
7. compare image ID, block CRC/MISR/KAT, partitions, stage-neighbor identities, and
   expected degraded capability;
8. commit schedule epoch, publish capacity/counters, enter IDLE, and wait for explicit
   service enable;
9. on any failure, capture diagnostics and enter SAFE without queue enable.

Boot steps and results are logged with device/image/repair/schedule identities.
Service software cannot skip a failed mandatory step with an error-mask write.

### FW-5.2 Runtime ownership and recovery

Firmware serializes schedule/repair commits, BIST, power transitions, and service
ownership. It never writes active schedule/repair banks. Quiesce waits for hardware
acknowledgement and checks counters/credits before commit/reset. Timeouts request
abort and preserve first-error/reset cause.

Correctable errors trigger policy counters/scrub. A quarantinable permanent fault
causes quiesce, diagnostic confirmation, repair/schedule recompile/load, BIST, new
capability publication, and resume only if the manifest remains legal. Identity,
credit-conservation, clock/power, or required-capacity failure enters SAFE and
requires reset/requalification.

## FW-6 ABI and release control

### FW-6.1 ABI and capability discovery

Host software first reads ID, spec/ABI version, image ID, stage/partition, numeric
profile, queue/tag/session depths, schedule limits, enabled resources, HBM/ROM
capacity, power state, and degraded flags. It submits only compatible commands and
treats advertised capacity as authoritative.

Major ABI changes can alter record meaning/width and require coordinated firmware,
driver, RTL, specification, and manifest changes. Minor changes may add capability,
status, opcode, or CSR values using previously reserved encodings while preserving
old semantics. Hardware rejects request minor versions it cannot interpret safely.

### FW-6.2 Reproducible release

A release archive contains source commits, clean-tree status, locked dependencies,
tool/container versions, compiler/checker binaries or sources, complete commands,
input/output SHA-256 hashes, manifests, schedules/certificates, repair-policy schema,
known-answer data, test/regression results, bugs/waivers, and evidence classification.

Two clean builds on independent directories must produce byte-identical canonical
artifacts. Full mask/payload files may reside in controlled storage; their hashes
and independently checked metadata remain in the archive. A timestamp belongs in
an outer release record and never changes the image identity.
