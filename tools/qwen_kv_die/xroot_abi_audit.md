Qwen root ABI audit: conditional field lower bounds, no architecture adoption
============================================================================

Source inspected: q14 tile branch8a9a083c5 (actual ctl GT6144/NW18/SMIN7,
TG4/W16, CEXT2). Core registers x_epoch={k[17:0],j[2:0]} alongside96-bit
x_addr on the same generation edge. Four addresses are
  A[i]=(xbase+(((tile_id*4+i) mod2^split)*xcs)+k*xks+j*xjs) mod2^24.
Round t does not change the x base; repeated rounds may reuse a snapshot
only while VM values stay unchanged. x_re[3:0] masks the incomplete GT/S tail.

149bits/root =128payload+phase4+epoch16+fillvalid is a PROPOSED lower bound.
It has no current production controller establishing how epoch16 maps to
{k18,j3}, full addresses, instruction generation, or source-write version.
Fillvalid qualifies a cache fill; it is NOT compute ib_go.

Separate common instruction =379bits (3*NW+13*AW+13) plus compute ib_go1,
therefore380 bits. Do not remove its issue bit because a fill is valid.
Counts with a copy of metadata per physical root:

 encoding                 root bits  32roots+common380  root+common380
 proposed opaque epoch16      149           5148              529
 direct k18/j3 +phase4         154           5308              534
 full96address key +valid      225           7580              605

The225-bit address-key response does not also require phase4 for matching:
root routing determines destination and the full quartet key is self-contained.
If the physical protocol still needs phase to assemble/gather, add it (229,
7708 source,609 distributed). Counts exclude credit/ready, instruction or
source-version generation IDs, snapshot capture/drain control, clock/reset,
error/poison, fanout copies and the actual route. They are necessary signal
counts for those encodings, not a final slot or capacity verdict.

An opaque16-bit token CAN be sufficient; it need not carry a truncated k.
Required proof: a bounded credit-controlled table retains full21-bit k/j,
instruction context, actual quartet addresses and source version; every
response token resolves to that exact entry; no token reuse until all
replicated consumers and in-flight old responses are drained. Reset or
clear must flush sources, transport and consumers coherently, or carry a
reset-generation tag. This table/request/control state is not free. A16-bit
sequence wrapping without the reuse/drain proof is insufficient: k65536
aliases k0 if epoch means low16(k), and dropping j aliases different xjs.

A direct21-bit coordinate encoding is collision-free for addresses only
conditional on one correctly latched common instruction, correct tile_id,
all four group offsets, request masks, and matching k/j pipeline placement.
It does not distinguish two instructions with the same k/j or two versions
of a concurrently written VM address. Instruction/source/reset generation
fields can be omitted ONLY with explicit serialization/drain/freshness
invariants proving old returns cannot be mistaken for new ones.

Minimum source request choices:
 - Direct coordinates: k18+j3+phase4+requestvalid1=26 bits, with the entire
   latched instruction and source generation supplied by the common context.
 - Literal quartet: address96+readmask4+requestvalid1=101 bits (per quartet),
   plus any required transaction/version tag; no instruction compression
   is needed for locating the four operands.
 - Compress quartet to firstaddress24+stride24+mask4+valid1=53 only after
   proving the four addresses are an affine sequence modulo2^24 for every
   supported split and tile mapping. TG4 and aligned tile_id*4 support that
   for valid split>=2, but lower split encodings and their fault behavior
   must be checked; do not assume it for all raw4-bit split values.
 - Replicated local request counters can omit transmitted k/j only after
   proving equal instruction acceptance, exact pre-update state, every
   enabled edge/stall/reset, snapshot-capture edge and phase alignment.

Phase4 is enough for32 cyclic roots covering SMAX11:512quad lines require
16 phases. It does NOT cover all raw split values through15 if those are
legal computational requests: split15 requires8192quads and256phases,
therefore phase8. Existing SMIN/SMAX faults must be preserved exactly;
masking split>11 into the supported field silently is not a proof.

VM freshness is a separate semantic obligation. The new unreplicated
2048-bit/column snapshot must capture at the original registered-o_v edge;
phase muxes then read that stable snapshot. Next-line writes may proceed,
but the next o_v must not overwrite it until every phase/gather return is
consumed or another snapshot bank holds it. A transaction token labeling
reads from live, changing line_data can identify a mixed snapshot and does
not repair the data. Each column must also prove equal phase/epoch/valid
under actual balanced control/me paths; root bit packing is
q_root[32*k+col]=q_col[4*root+k], not q_root[4*col+k].

Stalls: whole core, operand-memory response, ROM capture/return, TX, lane
accumulators, node/tree tags and shared result collectors must advance
coherently. Clocking a local cache response on the live base clock while
its core is paused advances data before tags. Core-side registeredresponse
with XLOCAL1 bypasses only the XL IREG and retains ME_EXTRA8; ib/go IREG
remains. Actual CEXT2 tile proof is still in progress. Earlier9f5f36024
proved a direct PART1 core seam, not the actual25-root tile or die.

No new physical ABI is adopted here.149/5148/529 stay proposed until an
actual controller/consumer proof closes the opaque-token obligations;154
is the direct-coordinate lower bound conditional on serialization and
freshness. Full96 keys remain the established arithmetic proof vehicle.

Back-to-back context warning: production ready=!active&&!pend rather than
full idle. The spine explicitly retains the previous instruction's last X
through two read-latency edges after accepting the next instruction. The
current arithmetic seam gate drains between instructions. Do not treat
clear-before-next-preload or one latched instruction as already proven by
ready. Preserve outstanding old context/returns, or prove and price an X-path
drain; a full arithmetic barrier is not silently permitted. Also, a compute
ib_go pulse travelling through live pure-delay stations can be lost while
core_clk is paused. Instruction holding/buffering or coherent producer and
corridor pause is required while a separate loader path remains live.
