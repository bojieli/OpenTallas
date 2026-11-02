This source frontier assesses full512-group arithmetic with actual native
components, without a whole hierarchy build. It executes nothing in PREP.

The selected fullleaf ROM_TILE identity is an elaboration parameter, checked
against the physical tile_id strap; actual macro INSTANCE/VIAMAP initialization
also occurs once. One selected fullleaf ELF cannot retarget physical identities.
Neither guard nor mask content is changed. Alternative A can reuse only verified
byte-identical generated arithmetic objects across a very small specialization
pilot; this proposal does not launch256 builds.

Alternative B changes the explicitly named component boundary. The unchanged
public `ot_qwen_romleaf_logic` and actual macro's existing VIAMAP content-context
parameter can run one ELF in distinct immutable fresh-process directories. Each
context authenticates original canonical tile/bank/column/path/fullmask SHA;
fixed generic component filenames identify content inputs, without claiming the
selected ROM_TILE wrapper executed or changed identity. The macro's INSTANCE
stays empty; its documented VIAMAP parameter initializes the unchanged array.
This is a public macro model API, not a new DUT port or runtime mask overwrite.
`native_head_rom_return_cut.sv` is a source-only bank4 boundary prototype using
actual logic and macro instances plus the selected pre-seam and RQR registers.

Selected REGROOT3/RPH3 uses one pre-seam request relay, native MPR, actual macro
read, capture, two expansion rungs, group g, return r, and RQR. Request publication
M returns BF16 atM+9, exactly MEM_EXTRA8's M+1+8. No extra L1 is present. The bare
unmodified public PART1 consumes WCONV1 1024-bit BF16 returns. Its i_gbase is an
existing strap and must stay constant through a fresh process. Selected NX0 disables public x_re/x_addr generation. Its X return must keep
that configuration and use the context group/K mapping at public x_q, with
one registered H read plus MEM_EXTRA8, using BF16-RNE H.
A future transcript must carry context, ordinal, address, launch/return counts
and actual producer response; executor-side guards must reject mismatches.
Expected oracle values cannot replace actual observed ROMproducer responses.

The bounded dataset is rowblock0/q0 and tail148/q4:128 TG4 contexts each,
tileIDs0..127 and512..639. A read-only2,183,168-byte physical-row extraction from
512 existing genuine bank4 files proves all720,896 used INT8 bytes match the
already SHA-guarded88-word logical crop. Unused80 physical bitlines are zero.
Existing full masks total139,722,752 bytes; none were copied or rewritten.
Whole-file SHA values are currently manifest declarations; actual pilot masks
must be fully hashed before execution. The local extraction artifact is
`/home/ubuntu/coord/tmp/codex-native-head-full512-source/genuine_mask_rows_metadata.json`.

Actual IL8 one-round PART1 operations require16,384 code reads/rawTG4 vectors
and262,144 raw scalar prefixes across256contexts:64fetches for each context.
The11,264vectors/180,224scalars are the useful reference subset. Tail padding
adds327,680 genuine code bytes, observed zero in the same physical-row excerpt.
The unchanged 176row reference still needs16 L6 stream contexts and704vectors;
actual collector suppression of padding is a separate source-join question. These counts describe rounds0/24 at the public execution boundary, not
all four native GME descriptors. Replaying the original8/8/8/1 instructions would
instead require1600 reads per context. Public one-round descriptors must retain
proper global q validity: block0 one-round nout768, tail last-round nout560;
only q0 orq4 is selected for this dataset. No dispatch/calendar adoption follows.

The next pilot should use two real identities, tile0/block0 andtile639/tail148,
fully immutable genuine masks, exact request/date/response controls and explicit
nominal clocks. Actual resource measurements must precede scaling. Parent owns
the source-exact L6 outer-face/node cut. No full hierarchy, source activation,
checkpoint regeneration, compiler or simulator was run for this assessment.
