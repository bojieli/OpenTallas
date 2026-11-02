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

The selected source mapping is now recorded in `selected_post_port_map.json`.
`native_head_post_port_map.py` follows named ports from literal native tile IDs
through all fifteen cluster add nodes and original die transport words to the
station's four own inputs. Each cluster's 64 groups use the canonical adjacent
balanced tree. Each pair covers eight disjoint 64-group intervals.

| Block | Receiver held own bracket | Sender neighbor bracket | Final operation |
| --- | --- | --- | --- |
| 0 | `(L4+L5)+(L7+L6)` | `(L0+L1)+(L3+L2)` | receiver + sender |
| 148 | `(L0+L1)+(L3+L2)` | `(L4+L5)+(L7+L6)` | receiver + sender |

`Li` denotes logical split groups `[64*i,64*(i+1))`, relative to the block's
code-group base. The literal brackets compare bitwise with the unchanged
canonical reference on all 88 K-prefix vectors / 1,408 FP32 values. This is a
source and reference arithmetic result. It does not prove executed collectors,
arrival alignment, region clock phase, station scale timing, or AMAX integration.
The actual near-input SKEW14 and neighbor transport remain required fixture
premises; near inputs cannot simply be published with the far inputs.
