# Shared landing SRAM backend: source contract and admission model

Status: MODEL ONLY. No canonical RTL, generator, consumer or gate changed. Canonical source owner is CODEX PGVM. The three consumer owners retain integration. Imported Yosys sequential-cell behavioral models are not used by this arithmetic/source inventory.

## Frozen inputs and storage cost

The adjacent records/specs are exact copies. `inventory.json` binds their SHA256 and records every width, source/destination region and Manhattan distance between the declared region centres. HBM/S81 git refs are recorded; QW inputs were read from the owned slice6 parent WT, with exact bytes copied and hashed. These centres are model anchors, not measured placements or timing results. Actual endpoint geometry must replace them before physical admission.

|Consumer|D / K / E|Readers / writers|Sum reader widths|All-reader-copy 32x64 macros / area um2|Only >2048-bit reader copies: macros / area um2|
|---|---|---|---:|---:|---:|
|HBM PGLG|2 / 1 / 1|16 / 16|14002|230 / 127325.60|134 / 74181.00|
|S81 lpk4|4 / 2 / 2|17 / 17|3604|69 / 38197.68|54 / 29893.84|
|QW slice6|4 / 2 / 2|183 / 154|28312|564 / 312224.52|322 / 178255.84|

The hybrid column leaves smaller logical stores as independently bounded FF rings, and therefore does not claim all-native32 yet. Splitting one large logical bank into FF chunks does not exempt it from SRAM. QW has 14 unique D4 writer stores >2048 bits, consumed by19 readers; independent reader clocks require replicated read storage or a proven multiport service schedule. Its419-macro /231954.03um2 shared-writer total is a storage-only lower bound, not a realizable one-read-port backend for all readers. No credit/backpressure or dynamic arbitration may be added.

Concrete existing macro is v2 `ot_sram_1r1w2c_32x64_m1`: 32.0x17.3um approximately, exact31.992x17.304um, 553.589568um2; 32rows*64bits allocated even when D2/D4/D8. The SHA receipt binds Verilog/LEF/all-corner Lib/JSON. SS model clk-Q317.7648ps, setup39.8005ps, hold30.0740ps, min-period318.1278ps. These are repository characterized model values, not new silicon measurements. Cost above excludes final data FFs, reset/control replicas, routing channels, input/output hops, SRAM clock trees, parent resizing and compiler padding. Exact macro origins/orientations/pin tracks still need owner-approved physical evidence.

## Joint interface, ownership and multicast

Proposed new opt-in module `ot_pl_land_mem` owns both halves: parameters W,D,K and separately priced source/read pipeline depths; ports `ck_w,ck_r,rsi_w,rsi_r,i[W-1:0],o[W-1:0]`. No public bank wire, ready, credit or training interface. One instance per destination read clock. A source writer shared by several readers is duplicated into one macro bank per reader unless a concrete multi-read-port master and clock proof exists. Generator records must preserve the original net/ring_of/reader identity and explicitly report logical width, physical copies, actual cells, clock pins and added edges.

SRAM writes preserve epoch wc modulo D. SRAM reads are synchronous. Final output must still be a register and must reproduce the original zero-on-invalid/warm-up behavior without relying on the behavioral array's initialization. The candidate therefore needs a final data register, a valid pipeline derived from the actual reset/epoch contract, and bounded local control state per macro group. SRAM contents remain arbitrary through reset. Epoch tags remain diagnostic; no silicon fault may be masked by assumed initialization.

For small FF rings the measured chunk24 implementation is unsafe: W1095/D4 writer rq105 loads, D8 rq209; read_oh26/write_oh27 are safe but do not bound rq. Top reset also46 loads. Reset/warm/valid and writer enables require kept bounded copies of the actual state/cone, including a reset forest of equal total depth. New grouping cannot silently change rsi release age. Bound all data/control/reset drivers to32 in the mapped native census, including buffer/inverter transitive roots; synthesis-equivalent copies must remain distinct through CTS/GRT/final netlists.

## Edge/phase proof required before source adoption

Original output at reader edge t is slot `(rc(t)-K) mod D`, expected epoch `rc(t)-K`, zero unless warm and written. With a synchronous SRAM and final output FF, prefetch at t-1 would address `(rc(t-1)-K+1) mod D`. Thus effective read age is K-1, one less than the old bank-wire landing window. This is not a drop-in timing-equivalent replacement.

HBM actual K1 cannot use that lookahead while retaining the original age without a same-epoch write/read collision or an unproven phase assumption. Its minimum safe contract must be recomputed and any K/edge growth explicitly priced. S81 and QW K2 are only candidates: actual write/read phase intervals, clock/reset release order, minimum write completion-to-read setup and maximum SRAM-read-to-final-FF setup/hold must be proved at all corners. Same nominal PLL frequency does not prove phase or first use. A +/-400ps phase bound at833ps, for example, is merely a hypothetical bound; it has not been established for these consumers and cannot be used as admission evidence.

The certificate must list each actual clock pair and reset first-active edges, solve the latest write completion before each read and the earliest overwrite after each read, forbid read/write same-address ambiguity, and prove exact output epoch over wraparound and in-flight reset. Positive traces with arbitrary initial SRAM, both reset orderings allowed by hardware and extreme legal phases must match the original contract. Causal mutants must expose wrong read epoch, early read, reset-age slip and omitted physical hops. No false-path/multicycle relaxation may hide a newly single-cycle SRAM output path.

## Reach and implementation choice

Model centre distances: HBM max691.2um; S81 max832.2um (one of17 pairs>810); QW max3245.4um (120of183>810). A single macro placed between source and destination cannot be within405um Manhattan reach of both centres if their separation exceeds810um, even before macro extent, obstacle detours or local pin locations. These are source-model blocking findings to validate against actual endpoint placement, not a blanket measured physical FAIL.

For long pairs, place the memory near one clock region and add explicit data/valid/epoch pipeline hops under a related clock, or partition the parent into intermediate registered regions. Minimum purely geometric data hops is ceil(distance/405), before macro footprint/channels. The source or destination pipeline cost must enter the generated dependency graph and compiler calendar, followed by balanced joins. D/E/K must be re-solved for the new write/read schedule; existing D4/K2 or D8/K4 is not assumed to absorb those hops for free. Required SRAM width/clock-tree area plus extra register area and per-operation latency must be charged before proposing a rate.

Next concrete deliverable is a per-consumer pair/phase/reset certificate and priced opt-in contract, then a direct RTL+real macro-model coupon with causal mutants. Only after that: actual mapped all-driver<=32, >2kb SRAM inventory, registered boundary/reach checks, physical kit/PNG review and gate. This packet authorizes neither generation nor physical build.

Owner follow-up: S81 frame-link and QW slice6 explicitly confirmed no hardware-backed allowed regional phase interval or per-pair reset first-active order is currently available. QW additionally reports its D8 lab reset cone has K[4,3], not an immutable K certificate, and its clock-bump ROM lacks production package/PLL correlation. Nominal reset depth and frequency remain inventory facts only. The phase admission status is BLOCKED until concrete hardware evidence arrives; no source build follows from the cost model.
