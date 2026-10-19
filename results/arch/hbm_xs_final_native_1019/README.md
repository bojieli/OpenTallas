# XS14.1 terminal gates: HOLD for structural redesign

This is read-only pickup of `claude/smhxs-safe-ab-1019@48f182692`.
No new gate, synthesis, RTL, REVIEW or submission was created. All three original
clients ended. Their immutable complete gate JSONs/logs are preserved here.

| Kit | Gate verdict | TT/FF boundary spread ps |
|---|---|---|
| kmr | FAIL | 125.1 / 115.6 |
| c32 | FAIL | 178.7 / 156.9 |
| c32k | WARN | 39.6 / 38.0 |

c32k has TT placement-RC setup +108.895 ps, hold +47.953 ps, reg-to-reg
setup +182.1 ps, trial GRT overflow 0. Its 26,146 clock sinks and insertion
556.1/449.7 ps are guidance, not independent rejection criteria. This does not
qualify routed timing or a neighbor-matched native boundary.

Actual geometry independently FAILS. Original IOP `gate_dump.json` SHA256
`da55ebe67f8611e9ae79e031d4215a187eebdd33ba7f825931de39d123ed9f2d`
contains top signal/clock contacts spaced 0.096 um in long contiguous runs:
S 2,052 adjacent gaps, N 1,612, W 822, E 18. Thus the headline whole-face average
does not describe local contact density. Supply contacts were excluded explicitly
by their exported POWER/GROUND roles; the remaining S count is 2,069.

Every SRAM also exceeds the full-face 6 contacts/um rule:
seven `32x128_m1` macros have W/E 199/198 contacts over 20.790 um,
9.572/9.524 contacts/um. Four `128x256_m1_r2c2` macros have 410/409 over
41.040 um, 9.990/9.966 contacts/um. Macro lattice flags, rectangles and exact
counts are in `geometry.json`. GRT zero and track-access PASS cannot waive this.

The original remote run is
`ot-agidock128:/srv/opentallas-scratch/claude/ref_gate/smh_xs_ring_c32k_1019-20261019-115411`.
Actual 4_cts and 5_1_grt ODBs remain there. Original archive SHA256 is
`317de9f17575862f7f25a53ca2135cc36586afb25ac4c673dd815fbdaeeecc26`;
source manifest SHA256 is
`2dc3be7f536b198e2e70864675fd149d26bcbf72b6cd330c806feaf6ca128ded`.
The full source/consumed/helper bindings and image identity are in the gate JSON.

The full raw 4_cts OpenDB export has 116,757 cells, 77 native masters, 112,965 nets
and 4,545 top ports, with NO graph exclusions. ODB SHA256 is
`9783679fcb24b771ccc0799bb111cf07c09e18eb6303c27fab0c3486ece5276e`.
`raw.json.gz` retains all native MTerm roles, PG, ties, disconnected pins and
connections. Exact library bytes, original raw JSON and manifests remain at
`ot-agidock128:/srv/opentallas-scratch/claude/hbm-xs-final-native-1019/out`.
SHA256SUMS and native-summary.json bind those bytes. The five real ASAP7 TT
libraries were copied from the exact pinned gate image; SRAM TT models came
from the original immutable gate snapshot. Unused FAKE library files remain
hashed but are not selected by the strict parser.

The strict oracle from `969965293` REFUSES the actual SRAM Liberty bus:
`unsupported bus in ot_sram_1r1w_128x256_m1_r2c2`. This refusal is preserved in
native-summary.json. No name-based clock exclusion, scalar surrogate, invented
macro clock or direct-fanout substitute was used. Full BUF/INV-transparent native
fanout and registered-boundary qualification remain OPEN, not PASS. The first
export attempt succeeded but library copy missed NLDM/; that command exited 1.
Corrected collection ended exit 0; diagnostic replay ended exit 0 with REFUSED.

SAFE checklist: pins HOLD (actual registered ownership not yet certified);
reach HOLD (no complete logical stage paths); fanout REFUSED; depth gate-only
288.4 ps, native scope OPEN; storage geometry FAIL; floorplan contact geometry
FAIL; clock boundary spread PASS but parent matching OPEN; schedule source says
zero new edges, independently composed parent/source guard remains OPEN. Real
PG/contact/via/OBS and detailed-route electrical/timing checks remain OPEN.

Next work requires a model for truthful wide-pitch SRAMs and legal full-face
pin distribution, priced outline/latency/parent fit, plus an explicitly reviewed
Liberty bus adapter before all-driver qualification. Do not submit c32k or tune
the same failed geometry. ROOT critical PNG review is not requested for adoption.
