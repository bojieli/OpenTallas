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

All40 dynamic expert regions bounded (next source milestone)

vm_expert_entry.py now derives the footprint from each actual native block,
rather than hard-coded L14 intervals. It preserves original aliases and native
rsel semantics, includes implicit full36-ID I+L streams and table rows, bounds
indexed VM score reads by the actual384-expert UNION contract, and accounts for
e-based A AND O on the final w2 record (emask17; the first two use emask16).
Unknown union shape, row-table pointer and indexed extent fail closed.

All40 actual IDX.UNION entries through the third rsel SM and final collective
lower to bounded source components (expert_all/components.json + bytecode).
VM requirements are100416..255168 words, all below262144. The largest component
has6976words left; no other live values or numerical engine state are assumed
resident there. Inputs/outputs still require native publication around each
component before installation. New generic layouts coexist with the previously
qualified fixed L14 layout; prior artifacts are not overwritten.

check_expert_all.py compares33564 actual expanded record/slot/descriptor and
indexed payload cases across3 profiles per component, retaining all source
arithmetic fields. It also refuses3 unqualified dynamic mutants. The existing
64-profile representative check still passes on the new derived layout101152.
This closes the expert-address/selection footprint obstacle for ALL40 regions,
not full numerical replay, whole-token liveness, mutable-HBM execution or G5.

Conservative source-complete canonical backing stream

vm_canonical_stream.py now lowers ALL3916 actual a122 source records through
END. One2MiB canonical HBM backing image retains the original full VM namespace.
Static operations execute ordered3-row workspace phases; each expert block stays
one6-row component, and each attention plan stays nativeNL3. Native whole-sector
loads/stores keep canonical source order rather than trying to retain the old
six-row overlap schedule. All source arithmetic/template/rounding fields remain.

The conservative artifact is54176 native commands,421238848 boundarybytes, and
max255168oldVMwords. This intentionally gives up overlap and has large unpriced
traffic. It is a complete source-address lowering vehicle, not a viable-rate or
physical release claim. Actual current DMA coverage/VM banking is unqualified;
stack3 backing is a source-only candidate and remains UNRESERVED.

Additional failures handled: standalone nativeDMA.FENCE/STORE and CTL.ACCEPT/
TOKX require explicit support; ACCEPT/TOKX VM pointers must be relocated, not
copied above262144. The final SM3910→ARGMAX3911 is a STREAM producer/consumer
pair. Inserting an ALL-unit drain between them could alter source protocol or
stall a finite stream. They now stay coupled inside each3-row phase and retain
the original consumer wait0. This is a preserved source contract, not a measured
RTL deadlock claim.

check_canonical.py proves the address/version mechanism by interval translations
rather than hundreds of millions of per-word tags. Native loads establish source
address identities; source/physical writes invalidate prior aliases; reads and
whole-sector retirements must see the right remaining translation. It checks
20842 static addresses, all40 previously-qualified dynamic expert components,
all3916 source records/row order, and six coupled head stream rows. Wrong backing
load, missing load drain and altered stream-consumer wait controls are caught.
Numerical operator execution, mutable-HBM execution, actual backend namespace,
initial canonical-image publication, scratch authority and full schedule remain
OPEN: whole_programme_executable=false/full_programme_fits=null.

PYTHONPATH=/home/ubuntu/OpenTallas/tools python3 tools/hbm_next/vm_canonical_stream.py \
 --image /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r \
 --compiler-tools /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools \
 --backing-base 0x1D11000000 --out-dir results/tok_hbm_1030/canonical_all
python3 results/tok_hbm_1030/check_canonical.py

Optional grouping reduces the conservative source vehicle's traffic

--group-static commutes only independent row groups. It checks actual VM RAW,
WAR and WAW inversions between later group0 and earlier group3 operations,
including attention-plan reads; DMA, control and stream operations are explicit
boundaries. Source regions are split further when the allocator cannot fit.
No numerical operation changes, and the default remains the ungrouped stream.

An initial grouped preparation failed the address proof: emitting all prefetches
at group entry ignored the allocator's workspace lifetimes (source147504:147632
unavailable at workspace0). This failure remains in group_failure.json and its
scratch candidate. The fixed compiler emits external loads at their actual
before_source_record anchors. No passing verdict replaces that failed candidate.

The optional canonical_group_anchored result covers all3916 source records as
40536 commands and383876096 boundarybytes:25.2% fewer commands and8.87% fewer
bytes than the conservative baseline. Max VM remains255168. The same20842
address/version checks,40 expert components and6 coupled head rows pass, plus
wrong load, missing drain, stream-coupling and known reverse-source-group controls.
Current backend stack/VM namespace, scratch authority, initial publication,
numerical RTL and full source calendar are still unqualified. SOURCE ONLY.

Compile-time resident copy elision (no runtime cache or new RTL)

vm_static_cache.py tracks opaque value identities through the actual fixed
stream. Native copies propagate identities; arithmetic assigns fresh identities
over conservative native write bounds. Expert writes use all possible declared
source output ranges, not a guessed union profile. A known static linear HBM
body write preserves backing identities only when its exact address range is
disjoint; unknown/overlapping writes invalidate them all. All288 expanded body
HBM write rows in this source are disjoint from the candidate backing.

A LOAD or STORE sector is removed only when its destination already holds the
exact same opaque source value identities; changed runs retain real whole-sector
native DMA. All arithmetic/body bytecodes and all explicit drains remain.
This uses existing VM contents across phases, with no hardware cache, allocator,
credit, speculation or new instruction. The flag is a separate opt-in source
post-pass, not an installed release programme or source-calendar claim.

