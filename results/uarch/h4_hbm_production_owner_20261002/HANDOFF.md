Actual all96 PC0 publication to finite owner-controller G0

This additive successor consumes the actual completed PC0 journal SHA6b4f32a19ab71908e90d51d9e6d292d73932c8d8d28d974fefc92f5b859940de. A read-only raw scan verifies all738816 transaction lifecycles,96 framed journal hashes,384 actual exact-output receipts and246144 matching two-copy write-sector pairs against the source homes. Readback remains copy0 only. Software backing-visible events are not physical SRAM ACKs. PC0 does not qualify PC1..9 or the corrected PC10 collective.

The actual64-tile directed PC10 receipts join to the current home directory at512 source spans. Every required source home reference, SM, slot and RF address is exported. All512 directed source addresses differ from current RF homes: the control uses state-fragment backing. All64 directed outputs also differ from current homes: the retained fixture builds synthetic slot32 homes. No historical control is rewritten or claimed as a production translation.

OwnerController is an executable constructive FSM, not engine RTL. It reserves one SM and one bank credit, observes prior H1 drainage, issues and captures each32B bank word in order, fences both mirrors, accepts visibility/consumer completion, then retires on reverse grant. Stale/foreign owners, aliases, early publication, duplicate ACKs and unregistered physical contexts refuse. Full64bit generation and monotonically increasing40bit per-physical-SM dispatch sequence remain stored. The finite die inventory is explicit; rank-to-die translation is not guessed.

Actual H1 has one combined registered host ACK. Its adapter requires both copy write-enable acceptance observations plus that ACK handshake; it does not invent independently timed mirror ACK pins. The source-bound controller stores442 bits, including all322 request metadata bits and stale-return state. The provisional cell/compare footprint is600.9744um2 per entry, a subset of the existing5033.0112um2 connector reservation. Bank metadata fits within the already reserved576 request+reverse bits. This does not qualify the complete arbiter/mux timing or deployed whole service. Existing source L2 cuts retain Qwen12919/13013/12919/13013 and DS12919 each. No new geometry, route capacity, clock relaxation or area/rate credit is invented.

Finite arbitration is priced symbolically using actual contender inventory: H=drain+words*word_service+mirrored_ACK+visibility+consumer+reverse; wait=(N-1)*(H+1). All required external terms and N remain unbound. Positive source-pinned provisional terms yield conditional model bounds only. Software ticks, including actual108/read and128/write ticks here, never become hardware edges or qualified latency. All existing RF/I64/RMW/C0/provider costs remain charged once, added cost=0; whole-token latency is null.

Production physical bound calls=0. Next admission requires actual rank/die/SM assignment, matrix/frame/provider-to-L2 row/bank refs, source mirror acceptance/ACK connections, and bounded downstream service/consumer/reverse intervals. This is independent of numerical execution. RTL/P&R was not launched. Verification was local; PVE2/3 and live numerical jobs were untouched.

Replay from a fresh checkout:

    python3 -m unittest discover -s tests -p test_h4_hbm_production_owner.py
    python3 tools/h4_hbm_production_owner.py --out results/uarch/h4_hbm_production_owner_20261002/final_r5 --verify

Optional full raw-journal recheck requires the released producer artifact:

    python3 tools/h4_hbm_production_owner.py --out results/uarch/h4_hbm_production_owner_20261002/final_r5 --journal /path/to/exact/events.sqlite --verify

The final model and source inputs are archived by hash. Portable model replay uses a hardpinned reduced projection; it does not claim to regenerate released checkpoint arithmetic or the external SQLite file. Preliminary records and the17-test failure are retained with explicit scope in preliminary_scope.json.
