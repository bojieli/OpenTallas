# ORDER hard-band ownership correction and physical audit staging

The n32c/d gates stopped before global placement: their hard-band hook required
`ot_inhold_firm.txt`, although these exact kits disable input hold. The actual
canonical pin-flop hook lists both input and output anchors in
`ot_out_flop_at_pins.txt`. New opt-in n32e/f use that actual ownership contract.
The selected RTL, two-stage native reset forest, six SRAMs, geometry, source
function and schedule remain byte-identical to the source-qualified packet.
The b38 exact plain native-reset API and band-edge tolerance are now on main.

Each new hook requires every listed pin anchor to exist, appear only once, and
be FIRM/LOCKED. It rejects an unexpected hold-owner file, any unlisted fixed
functional cell, and preexisting region membership. Every other signal-connected
standard cell is assigned to the inclusive band: ties and port/clock buffers
receive no blanket exemption. Six macros are required; only cells with no
signal-connected terminals are classified as physical infrastructure.

Fleet replay uses each actual n32c/d `3_2_place_iop.odb` and the byte-identical
canonical `io_flop_at_pins.tcl` plus anchor packer. The replayed anchor identities
must equal the historical actual gate list. Both baselines PASS: 2290 fixed,
ungrouped anchors; 86,751 other functional standard cells fenced; six SRAMs.
The two outlines contain respectively9133/10079 signal-unconnected physical
cells. All seven causal negatives per outline are REFUSED: missing ownership
file, duplicate/missing/unfixed anchor, unexpected hold-owner file, unlisted
fixed functional cell, and duplicate hook. Full logs and classification ledgers
are archived. Input ODBs remain at the hashed fleet paths, not checked into git.

Actual anchor bounds are wholly inside the approved model band:

- e: [2.268,216.27,300.132,300.24] um
- f: [2.322,216.27,343.332,300.24] um

Anchor area667.764 plus central allocation11640.278 gives12308.042 um2.
This is49.02%/42.81% of the approved band capacities. These are actual anchor
positions and preGPL cell allocation, **not completed interior placement or
CTS density qualification**. Fleet units3823747 and3843493 both exit0.

The old geometry model used `math.dist`:369.359/395.239 are Euclidean envelope
values only. The preserved raw history is `geometry_plan_original_euclidean.json`.
The same rectangles have conservative Manhattan envelopes514.08/557.28.
Neither metric is a connected-stage result. The signed coordinator approval
remains MODEL/fill only. Updated own geometry fields explicitly separate the
metrics and retain actual full-combinational-stage L1<=405 as OPEN.

Completed-log correction07:44: a/b **did execute** the original row-band
hook. The earlier observation was made before the floorplan script completed;
inferring that ORFS ignored the variable was incorrect. Completed b floorplan
log lines900-901 explicitly source std_band.tcl and report312 retained rows,
792 removed, area28749.4272um2. The existing a/b audits are therefore actual
row-pruned band diagnostics, not free-placement experiments. This corrects the
historical lane note and the earlier text in this packet; raw history remains
preserved. New e/f strict-fence proofs remain valid but those gates stay on HOLD
and may be unnecessary if the original b finishes the required final audits.

a completed CTS with pin-flop TT/FFspread23.8/23.1ps but failed GRT after hold
repair with DRT-9419 and20273 illegal cells despite zero reported overflow.
b completed WARN/0FAIL with GRT0overflow, TT/FFpinspread20.6/19.8ps, measured
band area15115.509um2/density52.58%/outside0. Its diagnostic TTsetupWNS is-64.6ps
and hold+32.8ps. Full-source final-stage reach, final-native, PG and registered
boundary audits remain OPEN, so no submit/physical qualification is claimed.
c/d failed before GPL as described above. Raw gate JSONs are retained.

`full_stage/` stages a private reuse of PEER/GRP guarded full sequential-stage
identity traversal on immutable actual row-pruned-band a/b4_1CTS snapshots. It binds actual
source, spec, Liberty, parser and macro behavioral identities, including six
registered-read SRAMs. Standard-cell endpoint coordinates use cell centers;
macro pins use actual pin XY. That approximation remains a limitation near the
405um threshold. Those audits are still running; no result is inferred here.
No n32e/f gate or physical qualification is claimed by this packet.

The in-progress extractor's descriptive scope string still says FREE-PLACEMENT;
that string predates the completed-log correction. Its exact executed source is
preserved unchanged for hash correspondence. The completed row-hook log and
this erratum correct the description; graph, coordinates and reach arithmetic
are unaffected.
