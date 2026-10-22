# Bounded L2 producer and native carriage replay

Engineering bench; no result is qualified by this source commit alone. The
immutable fleet source root is gold1:
`/srv/opentallas-scratch/claude/codex-s81-cap-sukv-2130/src`.

The two real frames are `u_f_2L13` (landing 2) and `u_f_2R10` (landing 4), owned
by source slice `u_s_2N`. Their real L2 checkpoint ROM weights produce ordinary
WKV values 0 through 7. The reference values are scoreboard inputs only. The
only vector data driven at an arithmetic boundary is the checkpoint input at
the real XS gather input, as in the existing bounded producer bench.

CAPc5r writes these values to source VP native rows 2 and 3. Its real south
D4/K2 chunk landing and the real DL4 leaf relay are present. Native RDOUT then
uses XRT and RSTOP to carry one pair over an adjacent horizontal connection to
`u_s_3N` rows 692 and 693. The test connection adds zero wire edges; physical
route dates and mapping to a production clock epoch remain open. A separate
GK command loads actual L2 KV normalization gains through native CTL writes.
No full KV/CN/IK/CP arithmetic consumer is launched from this eight-value cut.

All component clocks have an explicit common phase. Source-relative commit
and read sampling are observed at actual VP SRAM ports. The destination VP
and KV leaf use the production extension-port wiring; unused arithmetic
functions of a complete beat leaf are outside this cut.

The selected element source is SHA256
`517e501dd6a505871302dc93cf31b87f9dc5cfcc771a9564c07b58b662014d96`,
Git blob `90aa3d484c35951694b793faed243ca027c893aa`, CPR0. The current 4233
CPR0 generation result is preserved separately, along with the original stale
schedule rejection. No CPR1 physical view is adopted. The full fleet source
hashes are recorded in each output identity JSON.

`run_r1` stopped before simulation on a missing VP hcpost dependency; `run_r2`
adds the exact existing helper files. Raw monitor lines retain SRAM macro
masks, row addresses and the actual observed clock edge. Token/S81 owns
normalizing those events into row and gain lease manifests. Missing ranks,
other operand rows and future gain consumers remain explicit gaps.

The prepared single successor `run_r3` adds four actual `dsfd_dvland_276`
D4/K2 modules at the adjacent inter-slice seam, using the die owner's declared
G = R0 relationship at the landing core. Its bench reset calendar releases the
external kit reset two edges before that core epoch. These are component
clock and reset stimuli, not measured physical clock arrivals. Physical flight
and absolute production epoch remain open. This successor also initializes all
four GK descriptor rows (528 through 531), observes source VP `lo_v` read
readiness and destination KV dispatch, and enforces positive and causal
negative simulator outcomes. The preceding zero-wire `run_r2` remains intact.

The XS output to frame input and frame return to CAP input are direct component
boundary connections; frame-chain and frame-to-CAP physical route ages are not
asserted. The native control origin is the common bounded replay clock, with
real XS issuer words at its port and native CTL words at the RSTOP port. It is
not mapped to a production seqhost epoch. `u_f_2L13` uses CAP W2 and
`u_f_2R10` uses CAP W3 in the corrected successor; the original E0 connection
for R10 in r2 is retained only as an unqualified predecessor.
