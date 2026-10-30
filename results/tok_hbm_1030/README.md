HBM native VM continuation (2026-10-30)

Qualified bounded chain now covers actual source records1458–1558 (101 source
records) as684 native commands in fourteen phases. No RTL/arithmetic change.
The original unreplayed1537–1558 preparation is not adopted: wrapping exposed
phase0/1542 consuming a sector written by phase3/1540. A second source-order
hazard appears inside1545: earlier-row outputs overwrite later-row C scalars.
The original blanket two-phase reorder therefore fails, despite fitting VM.

The explicit cuts1537–1541,1542–1544,1545,1546–1558 restore original value order.
The HC_POST1545 first three rows remain scalar commands because native ROWX
independence fails; its next three rows retain a native array. Shared-weight SM
arrays remain grouped. Phase-private early publication exports nine HC sectors.

vm_pipeline.py walks actual boundary liveness backwards from the final cut.
Each source region retains downstream loads and untouched boundary sectors,
including partial-sector neighbours. This fixes the missing147504 publication
reported when linking directly against the older chain_attention artifact.
All fourteen phases fit the old262144-word VM; largest stays238592.

Reproduction (set compiler tools/image to the source snapshot in the prior handoff):
PYTHONPATH=/home/ubuntu/OpenTallas/tools python3 tools/hbm_next/vm_pipeline.py \
 --image /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r \
 --compiler-tools /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools \
 --scratch-base 0x1F00000000 \
 --cuts 1458:1473,1474:1527,1528:1536,1537:1541,1542:1544,1545:1545,1546:1558 \
 --out-dir results/tok_hbm_1030/pipeline
python3 results/tok_hbm_2249/check_chain.py \
 --shadow results/tok_hbm_1030/pipeline/link6 \
 --values results/tok_hbm_1030/pipeline/values0

Canonical source/value replay PASS2534778 read words,143856 final boundary
words,29 early sectors; wrong interstage epochs, missing drains and illegal
stripe controls caught. Real native HGI DMA executes added transfers; arithmetic
outputs remain tagged source versions, not numerical RTL execution.

Native boundary traffic6136704bytes, plus conservative unit drains, remains
UNPRICED. Each phase uses separate candidate linear HBM scratch; reservation is
explicitly false. Original source1458–1558 entry epoch publication, dynamic
expert boundary1559 onward, all other programme regions, actual numerical RTL,
mutable HBM execution and full physical calendar are OPEN. No whole-programme
fit, G5 or token-rate claim.

Expert continuation1559–1590

vm_expert_entry.py retains the actual full six-row expert union, all six indexed
score gathers, both runtime count loops, all three rsel SM records, routed/shared
combine slots and the source's intermediate aliasing. One contiguous source
workspace plus count/table and ID regions fits105808 words. No NL3 union split,
new slot pitch, numerical operation or template is introduced. The actual
producer1554 proves the384-entry indexed score bound. Source end1590 stops
before the next HC_POST and layer entry.

check_expert.py tests64 legal identical/disjoint/overlap/edge/random top-k
profiles. Independent union/table order and combine slots e=rho*7+kappa agree;
actual HGI indexed effective addresses preserve raw score bits. Every static
expanded descriptor and actual rsel rows/slots/HBM expert index match the
original source after translation (29952 comparisons). Wrong pitch, count,
rtab, output e-mask and indexed input-base mutants are caught. These are native
address/selection semantics; MATVEC/FUSED arithmetic is not numerically run.

Dynamic expert A inputs were absent from the old static live-out inference.
--extra-live-out declares those bounded inputs explicitly. The pipeline_expert
variant adds5 commands and113856 boundarybytes, now689commands6250560bytes.
It passes the same2534778 canonical reads and172320 final boundarywords.
link_expert.py then builds6 real native DMA LOADs from its published sectors to
the expert input layout (33072words132288bytes); actual HGI DMA transport passes
against canonical source outputs and catches a wrong source epoch. This input
ABI composes; full numerical expert arithmetic/output retirement remains open.
Run check_expert.py, then link_expert.py to reproduce.

Whole programme inventory

Actual a122 decodes3916 records:40 IDX.UNION,80 IDX.KVUNION,120 expert-rsel,
160 attention-plan records,80 runtime-count loops and456 dynamic operands.
The neighboring emitter.json is stale (3715records516304bytes/hash7fe74f vs
actual3916records540064bytes/hasha1228b), so its byte offsets MUST NOT label
current source layers. programme_census.py refuses that mapping. An earlier
stale-offset census is retained as rejected_stale_segment_census.json ONLY;
its layer assignments are invalid. Historical emitter original six-row schedule
peaks exceed262144 in all40 transformer layers (300038..452534 words); that is
historical planning evidence, not current per-layer fit or an exact spill bound.
Full current layer map/phase policy/traffic still needs composition.

Physical scratch failure and capacity-valid alternative (later correction)

The old0x1F00000000 logical scratch is INVALID for the release: stack3 local
28GiB exceeds actual STACK_BYTES22500000000 (ds_native.py and DMA front/back).
Its logical word-version proof remains historical and is not physical execution.
The first moved candidate0x1D10000000 is also rejected: it is exactly COLB and
overlaps13 MTP column slots at128KiB each. Neither candidate is adopted.

vm_phase_shadow now refuses generated scratch/transfer extents beyond actual
per-stack capacity, even when the40-bit linear address itself is legal. Two
controls catch the old28GiB address and the first invalid physical sector.

A source-disjoint capacity-valid candidate starts0x1D11000000 (COLB+16MiB).
The final capacity_mtp_tail/link6 chain ends0x1D17600000:106954752bytes span,
inside the existing MTP half of DATA_WIN and above the actual1703936byte column
store. Weights skip DATA_WIN and HC uses its first256MiB. The source bounds are
ds_native.py DATA_WIN/STACK_BYTES and ds_mtp_kernels.py COLB/PMAX/BLK/CSTR.
This establishes capacity/disjointness against those declared occupants; the
scratch allocation is still explicitly UNRESERVED and not source-adopted.
HBM owner must reserve it against all active programme occupants before install.

Capacity-tail source replay still passes2534778 canonical reads,172320 final
boundarywords/5controls. link_expert.py now defaults to that capacity-valid chain
and writes expert_tail/ loads, preserving prior artifacts; native33072word input
transport and wrongepoch control pass. Use scratch-base0x1D11000000 in the
pipeline regeneration above. No actual numeric/RTL/G5/rate claim changes.
