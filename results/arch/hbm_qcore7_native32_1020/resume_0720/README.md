# Qcore RF source model and SU collection, 07:20 takeover

Storage remains model-only: no storage RTL or physical gate was launched. The existing R9 flop RF and FP4 failure remain immutable. Independently authorized FP primitive successors were measured; FP6 now passes the scoped source gates described below. The model entry is `tools/uarch_model.py:hbm_qcore_rf_sram_candidate_model`, implemented in `tools/hbm_static/qcore_rf_sram_model.py`; regenerate `rf_sram_model.json` using that script.

The RF is 256×32 bits, exposed as64banks×4rows. It can accept five independent normal32-bit reads plus one8-word drain each serial edge (52bytes/edge), and four32-bit relay writes plus one256-bit COLL write (48bytes/edge). Source rules resolve same-bank relay collisions by highest port, then COLL overrides the matching eight banks; matching a bank with different row still counts as collision. A replacement must preserve this rule and fault behavior, not silently broaden successful writes.

| Candidate | Existing128×256 SRAMs | Required additional premise |
|---|---:|---|
| Five writer-owned arrays with six read replicas and latest-writer selection |30 | None on traffic concurrency; exact priority/state implementation remains unbuilt |
| One packed256-bit write row, six read replicas |6 | All writes on each edge share packed row addr[7:3] |
| Four packed physical banks, six read replicas |24 | Writes targeting each bank share its packed row on every edge |

The general candidate packs eight consecutive words into each256-bit SRAM row. Each scalar writer has one independent masked-write array; COLL has its own full-row-write array. All five arrays have six read replicas, since the five normal readers and class5 drain can request different packed rows. A persistent256×3-bit last-writer table chooses one of five arrays independently for each word. This table is768bits, below the2kb storage threshold. It must not reset to owner0 because the original RF data survives reset. Arbitrary startup owner codes and SRAM contents require a coupled-state/first-valid proof; zero-initialized SRAM simulation grants no startup qualification.

Logical edges can match the old component contract: capture command/write atE, macro read-before-write/commit atE+1, select/gate data atE+2, external RF result atE+3. This is a source-level candidate, not timing or physical proof. Thirty macros alone cost116,747.3um² versus the old78,848.6um² outline. A coarse literal43.2 grid for30RF+2existing reducer macros gives604.8×777.6um, with129.6×86.4pitch and34.776/45.36um channels. This is an area/reach screen, not an approved floorplan: actual pin access, channel tracks, one full-width40–60%std band, clockspread and PG remain unproved. The full source stage crosses405um without regional transport; every added registered seam must enter the static calendar and latency model before building storage RTL. No rate credit is claimed.

The current die structural contract was identified by the DIE owner at `artifacts/hdie-d4/d4g_gen2e4_r7portage/net/contract_pre.json` (source0ae60e322), with qcore MUT0/COLLPORT1/RF_LOCAL1 and programme PIPE2/start advance6. It does not inventory actual traffic. The cited old serial manifest SHA544ba72d0cf50f2ca1f75092fd1ba5c9a56adbb2b590bd77e7f30ebdb2a25e93 is explicitly unqualified standalone producer evidence:7116edges versus current c5 default7111. It cannot justify either smaller candidate. The DIE owner is tracing the current host-config image.

`model_check.json` records exact unified-wrapper invocation and arithmetic invariants. Whole-module import initially stopped on a missing sparse baseline dependency; it was not presented as a full unified-model suite PASS. No hardware or throughput test occurred.

## Original SU jobs

Programme-store r12_clg finished06:24: **FAIL clock_rule**, TT136.0ps/FF143.8ps pin-flop spread against80ps. GRT0 and native18 are scoped passes. Placement-RC diagnostic setup reg−94.4ps/macro−22.3ps and hold−95.78ps do not qualify timing. The source start commit is8d12be477; actual identity is an exact content snapshot with archive SHA bd620de25c59878b70ceb5e7ecca8f179bc1efa906192c43448a62fda24998fb. Original shipping manifest is compressed without changing bytes in `r12_clg/source_snapshot.json.gz`. Both PNGs were personally viewed:11hard leaves/3columns, sparse standard logic around perimeter and vertical channels. No band/reach/PG qualification or submit.

