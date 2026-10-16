# Additive local programme candidate — unadopted

The frozen S contract has one `su_prog`, 9,688 bits, 7,116 rows, 38 dictionary
columns and 301 SRAM macros. This directory records that **S/component shape**,
not the later RF36 native programme image. Recovery found that the cited RF36
native image has 302 macros: dictionary column 28 has four banks instead of
three. Its four-quarter candidate therefore needs **476**, not 474 or 475,
macros, because column 28 is duplicated across quarters 2 and 3. The RF36 image
and qualification must remain separate from this evidence.

The additive RTL retains global bank/address/image numbering, copies the
required index groups and boundary dictionary columns, captures read/config
pins locally, and gives every command column its own related clock root.
It adds exactly two startup edges; steady command interval remains one edge.
The normal source RTL and S contract are unchanged.

`component/` proves 282 rows over three starts using independent distinctive
dictionary/index images, real target SRAM models, the unchanged baseline RTL
and the additive RTL. It covers multi-bank reads, quarter/column boundaries,
the partial last column, image reuse, simultaneous final image write/start,
invalid lengths and invalid bank numbers. Quarter rotation, early command
stage and missing column clock all fail. These are storage/control proofs;
the images are not compiler token fixtures.

`mapped_summary.json` independently checks the actual mapped S-shaped candidate:
474 SRAMs, 23,931 FF, 9,688 registered command bits, four controller roots,
41 column roots and 474 separate macro roots. Every internally driven net has
at most 256 cell-pin loads; the old 9,689-load gate is absent. The mapped netlist
passes `check -assert` with actual mapped library cells loaded. Standard-cell
area is 12,667.35186 um²; SRAM area is excluded from that number.

The first source-shaped 7,116-row functional run failed its final test-harness
aggregate: the expected count was still 282 instead of E+21=7,137. No per-row
data or timing mismatch fired, but the run is not counted as a PASS. The failed
log is preserved. The corrected positive-only run is active; its verdict must
be collected separately. All three failing mutants are proved by the component
fixture, without a full-shape mutant claim. There is no
routed/native qualification, real pin/clock allocation, programme home, compiler
calendar release proof, full token cost or adoption. The large index-bank read
selectors and global configuration distribution still need actual geometry and
timing. The proposed eight-bank leaf outline in `model.json` is sizing only.

Reproduction scripts are under `rtl/test/hbm_programme_local_1016/`. Their
snapshot argument must point to the exact S snapshot recorded in `receipt.json`.
`run.sh SNAPSHOT CANDIDATE OUT 0` runs the component; `1` selects the S-shaped
301/474 fixture (the historical test flag is named `PRODUCTION`, without a
native-qualification implication). `synth.sh SNAPSHOT CANDIDATE` maps the
`production.sv` parameter wrapper; `check_mapped.py` checks its JSON output.
