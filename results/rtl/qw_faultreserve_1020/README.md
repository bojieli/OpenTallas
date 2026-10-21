# Fault cover source reservations and channel-capable MST

Source: exact `dv2f20g5rf/src/tools/qwen_split/fault_emit.py` snapshot, over
973335ec2. The paused snapshot already implements CAP360 cover roots and
base-relay-box reservations; the new source keeps those changes explicitly.
The generator remains the immutable actual rf source, not a fresh branch export.

The terminal rf edge flt_t_c16_W5_2_g2 had endpoints (3376.416,13409.292) ->
(2957.568,13399.548), length428.9um; only3/36 endpoint sites free and no reachable
midpoint. Its warn twin reached post then failed on inputless flt_root_dvs_W1.

Opt-in structural change:
* OT_SPLIT_FAULT_SAFE_MST=1 excludes intermediate root edges with estimated
  pin spans395..650um from the Prim topology. These crowded-face edges would
  require a local landing but have no verified reserved landing site. The tree
  chooses a different parent, with full standard relay search. This is a
  conservative topology policy; it does not claim every such edge impossible.
* OT_SPLIT_FAULT_RESERVE_SOURCES=1 constructs bipartite matching from actual
  fullshape source bits to otherwise inputless roots. A unique source witness
  must be within395um of the actual f0 pin on the SAME clock trunk. Witnesses
  are consumed first; an unmatched root fails without pruning or waiving it.
* CAP360 variant A preserves cover geometry; CAP320 variant B requires a
  closer source cover and prices the additional roots through GEN counts.

Analytical cost before GEN: each root is21.6x21.6um (466.56um2) and N+4flops,
N<=16. Capture source matching adds no hardware. MST parent changes preserve
node count but may add forwarded relay and landing frames. CAP320 can add
cover roots. Each fault-OR stage is registered sticky input -> reduction ->
output; root observation delay is3cycles per node plus actual forwarded-hop
and landing stages. No data schedule/throughput change: this is observation
only. Actual node/frame/flop counts and path depth must be collected from each
candidate before adopting it. Static fault propagation has no backpressure.

Safety checklist: pins/reach/clock are checked by existing GEN on full actual
placement (405um wire limit unchanged); fanin<=16; no runtime storage array;
base data relay boxes remain reserved; fixed-latency regional landing rules
unchanged. Native synthesis/CTS/GRT/SS/FF are NOT performed by this GEN-only
campaign. No physical closure claim. Crucially root_sink remains OPEN because
sys_face has no obs_fault input: even GEN PASS is NOT final fault coverage.

Fleet records: pending_results rows CODEX-QW-FAULTRESERVE, directories
/srv/opentallas-scratch/claude/codex-qw-faultreserve2210a and ...2210b.
Each carries source.json exact file hashes and a private fullshape source copy.
