# collft FF5 eight-entry clock architecture proposal

Current result: **MODEL ONLY, NOT GEN/BUILD QUALIFIED**. Eight proposed actual
RCLK input ports and seven existing forwarded FCLK owners have a concrete named
buffer forest, actual FF clock-pin geometry, finite whole-body/row packing and
TT/FF NLDM screens. No original FF/data/reset state or cycle changes. No ODB was
written and no P&R, CTS, STA or parent activation occurred. A0 stays untouched.

The actual FF5 3_place ODB and every failed alternative are preserved on intel2:
`/srv/opentallas-scratch2/claude/codex-collft-ff5-0336/`.
This proposal's scripts/full census/models are in sibling
`codex-collft-clock-0336/`. Current packed source is
`tree_packed_actual_pins.json.gz`; every per-root slice names the ACTUAL input
port (including scalar vector-bit spelling) and actual partition module.

## Diagnosis and choice

Actual FF5 has18,501 sequential clock sinks. RCLK9,428 still all trace `clk`
at pre-CTS PLACE: there are zero clock cells. The six published grid BTerms
produce NEAREST projections3075/806/1649/358/2857/683, not six installed trees.
Six times1500 leaves428sinks uncovered even with perfect redistribution.
`geom_rules.clock_metrics` traces BUF/clock cells back to input BTerms; ordinary
buffer names cannot create extra roots. The current recipe's cap3000 also
conflicts with the1500 gate and must become1500 for a new candidate.

Seven is only the arithmetic lower bound. Preserving the16large functional
cohorts (four CA modules623..625RCLK sinks and12FT stations548..550) needs at
least eight entries: any three of those cohorts exceed1500. The chosen proposal
uses two entries per populated station band, retaining every cohort as a unit:

| Proposed port | Local x/y um | Actual RCLK sinks |
|---|---:|---:|
| clk |365.024 /17.312|1290|
| clk_t1 |119.968 /17.312|1251|
| clk_t2 |119.968 /331.168|1099|
| clk_t3 |365.024 /331.168|1135|
| clk_t4 |119.968 /662.368|1098|
| clk_t5 |365.024 /662.368|1138|
| clk_t6 |119.968 /976.288|1106|
| clk_t7 |365.024 /976.288|1311|

The six existing clock pin positions change and two inputs are added. For
coll_f1 origin[777.6,6445.44] and coll_f2[777.6,7439.04], bothR0, this needs four
additional REAL die tap bindings and six moved endpoints per instance. The
current safe graph has only six bindings each; do not reuse their node IDs for
new entries. ROOT owns the new source/plan/provider/target/bind event, preferably
batched with its native PHY change. Data/forwarded pin positions remain unchanged.
Four proposed new BOOT flops are not in this native checkpoint: their actual
source/control integration must refresh the census/model; current max1311 has
capacity margin but is not their qualification.

The direct-input radius alternative is retained as fallback only: canonical
density clustering over the exact RCLK-only inventory gives22nonempty taps,
max1266sinks and189.486um radius (target1500/radius200). FCLK inventory is
excluded from that RCLK clustering. It is not the preferred source expansion.

## Actual geometry and model

Read-only native ODB census captured18,501 actual CLK ITerm getAvgXY points,
139,359 ALL instance bodies,63,871TAP/endcap bodies and3648actual rows.
Maximum FF-body-centre to actual CLK-pin displacement is0.652um. Five buffer
master dimensions came from that same DB. Model-only finite packing blocks all
actual bodies and ALL pre-anchor software intervals conservatively, including
protected .4tails. Every8,436 proposed clock bodies fits actual54x270DBU
row/site/orientation footprints; maximum centre displacement29.7um. Nothing in
the original checkpoint moved. This is a packing plan, not an installation
certificate; exact runtime all-body checks remain mandatory at installation.

There are4,948RCLK buffers (including1112shared branch-balancing cells) and
3488FCLK buffers. Buffer masters are unconditional non-inverting BUF6f/8/16f/24.
No ICG/clock mux, tri-state buffer, inverted clock or new sequential stage is
introduced. All18existing falling-edge DFFLQN RCLK sinks remain falling-edge;
Liberty clocked_on is !CLK at both corners. Other sinks retain rising edges,
including async set/reset cell semantics.

The first naive tree failed slew up to201ps: a count-only leaf put sparse remote
controls on one8-sink net. Leaf radius<=30um, BUF24 internal branches and explicit
<=90um branch subdivision fix this cause. Unbalanced remote branch depths then
failed related-clock estimates by407/343ps within an entry and447/377ps across
entries at equal source phase. Pure joint TT/FF sibling-branch sizing adds1112
named shared clock stages; it does not fit measured timing or per-pair pads.
FCLK base trees are retained when balancing the RCLK forest.

