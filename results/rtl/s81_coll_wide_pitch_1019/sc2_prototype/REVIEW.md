# SC2 bounded source and geometry prototype

**SOURCE/GEOMETRY PASS; TIMING BINDING BLOCKED.** No Liberty, CTS, route,
client-array qualification or parent grant. This is the explicitly authorized
analytical compiler research prototype, not transistor-layout evidence.

The distinct master is `ot_sram_1r1w_512x128_m4_r2c2_p192_sc2`. The generator
pins the full prior model SHA
`564c39512720a00c2924f267b87e36c487b5bba76817142b2c5b54d346fbb988`,
planner SHA `2b4f2a2a23f5272393974655b89ad510947364e935b3771bfdc82136e5276394`,
and immutable original source manifest. Existing compiler defaults and every
old master remain untouched. The original behavior and blackbox are copied
with only the module declaration renamed; exact reverse-renaming is checked.

`generated/` contains the LEF, behavioral model, blackbox, JSON, hash manifest,
explicit timing-role specification and `NO_LIBERTY.txt`. The JSON includes all
437 complete paths, 870 native VIA45 instances, 77 preserved actual PG
rectangles, exact parent-visible obstructions, and original core anchors.
The LEF exposes the new terminals and preserved PG; internal access wires and
vias remain enumerated in the analytical JSON. This does not claim that LEF
contains an internal routed layout. New outline is **216.840 x 43.752 um**,
area **9487.18368 um²**, 219 W/218 E signal contacts at 192 nm pitch.
Only X/Y symmetry is advertised; no R90 substitution.

Fleet Verilator **5.050** tests cover all 512 addresses with and without both
row and column repairs, all column-mux lanes, masked writes, same-edge OLD
read/write, and disabled-read hold. All addressed memory is explicitly written
before comparison; the bench does not rely on the inherited simulation-only
power-up initialization. Positive: **4096 checks PASS**. Changing write order,
ignoring masks or ignoring read enable causes the retained mismatch witnesses.
Constructive geometry has zero enumerated errors; reversing columns causes a
real cross-net short and dropping source vias disconnects `r_ce_in`.
Emitted pin/PG/OBS geometry is independently compared to the frozen model;
foreign behavioral source is refused by hash before generation.

## Why Liberty generation stopped

At inspected main `22f53efd97b219b16039486b0638e3c592d37a63`,
`tools/w18/corner_sta.py:script` reads one `<master>_<corner>.lib` for each
macro. `tools/ref_tile/path_classes.tcl` also reads ordinary libraries into a
session containing both min/max queries. The existing `views.py` writer emits
one CQ table per corner, not separate minimum and maximum data. It cannot
express this access model's distinct roles through its current `Timing` API.

The required roles are explicit in `TIMING_ROLES.json`:

| Role | CQ policy | Constraint policy |
| --- | --- | --- |
| TT setup | Load-dependent maximum, including upper clock/output lead | Upper setup, period and pulse requirements |
| SS sensitivity | Separate SS maximum | SS upper constraints; not acceptance |
| FF hold | Original conservative minimum bound; added lead minimum **zero** | Upper hold requirement includes maximum clock lead |
| FF characterization | Separate load-dependent FF maximum | FF upper setup/period/pulse, never used as minimum CQ |

Adding maximum lead delay to FF minimum CQ would manufacture hold margin.
Using the FF minimum table for maximum analysis would understate delay.
Neither substitution is emitted. No nominal `_ff.lib` alias exists.
The inherited minimum model is an analytical lower bound within its declared
domain, not a newly measured minimum-delay characterization.

Per-pin capacitances and corner-specific clock, setup/hold, pulse, period,
slew and energy bounds are preserved in JSON. Domain: 5..320 ps slew and
0.72..46.08 fF load; no extrapolation qualification. The model's nonclock
capacitance map includes output-boundary lead capacitance as well as inputs;
a future Liberty writer must distinguish output intrinsic capacitance from
input pin capacitance rather than applying an input-cap attribute to outputs.
Energy is C*V² for one complete 0→1→0 cycle. Read and write each include one
conservative full nonclock-lead activity allowance; clock access is added
once per period even for simultaneous read/write. Original clock-cap driver
energy and upstream CTS must each be composed once. Leakage retains the full
outline-area budget (47435.9184 nW), with unchanged source-core leakage also
reported. No energy or leakage reduction is claimed.

## Bounded proposal for separate ROOT review

Add an **opt-in per-master timing-role manifest**, default absent, restricted
to this exact master/source/model fingerprint. It must name and hash separate
TT-MAX, SS-MAX, FF-MIN and FF-MAX tables. No filename inference or fallback.
The reader must verify cell identity, geometry/functional provenance, corner,
role and domain before loading any table. Emit role receipts with signoff
results and fail closed for missing, duplicate or swapped roles.

Before implementing, prove the pinned OpenSTA/OpenROAD build can bind
distinct min/max libraries for one cell. If its supported `read_liberty`
min/max controls are used, verify actual queried arcs under both roles with
a tiny SRAM-launch/capture vehicle and swapped-role negative control.
Alternatively, isolated analysis sessions may select an explicit role only
if **every** min/max query and clock/data dependency in that session is
accounted for. Merely loading two ordinary libraries is insufficient.

The route, CTS/native probes, path-class gate, final STA, measured re-STA,
macro clock/hold consumers and exported-view reader must use coherent role
selection. Any consumer that requests a missing role (including TT minimum
analysis) must refuse or require an explicitly reviewed conservative bound;
it must never silently use a MAX table as MIN. Maintain default byte identity
for all legacy masters. This proposal is not authorization to edit shared
helpers; ROOT must first approve its exact bounded scope.

Native external contact/PG/OBS/antenna/DRC access, parent power connections,
clock insertion/spread, actual client collision/forwarding and throughput,
all-driver fanout/reset, and parent slot fit remain open. Ten payload macros
plus five exact credits and ten exact gearboxes retain the prior model's
**110679.05088 um² / 35 clock contacts** before channels and client logic;
minimum origin pitch 259.2 x 86.4 um does not constitute a parent grant.
