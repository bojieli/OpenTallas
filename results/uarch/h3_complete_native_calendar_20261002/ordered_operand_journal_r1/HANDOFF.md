Actual operand-span/journal admission successor to ba0c1ba06

The r35 rich manifest names:
  /tmp/kepler-ds-r35-rich-provider-state-manifest.json
  /tmp/kepler-ds-r35-rich-provider-state-manifest.journal/events.sqlite
The latter directory is absent at inspection. ds_hbm_payload_manifest_r35.py
only writes a manifest path. Provider.__init__ calls JournalBudget first;
JournalBudget creates the directory/database before checkpoint/view validation.
Thus bindings are not needed merely to create the directory. Its absence does
not establish a specific runtime failure, and an empty database would not prove
successful execution. No full driver/provider construction was launched here.

Kepler: export the ACTUAL journal_id and [start,end) event slice for each
received call, plus concrete allocation base/window offset, active source
version/lease and accepted full tag/generation identity. Disk values are zlib
JSON; sequence order is scoped to journal_id, not database-wide PC order.
Sagan: bind those calls to CURRENT c65a584c... native source instructions and
current provider/catalog identities. The old ParentProviderJoin catalog cannot
silently stand in for corrected eight-group/window source. Exact required call
fields and existing checkpoint/state/payload paths are recorded in
journal_path_and_join_handoff.json. No agent message was sent by this tool.

verify_ds_operand_journal is an additive receiver validator, not another
movement exporter. It resolves retained opcode/attrs/result shape/SSA role and
actual PC/rank/template membership. Each explicit <=512B operand window fits a
concrete allocation window and a 64KiB shared tile. It checks every 32B sector
accept -> backing visibility/capture -> consume -> reverse credit -> matching
grant, finite tags, strictly increasing recycled-tag generations, monotonic
software ticks, exact span coverage, and no premature reuse. Optional physical
translation must match rank/SM/version/lease, extent and address width; absent
translation stays UNKNOWN. A supplied mapping is software input, not proof of
an installed HBM connector. SM routing and actual lease acquisition/release
journals remain outside this per-call proof; a nonempty lease is never promoted
to whole-program lease closure.

The retained actual_disk_operand_control.json.gz uses the pinned real r21
SectorProvider with r30 DiskEvents/JournalBudget. One 512B write is 16 accepted
sectors, 8 shared64 transactions, maximum one live tag, all reverses drained.
This is a constructed software positive control, NOT actual DS PC18 arithmetic,
released-checkpoint execution, or a production physical address map.

Run:
  python3 -m unittest discover -s tests -p test_h3_complete_native_calendar.py
  python3 results/uarch/h3_complete_native_calendar_20261002/ordered_operand_journal_r1/replay_control.py

66 tests PASS in19.366s; control replay PASS. Negative controls reject missing
accept/last reverse, stale/recycled generations, changed source attrs/typed span,
wrong source PC, allocation/shared overflow, released lease, exhausted tags,
stale physical lease, short translation extent and address-width overflow.
Source snapshots and the external manifest snapshot are retained with hashes;
replay does not need Git or any checkpoint/image payload. This adds zero native,
C0, provider, RF mirror, I64 or W15 cost and does not repeat the large calendar.

Production shared calls closed:0. Remaining UNKNOWN:193316. The whole-token
latency remains null. Full bounded operand continuation, actual lease events,
installed physical map/current C0 admission and all production call journals
remain required. W15 wide-rate credit stays absent; STALL1 remains untouched.
Third-party matched agentic per-request median remains conditional/unavailable
in the audited candidates; prior provenance evidence is unchanged.
