# Qcore RF source model and SU collection, 07:20 takeover

No storage RTL, FP successor, native build or physical gate was launched in this takeover. The existing R9 flop RF and FP4 failure remain immutable. The model entry is `tools/uarch_model.py:hbm_qcore_rf_sram_candidate_model`, implemented in `tools/hbm_static/qcore_rf_sram_model.py`; regenerate `rf_sram_model.json` using that script.

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
