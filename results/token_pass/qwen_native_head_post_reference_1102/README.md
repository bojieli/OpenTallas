Genuine selected-row data and REFERENCE S8 post boundary inputs, not executed L6.

The existing rank0 INT8 image was streamed read-only and checked against its
pinned source hash. Only88 selected word slices were extracted: block0 has
128rows/64words at code groups0..511; block148 has48rows/24words at code groups
2048..2559. Total720896 genuine INT8 bytes. No full151MB image was copied and no
checkpoint or quantization was regenerated.

Canonical H4096 uses actual4096 CROM norm gains, X32 and canonical RSTD3cffffff,
then BF16-RNE projection expanded to FP32. Its first32 values match the existing
canonical H32_me fixture. For each of176 selected rows, each of512 logical split
groups accumulates eight sequential RNE INT8*H products from+0. Each of eight
logical L6 streams reduces64 such group prefixes by the canonical pairwise tree.
The output is704 REFERENCE vectors/11264 FP32 values, including all K0..K7
prefixes. Logical stream labels are group intervals, not guessed physical ports.
Final512-split raw and genuine BF16-scaled REFERENCE values also accompany them;
the raw values match an independent call to canonical G.matvec(...,split512).

All64 ACTUAL captured native TG4 block0 prefix vectors (1024 FP32 values) match
the independent first-four-group reference, across K0..K7 and all eight slots.
The capture source hash is pinned in actual_TG4_block0_crosscheck.json. This
cross-check establishes that bounded TG4 prefix agreement only; it does not
turn any generated64-group L6 stream into an executed ME output or full logit.

Source preparation used0.16s wall/37208KB peak RSS. No RTL compile, simulation,
EDA or heavy dispatch occurred. Exact group-to-collector-port membership and
fs/ns/fn/nn bracketing remain a source graph task; these inputs must not be wired
by geographic guesses or clock aliases. Full STN/AMAX execution remains separate.
