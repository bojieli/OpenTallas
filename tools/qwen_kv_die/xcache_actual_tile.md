Actual CEXT2 tile/cache response seam
====================================

This gate uses immutable parent source commits, not patched production files.
Prepare/run with tools/qwen_kv_die/xcache_actual_tile_bench.py under ot-run.
Canonical source41be8efee defines ot_qwen_tile_ctl_tp8 (GT3072,NW18,XLOCAL1)
and ot_qwen_tile_ctl_tp8_ref (same GT3072, historical XLOCAL0 path).
The inherited GT6144 run is retained only as a legacy/fallback diagnostic.

Composition in this gate is the actual CEXT2 ctl plus RPS1/SPLIT1/MCLK1
children:5 ROM-row capture pipelines,8 lane slices,8 TX leaves,2 RQR leaves
and the node. All25 logical clocks and the cache response clock pause
coherently; the cache loader base clock continues. ROM macros use the same
synchronous deterministic INT8 image on both sides. VM data are finite FP32
hash values. This is structural arithmetic proof, not checkpoint, physical
clock signoff or native token/layer performance qualification.

The cache uses32 indexed128-bit entries with full21-bit {k18,j3} tags.
For native xjs0,J slots share one K entry; arbitraryJ uses the complete tag
and misses when a slot wraps. A fresh exact request is then loaded while the
whole pipeline pauses. Storage is32*(128+21+1)=4800 flops, plus128 output
flops and1 sticky fault:4929 total across the two related clocks, before
synthesis optimizations. This is an indexed candidate, not the earlier
256-entry full-address CAM. Full source instruction/version/drain proof is
still required before adopting a compressed physical root ABI.

The historical XL path is XL IREG1 then ME_EXTRA8. Local cached response is
already registered one core edge after the request. XLOCAL1 bypasses only
XL IREG; instruction/go IREG stays, and ME_EXTRA8 stays. The differential
bench compares each512-bit arithmetic t_out and valid against the canonical
XLOCAL0 path, with raw VM operands supplied before its IREG capture edge.
An independent oracle reads actual reference-core pre-update xc/gb/k/j state
and checks candidate x_re4/x_addr96/x_epoch21 on the generation edge.
This prevents the old NX0 dead exports or a copied fixture counter passing.
XLOCAL1 must restore NX=TG; external-spine XLOCAL0 keeps historical NX0.

First four IB379 words come from the pinned candidate TP8 program at
14065c8c7, results/rtl/ref_tile/qfd_su_vreduce/native_profile_1013/
candidate_tp8_layer0.hex, SHA256
120b42a583db68fb9faaa32d2076f1515d5c07e41787bf47533a1d230b4d1903.
PCs1/16/19/23 are decoded and packed, including actual weight/output/scale
bases and flags; they are not hand-derived opcode approximations. This
program itself is explicitly a candidate profile, not checkpoint execution.
Canonical physical tile IDs exercised are0,127,512,767,511,703; the die's
per-instance tile_id binding remains a separate pending requirement.

The six-op gate includes the four native ROM profiles plus SMAX11 and two
arbitraryJ stride diagnostics, instruction invalidation, reset during an
actual in-flight operation, manual pauses and reactive misses. It must
produce exactly680 arithmetic words and at least600 nonzero actual read
requests; the current positives produce684 requests and144 reactive misses.
The root/meta contract remains separate: fillvalid does not mean ib_go.

Negatives select the adjacent cached data row or add one unwanted XL edge.
Both must fail actual CEXT2 arithmetic, not just packet/metadata assertions.
The optional ALL_SPLITS diagnostic compares raw split0..15 codes and their
local tile fault behavior against the same canonical reference. It does not
assert that every raw code is a valid instruction under the full spine's
SMIN/SMAX checks; those faults must be preserved, not masked or relaxed.

Unclosed obligations: actual producer snapshot freshness and next-o_v drain,
complete VM/band/32-root transport/metadata protocol, global glitch-free
clock enable with real views, read metadata/instruction/version collision
proof, assigned pins, cache leaf physical closure, native die tile-ID ties,
and full native layer/token measurement including every actual wall-clock
pause. Preloading a local test cache is not a measured full VM transfer.

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