k9xr remains in preGPL `io_flop_at_pins` hook on ep7; pslice r9b remains in GRT/incremental legalization on ep5. Original clients/run directories were read only and preserved. MC3F e6dfdb4e2 remains literal l531/l358 models with missing ROOT approval and band-confinement mechanism; no gates or duplication. SU7/VMG8 lane files were not found; no newer qcore build was found in pending/tree/lane reconciliation.

## Traffic-independent regional transport alternatives

The unified model now contains reproducible `regional_transport` alternatives. A detailed explanation is in `rf_regional_latency_model.json`. Six read-local hard leaves each hold five writer-owned macro arrays. A single central768-bit owner table sends39 selected owner bits along matching data stages; state is not replicated into six indexed flop tables. This moves416bits of selected read data plus36 command bits back from the leaves, versus7680bits/edge for a five-writer-leaf architecture gathering all read arrays centrally.

A conservative3×3 grid reserves the centre for ownership/control and six outer leaf slots for5macro/345.6-square readers. With43.2um inter-leaf channels,388.8um grid segments stay below405um. A far corner requires two grid hops plus one face/local hop. The budget is command+3, return3segments: readE+8 versusE+3 (+5edges), writecommitE+4 versusE+1 (+3). At an ASSUMED single usable0.048um-pitch signal layer with50%tracks available,43.2um supplies450tracks against489command bits per independent corridor, so this screen FAILS capacity. Actual routing layers could change that result; no capacity qualification is claimed.

At86.4um channels the same conservative arithmetic screen supplies900tracks. Grid-centre spacing432um requires two registered segments per axis, giving command+5/return5segments: readE+12 (+9edges), writecommitE+6 (+5). The coarse parent becomes1296-square with a16,673FF transport budget, excluding pin/reset/clock/branch copies. This is a traffic-independent candidate price, not a topology choice, tight lower bound or approved floorplan. The old280.8-square slot cannot contain it; DIE must recompose all replicas and the actual reticle envelope. Local full-width density, native fanout, PG and clockspread remain unmeasured.

The generic geometric lower bound is only `ceil(ManhattanD/405)`segments for an explicitly named source/destination pair. It does not prove a particular pair exists or that the illustrative grid is globally minimal. Edge accounting explicitly includes which capture registers already exist: root commandE, local commandE+Hc, macroE+Hc+1, selectionE+Hc+2, returnKsegments endingE+Hc+2+K. Relative readdelta isHc+K−1, write deltaHc. No extra frequency or multi-pumping is assumed.


## Independent FP6 primitive result

FP6 source d73bee5f7, LAT6/DRST0, **PASS actual TT RVT native max32/3246roots, zero role errors and zero constant outputs**. All14 exact-copy families passed; actual7895-cell alias graph passed and shipped source SHA matches the private source plus unchanged shared arithmetic. Three seeds each20,030 every-edge y/err/valid checks PASS, including invalid data and repeated resets. LAT5 causal negatives fail19634/19617/19641 checks; directly inverting the actual9-bit shift-stage select fails8021/20030, with a clean expected-failure wrapper. Mapped area442um² versus FP4 420 (+22,5.2%); no extra FF/pipeline edge from the new control decomposition.

This fixes FP4's three B2 native violations by separating exponent LZC and three shift-local count trees, then dividing each of five barrelshift stages into three kept9-output consumer groups. Earlier FP5 only isolated exponent from shift: native FAIL4/max75 on shift count bits0..3, despite the exactness bench passing. Its direct wrongcount mutation raw bench FAIL8021, but that run's classification wrapper failed because remote rg was absent; both raw/wrapper failures are preserved. FP6 uses grep for classification and catches the actual mechanism mutation cleanly.

Exact FP6 sources, native report, family/graph proofs, benchmark logs and prior failures live in `fp6/`; no qcore integration, layout, throughput, PG/clock or SS/FF timing claim transfers. All own FP5/FP6 jobs are terminal. Remote snapshots src_fp5/fp_native5/src_fp6/fp_native6 and mutation variants remain preserved.
