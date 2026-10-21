# S81 contents-only twelve-pair ROM placement and calendar capacity

Owner 10-20 03:06 permits release ROM layout changes only with the existing physical views. This implementation changes compiler output only. All frame, element, XS, calendar-reader and ROM RTL remains unchanged. No physical view is changed or regated.

The switches are off by default:

- `OT_XS_QPAIRS=12`: use all twelve existing physical q pairs; keep the measured ten-pair a_proj placement and append its two idle pairs. Later phases rotate their active subset and translate planner assignments back to stable physical cfg/ROM slots.
- `OT_XS_GU_MERGE=1`: existing ROMCAP gate/up concatenation (3e78585a3), combined here.
- `OT_XS_CAL_SEGMENT=1`: deduplicate equal immutable stream programs, rebase short calendar intervals and reuse identical interval contents in the existing 4096-row ROM pair. PRIME/START uses fixed compiler-selected gaps. No completion/ready signal sets the schedule.

## Measured evidence

| Check | Result |
|---|---|
| Release col_h9_l4 frame / LK5 / Verilator5.050 | Five golden cases PASS: two different GU physical rotations, a one-row GU tail, two wq_b eight-row phases using all twelve pairs |
| Causal data/calendar negatives | GU and wq_b swap/shift controls each FAIL with retained witness logs |
| Full L0 frame compilation | 72 phases, zero legaliser faults, fixture max fill1088/8192 |
| Default / segmented calendar selftests | 23/23 PASS in both modes |
| Production GU sequence | 18 phases /54 fixture rows, P145 PASS, exact span2810; P144 FAIL4 sticky faults |
| Production wq_b sequence | 8 phases /64 fixture rows /96 RET words, P126 PASS, measured span1189; P125 FAIL4 sticky faults |
| Actual L0 multi-phase calendar | 5278 rows before reuse -> **1868**, 65 intervals, 19 unique |
| Actual L2 multi-phase calendar | 5552 rows before reuse -> **2006**, 68 intervals, 20 unique |
| MU admission, L0 and L2 | 46 AR users / 10+1 MTP users: zero collisions, busy-span premise PASS |
| Actual paired4096x72 ROM + 75-bit PINREG1 reader | Every-cycle golden trace PASS for both real images; missing re-prime and wrong-base controls FAIL with committed witnesses |
| Production DVC `emit_files` hook | Nine shared files per layer, byte-identical to reader-tested images (plus manifest) |

The seventeen compiler sources and seventy-five RTL sources of the single-phase exactness bench match committed1a4084829 exactly. The twenty-one imported compiler sources of both real calendar builds match fee5bd44a exactly. The DVC hook is4166f026c; it adds emission only, preserving the admitted image bytes. `compiler_sources.json`, `rtl_sources.sha256`, binary hashes and Verilator version are retained.

The original ten-pair/GU-unmerged compiler case needed6091/6501 calendar rows. Twelve pairs plus GU merge alone still needed5278/5552: selecting per-op base/length segments without reuse does not solve capacity. The existing XS has no calendar programming input and its reader rejects base+length>4096. Reusable contents solve this without STREAM_BURST hardware or another ROM pair.

## Why the reused schedule is exact

`dedup_stream` checks every original phase's stream payload against its shared replacement. The phase-ROM stream base and calendar stream address change together.

Each interval after the first starts on its phase's launch edge. The preceding interval carries its ACCEPT/CFG events and terminates two edges after its final required action. PRIME is twenty edges before the next START. The compiler checks each actual event gap, the issuer delay-line occupancy, and every original functional action's absolute edge/value. It also checks calendar availability at all GO/ACCEPT edges, including tag-zero accept words whose payload is zero.

ASAP op windows can touch. The packer joins the previous tail and the next head rather than attempting to re-prime an active reader. The hardware bench uses the existing source-checked reader and real physical via-map ROM simulation; no reader model substitutes for RTL.

## Adoption limits

This is a compiler/mechanism result, not a headline token-rate update or a die-bound token-pass result. The shared image covers the existing CALPIPE multi-phase-op scope. Single-phase a_proj/cmp and the separately owned Engram path, real gather/consumer scheduling, selected CAP/LEP/SVC/XDIE deltas and the complete layer DAG still belong to release integration. L14/L20 unsegmented op compilations pass; only L0/L2 reused images have been read back in this change.

The1088-word fill is the six-expert fixture, not a full release-checkpoint capacity claim. ROMCAP's all-twelve-pair110-stage estimate leaves headroom, but a complete per-stage expert map must still be admitted against actual per-pair ROM depth and cfg7 phase counts.

The new-shape production sequence runs are committed in `fseq12/` and `fseq12r2.otrun.log`. All78 production RTL hashes match1a4084829; the differing sequence testbench is retained in `fseq_src/`. GU18-phase P145 measures2810 exactly. The eight-phase wq_b P126 measures1189 from `u_sp.go` (GO0 edge63) to frame-root RET (edge1252). Its old compiler prediction1105 was84 edges short (7.6%). Commitc865c47c3 prices the twelve-pair vehicle with tail307; the default old223 remains unchanged. `span_correction.json` proves the corrected price changes no ROM/action/issuer bytes.

The WQBP composition denominator is a DIFFERENT origin and shape: first actual element capture to final root return,1987 edges on the fullsix15-phase/512-row vehicle, plus transport195 separately. The FSEQ1189 raw span must not silently replace that value. The same-origin GU3680->2810 replacement is directly composable.

`compose/` preserves both cases, with29 input hashes verified againstc865c47c3:

| Composition | AR tok/s | MTP tok/s | Qualification |
|---|---:|---:|---|
| Existing measured baseline |834.0|2649.1|Unchanged|
| GU same-origin improvement alone |854.7|2705.4|Component substitution; existing other shapes retained|
| Existing CALPIPE scenario |915.9|2869.4|Already a proposed scenario|
| CALPIPE + measured GU |940.8|2935.5|Same-origin GU substitution|
| Eight-frame compiled projection |965.0|2998.8|Assumes8x64=512 parallel rows; one h9 frame measured, new earlier spine-go origin retained conservatively, fixed transport195 and owed source-age edges unchanged; NOT release-adopted|

Minimum remaining measurement for the final projection: use the real static eight-frame slice stage bench and its native gather/launch calendar; measure actual producer capture, each frame-root RET and CAP consumer acceptance. Include h9, h9_MX and h10 geometries and take the slowest frame. Measure the same512-row/K1280 contract, with source-age markers for both spine GO and first actual element capture. Prove CAP descriptors, golden rows and consumer deadline, then compose fixed die transport analytically. A full-die simulation is unnecessary.

Initial stale-topology, insufficient-gap and legacy-base-overflow failures are preserved. They are superseded by the source-pinned real-image and RTL reader results, not overwritten.
