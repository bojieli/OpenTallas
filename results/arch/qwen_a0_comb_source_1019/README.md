# Private A0 combinational native-source substitution

This is the authorized source implementation of exactly the three combinational partitions in `e32ab74ba`, using the complete expanded graph from `8f6101cf2`. It is a separate private source artifact, with no production selector or public activation. No synthesis, HDL simulator, formal engine, placement or route ran. It is **not whole-A0 SAFE**.

The original emitted native source SHA256 is `422b8cdacc31dd6cc14cc912cf91a1a037f2de4e09a4875f1a1d9e0749f4f66a`. The decompressed `private_candidate.v.gz` SHA256 is `cec6c609e47f0bc72b6635d6aaa26ca2db2b26da6fc73979c176b29432b06725`. All dependency hashes are in `input_hashes.json`. `prove.py` regenerates the source, controls, finite proof and full census in this directory from the pinned repository dependencies.

The source has 38,619 cells, adding five actual `NOR2x1_ASAP7_75t_R`, three `OR2x2_ASAP7_75t_R` and two `AND3x1_ASAP7_75t_R` instances: **10 native cells / 0.8748 µm²**, zero new storage, clock pins or logical cycle edges. These are source counts and Liberty areas; synthesis retention, physical distribution and access RC/energy are not measured. Each copy has explicit `keep` and `dont_touch` attributes, whose downstream survival is unproved. No old transparent cell is deleted or credited.

`replicas.json` lists every actual input net and exact terminal group. All 269 moved terminals have original noninverting transparent parity. Their source connections now use the corresponding new output directly. Original instances and masters remain; only those exact 269 input connections change. The seven sequential controls, all sequential D/clock/reset/set nets, all ties and every protected original canonical-cone terminal remain identical. The original top module name and complete original hard-macro connections remain in the separate artifact; never compile it together with the original definition.

## Finite source-function proof

`native_liberty_cells.lib.gz` preserves complete real cell blocks from the source-pinned ASAP7 RVT SS SIMPLE and INVBUF libraries, including their original VDD/VSS roles. `native_liberty.json` gives library/block hashes, full pin directions, functions and areas. `native_four_state_truth_tables.json` records every input combination over 0/1/X/Z, interpreted with ordinary four-state Boolean operators applied to the actual Liberty function expressions. This is a functional interpretation of Liberty, not transistor simulation, timing-aware X propagation or foundry-model qualification.

The original and new complete emitted sources are reparsed with exact concatenation ordering, escaped identifiers and all real hard-pin connections. Every original native instance/master/pin is compared; only the named substitutions are accepted. A graph evaluator follows the actual original BUF/INV paths and new native-cell pins, using the real input nets as a local proof boundary. Across all input valuations, **5,936 moved-terminal comparisons match**. The 0/1 cases establish exhaustive steady-value substitution for these three publications; X/Z cases additionally check the stated functional interpretation and transparent polarity. This proof does not assert all-output sequential equivalence, reset reachability, phase, glitches, recovery/removal or setup/hold.

For each selected root, three controls mutate a real emitted source: a different real master, an actual wrong input-net connection, and an inverted-output real master. The complete mutant source is reparsed and evaluated on its real moved terminal. All **nine controls produce actual DUT terminal mismatches**, with input values and outputs recorded in `mutant_witnesses.json` and individual `mutants/*.log` files. These are functional mismatches, not malformed-source or policy-checker refusals. Each complete mutated source and its SHA are retained in `mutants/*.v.gz`.

## Complete fanout fixed point and remaining debt

The all-driver recount expands every source connection, then follows every transparent BUF/INV path to distinct real terminal input pins or output ports. It includes input-port drivers, clocks, ties, reset/set loads, hard macros and all transparent descendants. Direct loads count actual input pins; source output ports appear in the terminal count. The baseline **46,913 rows match the frozen native census exactly**, including complete endpoint sets. The new census has **46,923 rows**. Raw before/after rows, exact terminal additions/removals and every unsafe row are preserved in compressed JSON files.

Nonclock rows above 32 loads fall **70 → 59**: the three selected logical root rows and eight transparent alias/descendant rows become safe. The remaining 59 are **7 sequential roots + 2 tie roots + 50 transparent BUF/INV rows**. This is eleven fewer violation rows, not eleven independent repaired publications. Original selected root loads become NOR2 156→5, OR2 84→0 and AND3 34→0. The ten new copies drive 32/32/32/32/23, 32/32/20 and 32/2 terminals respectively.

All **22 added input pins** are included: leaf00_qn +8, `_14821_` +8, `_12924_` +2, `_14780_` +2 and leaf03_q +2. The complete upstream increases are:

| Actual driver | Terminal loads before → after | State |
|---|---:|---|
| active QN | 82 → 84 | Remains unsafe |
| `_21663_/Y` active BUF | 82 → 84 | Remains unsafe |
| `_21664_/Y` active INV | 38 → 40 | Remains unsafe |
| pend QN | 11 → 13 | Below limit |
| `_31784_/Y` pend BUF | 11 → 13 | Below limit |
| `_31849_/Y` OR3 | 20 → 28 | Below limit |
| reset leaf00 QN | 24 → 32 | At limit; 27 direct input pins |
| reset leaf03 QN | 23 → 25 | Below limit |
| leaf03 positive INV | 22 → 24 | Below limit |

No upstream row becomes newly unsafe. All original reset/tie/clock debt is retained, not waived. Seven sequential unsafe terminal counts remain split[0] 335, split[1] 415, split[2] 281, split[3] 235, wsrc 89, k_last 62 and active **84**. `unsafe_classification.json` identifies every removed violation and every worsened upstream row; `unsafe_after.json.gz` preserves all 59 remaining rows and their exact endpoints.

The Liberty VDD/VSS declarations establish pin roles only. Explicit physical PG attachment, synthesis survival, native sites, parent fit, actual phase/first meaningful use, ≤405 µm routes, TT setup/FF hold and pin-flop spread remain unqualified. No geometry, the nineteen-macro placement, sequential cloning, landed publication, reset branch or compiler age was changed. Added logical cycles are zero for this substitution; an integrated SU/MU token result is not claimed.

The initial baseline roundtrip rejected an output-port/direct-input-pin counting convention mismatch; `initial_direct_port_convention_failure.log` preserves it. The corrected check matches actual direct-pin and complete terminal sets on all 46,913 original rows. The bounded final proof used one local CPU and less than 0.5 GB RSS; `resource.log` records actual elapsed time and peak memory. No fleet or simulation resources were admitted.