canonical_cached_disjoint contains40176 commands and361623424 boundarybytes,
saving22252672bytes(5.8%) and360commands over grouped source. It completely
removes487 DMA commands and splits some partial hits into smaller real commands.
29345 copy-induction checks establish identical affected ranges after every
transformed copy; final workspace and backing identity arrays match exactly.
Body bytes are checked byte-identical. A skipped required LOAD and wrong STORE
address control are caught. The first control attempt targeted copy ordinal0
(which was a STORE), so no LOAD was corrupted; the control was fixed to target
the first required LOAD, and now fails as intended. No failed source verdict is
promoted from that harness error.

The proof is copy/address exactness with unchanged opaque arithmetic, not
numerical RTL/G5, selected backend/stack coverage, scratch authority, actual
HBM execution or a token rate. Those holds remain unchanged.

Optional resident placement reduces copy traffic further

--retain-static is an opt-in placement preference for the source compiler's
existing workspace allocator. An object with external inputs may reuse a current
physical range only when ALL its external value identities match the canonical
backing at one affine offset. Hint objects are placed first, still respecting
actual lifetimes, aliases,8-word alignment and262144-word capacity. Infeasible
preferences or illegal native array encodings fall back to the old allocator.
No runtime allocator, cache tags, new instruction, RTL or default change.

This placement initially emits41888commands (1352more than the grouped baseline;
some SU row arrays become scalar commands). Both candidates keep681 static
shared-weight SM arrays and120 expert-selected SM arrays: no extra weight-stream
issue is introduced. The unchanged logical-source proof passes20842 addresses,
40 expert components and6 head stream rows with4 negative controls.

Applying resident copy elision gives canonical_resident_cached:
37226commands,319227648boundarybytes, max255168VMwords. Against the original
grouped40536commands/383876096bytes this saves3310commands(8.17%) and
64648448bytes(16.84%). Against copy elision without placement preferences it
saves42395776bytes. All29345 transformed-copy induction checks and final
workspace/backing identity equality pass; required-LOAD/wrong-STORE controls
are caught. Body bytes remain identical to the resident-placement baseline;
expanded arithmetic fields equal the original actual3916-record source.

Reproduce the intermediate baseline rather than storing another redundant
full manifest:
PYTHONPATH=/home/ubuntu/OpenTallas/tools python3 tools/hbm_next/vm_canonical_stream.py \
 --image /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r \
 --compiler-tools /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools \
 --backing-base 0x1D11000000 --group-static --retain-static \
 --out-dir results/tok_hbm_1030/canonical_resident
python3 results/tok_hbm_1030/check_canonical.py \
 --base results/tok_hbm_1030/canonical_resident
PYTHONPATH=/home/ubuntu/OpenTallas/tools python3 tools/hbm_next/vm_static_cache.py \
 --stream results/tok_hbm_1030/canonical_resident/stream.json \
 --source-image /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r \
 --compiler-tools /srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools \
 --out-dir results/tok_hbm_1030/canonical_resident_cached

This is still a source-only candidate. Actual provider/stack/VM namespace,
scratch authority, initial image publication, numeric RTL, physical calendar,
cycle/rate composition and G5 remain open. Byte savings are not a token-rate
measurement or permission to install the programme.

Compact STATIC LOAD counter capacity budget:
load_provider/target_capacity.json records why existing128-entry MODE1 loops
and1024-entry ROLE literal calendars do not generate LOAD address progress.
load_provider/effective227_contract.json supplies exact adapter fields, ordinary
VM mapping and dated window handoff. load_provider/counter_budget.json prices
actual full40-layer3916-record token source, inserted copies only:43117008 U32
words +12528 setupedges under chosen one-global-counter serial implementation.
At833ps the counter-only35.926903488ms ceiling is27.8343token/s; this is not
qualified performance or an unavoidable floor for coalesced/parallel designs.
No current programme/model includes this spill tax. Original dynamic LOADs,
STORE/arithmetic, window service, physical commit, scratch/stack authority and
full-calendar installation remain open. Window-policy release conservation now
also counts2 terminal owned windows; all27907 acquisitions require one all8leaf
release each. No RTL/P&R/target allocation is changed here.

Window-safe caller programme (source only):
load_provider/window_programme.py groups only adjacent LOADs with disjointVM
outputs, splits effective227 runs at actual PC-window-half boundaries and
preserves every source command anchor by its raw stream offset; precisely
12543 body/drain anchors plus12155 STORE anchors. The95313splitdescriptors
retain all43117008words and27907all8fill/release pairs, with2761validepochhits.
95313address/ownership/route checks PASS, staleepoch/wrongVM/missingrelease
controls caught. --program-out writes the complete caller event programme;
the checked-in JSON stores its digest, count and representative events.
Each run exposes sourcePC and destinationbank/quad mapping formulas to support
future real collision-free issue planning; no parallel hardware is assumed.
Symbolic dependencies keep taggedPHYfill before datedstep, actualVMcommit before
sourcebody, STOREcompletion before invalidation and actuallastconsumer before
release/reuse. Fill/commit/physical/done dates remain open. Revised singleword
counter+splitsetup43212321cycles=35.995863393ms@833ps. Proven future count8
coalescing would yield5389626sectorcommands+95313setupedges=5484939cycles
(4.568954187ms), before windows/sourcework/commit; not current implementation.