Current actual-pin/packed model, at EXPLICIT20ps incoming slew and equal RCLK
input phase, predicts:

| Screen | TT ps | FF ps |
|---|---:|---:|
| RCLK same-entry related bound |47.011|35.504|
| RCLK cross-entry related bound |54.026|41.534|
| Same-owner FCLK related bound |46.194|39.171|
| Maximum electrical slew, all15owners |33.582|31.964|
| Absolute RCLK insertion range |680.176..741.253|521.986..570.540|
| Weighted absolute RCLK insertion |701.271|538.371|

These are geometry/NLDM estimates, not measured timing. FF caps are actual TT/FF
Liberty CLK capacitances for all four native sequential masters. Wires use the
existing planning RC .014812kohm/um and.154233fF/um; buffer interconnect points use
the compiler cell-centre convention. Passive input-to-first-buffer wire is
included ONCE, with per-corner proposed port load in per_entry_frames.json.
Via RC is not extracted. Same-source input phase/slew remains an assumption.
The predictor's raw valid_for_build_gating flag means table calibration only;
top-level build_qualified remains FALSE pending the listed physical/clock gates.

Actual data/reset graph yields54,854sequential pairs:11,042same-entryRCLK,
7283cross-entryRCLK,27,339sameFCLK and9190different-family. Conservative leaf-span
bounds above cover the first three classes. **9190cross-family pairs remain
UNPRICED**, requiring actual forwarded sender/export/wire phase, input slew,
LCA/CPPR and the production CA/reset count contract. No equal-source fiction is
used for those pairs. The old nominal250/202.5ps frame is not the new insertion:
weighted increase451.271/335.871ps is real die-frame cost, with no SDC compensation.

## Forwarded ownership, source adoption and remaining work

Seven existing FCLK input owners retain exactly their actual sink sets:
crec_rx_s1=2218,rx_s2=2218,tx_s1=2226,tx_s2=2222,fltk=34,fltv=130,
cland_dn_0=25. None becomes a RCLK grid tap or helps hide its load. The current
clock_tap_sinks gate explicitly applies to the named grid family, not those
forwarded clock names. Actual forwarded local trees/source waveforms still need
normal functional/electrical qualification; their distinction is not a generic
sink-limit exemption. Source period833ps,60/25ps uncertainties and the18falling-
edge sinks must remain explicit in later STA.

Forwarded output source taps must follow their actual final station clocks:
RX1/RX2 final stations suggest clk_t6; TX1/TX2 final stations clk; fltk/fltv top
stations clk_t7. These are source proposals, not adopted generated-clock/SDC
changes. cland_up monitor export remains UNRESOLVED until its actual FSTART/
ready/clock branch and sender interface are bound. Actual die source phase and
output-clock load must be repriced for every changed sender, not just latency.

The planned forest makes remote paths a chain of REAL named buffers. Current
model maximum buffer-to-buffer branch89.208um and own-leaf pin leg29.279um.
The200um geometry rule is NOT reinterpreted: only installed legal FIRM clock
bodies would become entry/driver geometry in the normal guard. Present FF5 still
has no such bodies and still FAILS. All M7/M6 drop, PG/NDR/via access and layer/
corridor reservations require the next physical review; track-snapped tap points
alone are not that review. No threshold is raised to conceal a long root path.

Normal GEN is also blocked by a real shared-tool gap: master_slice.py currently
refuses core_tree in a multi-root clock_entries slice ('per-root plan trees are
not compiled by core_infra yet'). Each of the15graphs here is independently
compiled/estimated, not an adopted multi-root installer. A reviewed default-OFF
forest composition must aggregate them with disjoint actual sink ownership,
per-entry TT/FF qualification/frames, one source per actual input, final clock
body/row/site guards and no hidden inferred roots. Existing single-root defaults
stay unchanged. A results-local adapter would need equivalent ROOT/FLOW review.
The direct explicit-tap validator's200um INPUT-to-sink radius must not be given
falsified sink inventory to bypass this missing hierarchical contract.

No P&R/STA/activation should launch from this packet. Next concrete work is the
reviewed forest source adapter plus actual die/forwarded-source frame binding,
then current-source BOOT integration/census and a physical entry/via/layer review.
The personally viewed packed_clock_proposal.png and REVIEW.md document this
source/model milestone; runtime installation, actual clock netlist preservation,
833ps TT setup/FF hold and all remaining138START/reset plus maxpin163.26um data
failures remain separate obligations.
