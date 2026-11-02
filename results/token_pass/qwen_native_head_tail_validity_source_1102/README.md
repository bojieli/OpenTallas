This SOURCE diagnosis closes the selected tail valid path under legal steady
reset/count frames. It is not an executed whole-system failure or physical
phase/date claim. The passed24-word post boundary component remains qualified
for its stated compact input premise.

All256control paths (128valid,128fault) for q4(E2/E3) andq5(E4/E5), every8station
region and both near/far/north/south inputs, reach native cluster n_y bits512/513
through literal lane projections, whole-word registers and actual CA crossings.
No nout-aware thinning exists on these selected valid paths. Upper-half paths
include actual CTL transport feedthrough. Source hashes, exact operations and
line pointers are in source_join.json; full trace SHA/path is preserved there.

The actual PART1 loop issues all8slots for each of8Ksteps. e_v follows active,
S1..S3 carry it unconditionally, and t_vout is the raw valid line. NK/NL packed
bit512 takes tv; native nodes delay n_a-valid and report leg mismatch separately;
packed n_y bit512 takes nvy. Reset/CA warmup are not periodic row filters.
PART1 PORTSfalse makes a_tag zero, so raw_nb/raw_nout are NOT usable valid tags.
Its PORTS-only output mask does not suppress the selected raw publisher.

LastIB nout560/tiles1/split9 partitions six128row qgroups:

| Group | First rows by slot | Real vectors per K | Published raw valids now |
| --- | --- | --- | --- |
| q0..q3 | q*128+16*j | 8 | 8 |
| q4 | 512,528,544,560,... | 3 | 8 |
| q5 | 640,656,672,... | 0 | 8 |

HEAD source has298STNs/149receiver blocks. q4tail is actual sender9/receiver8,
nwords3/KC8, receiverdbase18944. There is no rowblock149/dbase19072 reservation
for q5. Current tail1 with64alignedraw pairs and nwords3 counts physical words
in groups of3: it selects ordinals21,22,23,45,46,47 (K2/K5 slots5..7), not desired
56,57,58 (K7slots0..2). Six receiver results follow with a native overflow fault
on the fourth fv. This is a source counter implication; no new RTL gate ran.

The coherent proposal is an explicitly defaultOFF HEAD publisher contract:
`row0=t*768+(gb>>9)*128+j*16; visible=row0<nout_r`, using full18bitt and28bit row
arithmetic. Its guard must pin the authenticated four HEAD descriptors and
resident code lease18432..20031, split9/GT3072/mmode0/k8. All64ROM/MAC/accumulator
updates remain unchanged; only t_vout is qualified by the correctly delayed
predicate. It gives q4 a gapped24valid pattern and q5 zero valids. A station-only
nwords3 repair cannot handle wholly absent q5. No source fix is implemented.

Using already-live t/j avoids restoring nb/nb_t state. An analytic upper state
budget is46predicate pipeline FF plus18nout_r and possibly1mmode_r perTG4,
about65per tile/49,920per rank before actual synthesis. Constant28bit additions,
comparison, match logic, fanout and TT/FF closure remain unmeasured. There are
zero extra arithmetic pipeline cycles. A fresh source event/lease must price
the actual sparse pattern: final selected raw ordinal58 versus compact23 is
35input edges later, without asserting global dates. Parent owns the separate
actual tail-control witness and any implementation decision.
