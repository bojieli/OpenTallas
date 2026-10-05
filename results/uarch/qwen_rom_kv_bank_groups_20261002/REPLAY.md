This additive submission is based on main
`6bb3ac9e7b05185e3e87ca0cdbe2dd8df1909359`. Parent owns cherry-pick/merge/push.
The minimum dependency is the previously received
`101a084a822dc1f149a8852704648fd317c632c9` (which includes its earlier KV
prerequisites), or its byte-equivalent clean rebase
`0d31a6ffd4ae31841b6a860e20ca88517264f9a0` on that main. Do not cherry-pick
both predecessor versions. The new commit is additive on that predecessor;
parent intake already containing101a needs only the new commit.

Final authority: `model-r4.json`, `admission-r1.json`, `kv-tests-r5.log`,
`persistent-tests-r1.log`, `peer-context-tests-r1.log` and the pin manifests.
Prior models are unadopted drafts. The initial protocol exception and the
read-only versus read-plus-write assertion FAIL are retained, not overwritten.
No docs, RTL or pinned originals were edited. No hardware build, second
numerical position, remote job, optional sweep or live-job mutation occurred.

The single minimum necessary candidate is8 return groups of4PCs per stack,
4 column32B command paths per stack and6 global64B fill lanes. The32 actual
context1R1W RAMs per stack are retained without replication. Aligned16-sector
blocks have one group under the actual XOR PC hash; group=PC>>2 and
commandpath=group>>1. Tile%6 partitions all1536 real destinations into256 sinks
per lane; exact fill demand per layer is10912 beats on four lanes and10880 on
two. The existing7.070976x deficit and50owner/6fill/4command requirement are
referenced, not replaced with a duplicate artifact or blanket50owner copies.

The owner successor retains12-edge lookup/output latency and proposes a
registered context capture at+1. Source macro SS clk-q is455.32054894758ps,
leaving484.67945105242ps for setup/route at candidate1GHz and60ps uncertainty.
That capture is unqualified. The actual native PC provider additionally has
one rd_pending record, a fixed16-record serial scan and a28-edge read interval
lower bound:1.0304ms per token. Four command wires do not remove it. The model
prices64 pending records/PC and frozen16-record lookahead, expanded64-row
return-pointer use and joint namespace/duplicate/remaining_PC controls.

One shared physical12-bit namespace per stack is retained. Allocation and up
to8 distinct final-tag retirements must update live_tags atomically.16 burst
credits/group remain leased through matching consumed grants and reader drain,
including quarantine;64 actual return rows/PC and32 flight/output credits/group
are finite. Four stack-matched bursts form one cohort so V quarters assemble
in the same central word.128 cohorts reserve at most4096 central words, the
same total as the predecessor4*1024. Direct cohort/word slots avoid a new
4096-way search. Central quarter-write selection and assembly cell/collector
repricing are included; no free four-write RAM or four private4096 pools.

Conditional demand at context8192/position8191 is150690816 offchip read bytes
plus156672 closing-write bytes per rank/token. The existing KV/HBM byte bound
is replaced once; calibrated compute has no HBM wait cycle debit to add again.
Actual two-K-tail/current-V-forward residence and release remain policy gates.
This is not a new compulsory whole-layer refill or full36-layer residency.
The full36 useful-residency minimum additional131.504169984mm2 is explicit.

The complete36-layer address-only port reservation retains sequential
arithmetic, two54-row leased windows, all four stack demands,12-edge owner and
39-stream-edge request/response/reverse links. Grants reserve shared bus slots
after masked visibility and reverse traversal, not at earlier DATA acceptance.
Current-V publication waits for the QKV producer prefix; future payload is
never fabricated. Prefix/matrix work may overlap historic next-window service
only conditionally. Attention starts after required fills/current-V readiness;
local window reuse waits for attention drain and all reverse grants.

Ideal port lower costs total327.36us. The one constructive FIFO-cohort
reservation costs336.659966667us through36 layers and339.296633333us if retained
non-layer costs are exposed, exceeding333.333333333us even before actual PHY
bank/row/refresh/turnaround and CDC/route costs. This order's miss is not a
universal lower bound on every possible ordering. Actual sustained PHY rate
remains unknown;113.135616GB/s/stack is required, not claimed supplied. Source
PHY still has one request input and32 response ports. Source timing parameters
are pinned; port reservations using minimum REQ/RSP/CL costs do not qualify
bank/refresh/maintenance commands or actual sustainable service.

Known service cell/macro reservation is8.74225513008mm2, plus the existing
0.0656627067mm2 parent-interface contract. The named747.6521730048mm2 baseline
join remains missing. If all those services and fourPHY footprints are outside
it,13.02236127106mm2 remains before unknown physical services and routes. This
is not floorplan fit. Additional48 actual64x512 response-holding macros,
central assembly, all6 fill roots and replicated domain collectors are priced.
No inherited service reservation refund or extra PHY bandwidth is credited.

The reused sharedM6/M8 corridor requires6925 tracks against1360 nominal
capacity, a5565 deficit. At the same pitch/layer reservation,492.734117647um
is required versus96.768um. Uniform widening produces48.234375529mm array width
against26mm and827.643944285mm2 added area. This rules out reusing that corridor
for this configuration; separate legal channels are not yet allocated. It is
not a proof that every different topology is impossible. No3k or hardware
adoption follows.

Exact independent replay from a clean worktree containing this submission:

```bash
python3 -m unittest discover -s tests -p 'test_qwen_rom_kv*.py' -v
python3 -m unittest discover -s tests -p 'test_qwen_rom_persistent_kv*.py' -v
python3 -m pytest tests/test_qwen_rom_local_parent_composition.py tests/test_qwen_rom_owned_ready_context.py tests/test_qwen_rom_parallel_owner_screen.py -q
python3 tools/verify_qwen_parent_context_evidence.py
python3 tools/verify_qwen_kv_bank_groups_evidence.py
replay_dir=$(mktemp -d /tmp/qrom-bank-group-replay.XXXXXX)
python3 tools/uarch_model_qwen_kv_bank_groups.py --parent-ref 6bb3ac9e7b05185e3e87ca0cdbe2dd8df1909359 --result "$replay_dir/model.json"
cmp "$replay_dir/model.json" results/uarch/qwen_rom_kv_bank_groups_20261002/model-r4.json
```

Expected71 KV tests (13 new),15 persistent-source tests and14 peer pytest tests:
100 focused tests PASS.57 source pins and28 immutable originals verify. Model
replay must be byte-identical. Original capture SHA256 remains
`d71d6d8a6d724b8f48c77ec90dd9027935d5d8f90d50b54be3a941b680f9beab`.
The final verifier checks source parent blobs, current implementations, every
packaged result hash, original capture and36 rows' read/write receipt debits.

Next necessary output is one named legal channel/shoreline PHY/controller/
clock-slot receipt for this8/4/6 configuration, with source finite64-pending-PC
service and Euclid's actual producer/demand journal joined. Popper, Kepler,
Euclid, Maxwell and Ampere contracts are individually addressed here. No
callable peer messaging transport is exposed; these are ready for parent relay,
not claimed delivered. Current source and physical admission remains FAIL.
