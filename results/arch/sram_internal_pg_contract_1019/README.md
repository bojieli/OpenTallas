# New analytical SRAM master: owned internal supply geometry

This contract completes a concrete **analytical internal supply topology** for both
families, through explicit M1 electrical interfaces, V1/V2/V3, every retained M4
rail, V4 and the central M5 trunks. It replaces 899b's unspecified internal
attachment with a new source-owned design. It does not require unavailable GDS
or transistor qualification to state this design. Its remaining core placement
assumption is quantified below; native access and electrical signoff are separate.
No native engine, AP, PDN, B/C, production view, Liberty or source activation ran.
The separate executing A3 experiment still uses exact c634 geometry, unchanged.

Inputs are exact c634d1540 model and 899b732d6 model. All 44 Qwen / 77 SC2 rail
IDs and VDD/VSS names remain distinct. Their 120 nm M4 rail rectangles, original
translated 96 nm attachment bands, +12 nm rail-center change relative to the
translated original contact, +39 nm original bitcore translation, +48 nm known
signal leads, all known signal vias and external terminals remain unchanged.
Two M5 trunks and all 121 V4s retain exact 899b geometry and external north/south
84 nm long ports. Original electrical source RTL is neither changed nor replaced.

## Actual metal and reservations have different owners

`model.json` separately enumerates **actual proposed internal supply metal/cuts**,
all original known signal access via the pinned input, all six original routing
reservations per family, and new internal exclusion volumes. Routing OBS remains
an external router reservation, not an invented sheet of physical conductor.
None is erased, shrunk, assigned a supply net or given a same-net waiver. Original
M1–M3 full-face reservations still protect the analytical core from parent routing;
original M4 OBS still protects internal rails and original M5 side reservations
protect signal access. Their overlap with internal source-owned metal is an
explicit ownership distinction, not a claim that an ordinary parent routed wire
can legally cross an instance blockage in the native checker. A later abstract
must expose the actual M5 ports while retaining these distinct reservation roles.
This packet generates no such abstract and grants no native OBS exception.

The **new master**, rather than the old unavailable implementation, defines its
internal M4 actual metal as exactly these retained supply rails plus enumerated
known signal access. Internal M5 actual metal is exactly the two supply trunks
plus enumerated known access. V4 actual cuts are exactly 121 new supply cuts plus
all original known signal cuts. Additional undocumented old M4/M5/cut shapes are
not imported. This is a constructive constraint on a new analytical implementation,
not an inference that an old undocumented layer was empty. A future proposal for
any additional internal M4/M5/V4 object must be enumerated and clear this ledger.
It cannot silently inherit unspecified old geometry.

The M4/V4/M5 central corridor is X=[base−84, base+180] nm, full outline height,
where base is the VDD trunk center: 26208 nm Qwen / 108432 nm SC2. It has
5.594688 / 11.563200 µm² of layer reservation. Only enumerated supply metal and
cuts occupy it. Every known signal shape and full via enclosure is outside it.
This upper-layer reservation is not subtracted from the lower bitcell area:
M4/V4/M5 do not physically intersect M1–M3. Lower core routing has its own
exclusion cells, counted once below. No unknown old cut is assumed absent;
new internal cut ownership is specified exhaustively by layer and identity.

## Exact lower electrical interface at every original rail

Each rail obtains exactly one complete stack:

`M1 core port → VIA12 → M2 landing → VIA23 → M3 landing → VIA34 → M4 rail → VIA45 → M5 trunk → north/south supply port`.

The core electrical model owns the M1 port as its new physical supply boundary.
That port is a defined source interface, not a demand that some unspecified
future internal contact attach to the old terminal. The original conditional
bitcell/core model consumes VDD/VSS through these explicit interfaces. Its
internal bitcell signal wiring occupies the remaining lower core reservation
and must not overlap any supply exclusion cell. No old lower-layer transistor
placement or old supply cut arrangement is inherited or claimed extracted.
Actual bitcell transistor sizing, supply impedance/current distribution and
native placement are beyond this analytical contract; lack of GDS is not a
blocker to the owned geometry stated here.

For every original ID, the interface X is base−288 nm for VDD and base+288 nm
for VSS, both on M1/M3 X=0 mod36 tracks. Lower Y is the nearest 18 mod36 to
M4-center−12 nm, matching actual M2 offset −270 nm modulo 36. This explicitly
prices any difference between translated original contact and the new M1 port;
each row records that offset. Original M4 attachment remains at its +12 nm
position. No port is teleported and no original rail disappears.

M1/M3 pads are vertical 18×84 nm. M2 is horizontal 84×18 nm. Each area is
1512 nm², above the pinned 666 nm² minimum; M2/M3 length 84 exceeds 37 nm.
Native VIA12/23/34/45 metal and cut boxes are parsed verbatim from the pinned
ASAP7 tech, not guessed or scaled. In particular VIA34 is M3 18×34, M4 40×24,
V3 cut 18×24 nm; M3's full 84 nm pad removes the too-small isolated 34 nm
landing. Every enclosure lies within its corresponding full pad or M4 rail.
Complete V4 enclosures remain within M4 rail and M5 trunk. All coordinates are
integer 1 nm grid; M4 Y3/M5 X0 modulo48 and lower M1/M3 X0/M2 Y18 modulo36
are explicit. R0 at origin0 modulo48 **and** modulo36 is required; the 43.2 µm
lattice meets both. Mirrors are not inherited. Native LEF58 EOL/enclosure rule
applicability is not certified by using the native default via boxes.

Each lower stack owns a 168×216 nm M1/M2/M3/V1/V2/V3 exclusion cell centered
at its interface X and M4 rail Y. These cells reserve actual lower attachment
space against the remaining analytical core placement, not merely parent routing.
All cells are disjoint. Every complete lower pad is at least31 nm from its cell boundary and each lower cut at least34 nm, so a new core object remaining outside those closed cells cannot violate these finite margins. All lower metal/cuts fit their cells, and source-owned
core routing must remain outside their closed volumes with the enumerated
finite clearance margins. A later lower core metal/cut addition must be checked
against the complete actual supply geometry, not just against gross area.

The first containment check rejected SC2 rail38: its M4 range29607–29727 nm and
lower attachment do not fit the old bitcore top29603 nm. The first attempted108×168 cell failure is preserved
in `initial_containment_refusal.json`; a subsequent finite guard check rejected
that narrow cell because its M2 side margin was only12 nm. The final168×216
cell guarantees the declared margins, and `guard_band_refusal.json` records
this structural correction. The new design adds a **172 nm north
attachment apron**, across the SC2 core width, extending the supply attachment
reservation to Y29775. Its 29.919056 µm² is charged as dedicated internal space
inside the unchanged macro outline. Original bitcore and bit/source anchors stay
unchanged. The apron is not free usable bitcell area. Qwen requires no apron.

| Finite cost / capacity | Qwen | SC2 |
| --- | ---: | ---: |
| Original rail IDs, each with one M1 interface |44|77|
| New V1/V2/V3 cuts |132|231|
| Retained 899b candidate V4 cuts |44|77|
| New lower supply metal union area, each of M1/M2/M3 µm² |0.066528|0.116424|
| Lower exclusion cells total µm² |1.596672|2.794176|
| Exclusion intersecting original bitcore µm² |1.596672|2.765280|
| Original bitcore area µm² |544.066320|5142.598672|
| Remaining original bitcore capacity µm² |542.469648|5139.833392|
| Required density multiplier for same core state |1.002943339|1.000538010|
| Dedicated north apron area µm² |0|29.919056|
| Outline µm, unchanged from c634 |52.440×21.192|216.840×43.800|

The 0.29433% / 0.05380% density increase is a **conditional core fit** assumption,
not demonstrated transistor placement. It is a finite, priced implementation
specification. Any core unable to meet it must enlarge its reservation/outline
and update the model; the current packet claims no free unchanged-outline fit.
The original analytical core state retains 2048 / 65536 logical data bits with original
mask/repair/control semantics and zero additional state, clocks or cycles. SRAM
ECC is not introduced. Outline and nominal lattice area deltas from c634 are zero;
this does not prove actual parent placement or available channel capacity.

## Geometry and cost checks

All new metal is checked against every known signal shape, complete signal via
metal, other-net supply object and new supply object on the same layer. There
are 178853 / 754893 such pairs. Metal checks require 18 nm lower / 24 nm upper
box clearance and conservative projected gaps31 nm lower /72 nm upper.
Cuts are checked by actual cut layer: V1/V2≥18 nm, V3/V4≥34 nm. All original
signal V4 cuts participate: 21736 / 78694 pairs. No failures were found by these
finite predicates. `all_new_crossnet_neighbors_within_200nm` records neighboring
IDs and distances; 200 nm is only a reporting selection, never a check cutoff.
Each outline, first/last contact, full pad, enclosure and cut is checked. Lower
cells are checked against the explicitly expanded attachment reservation.
M1–M3 core reservations are capacity objects, not physical conductors to which
same-layer metal spacing is falsely applied.

Independent planar positive-overlap edges plus complete native via bridges form
exactly **one VDD and one VSS geometric component** per family, including every
M1 electrical port and every M4 rail. Net-name equality alone creates no edge.
Removing an actual VIA34 bridge disconnects its M1 port from its M5 trunk in the
causal graph control. Other controls reject coincident VDD/VSS trunks, an unowned
cut in the supply corridor, undersized M3 landing, ignoring lower exclusions,
unchanged old attachment coordinates and SC2's unpriced top attachment. All
controls are finite geometry/model refusals, not native DRC controls.

Current pinned platform `setRC.tcl` supplies all M1–M5 wire/via coefficients;
raw file and contemporary read-only image receipt are under input. It agrees
with c634 M4/M5/V4 coefficients. The M1 capacitance coefficient is the platform's
**1e−10 fF/µm placeholder**, so it is not a characterized physical capacitance or
an upper bound. Native extraction/coupling and cut fringe are unmeasured.
Additional lower wire C is1.221513216 /2.137648129 fF; retained 899b M5 C is
6.962165376 /14.389526400 fF, giving conditional additional wire C
**8.183678592 /16.527174529 fF**. V1/V2/V3 each add0.0172 kΩ; V4 retains0.0118 kΩ.
Every contact has a source-pinned conservative full-length lower-stack R plus
actual rail-center-to-trunk R and full-height M5 R bound in `path_R_inventory`.
M4 rail sheet R is scaled24/120 for the retained120 nm width. These are wire-only
coefficients and finite path costs, not an IR/EM/supply-drop bound.

PG is supply metal, not toggling signal. No false per-access C·V² switching charge
is added for VDD/VSS. Boundary signal/clock RC and original conditional core
energy/leakage assumptions remain explicit and unchanged at this model level.
Core electrical dynamic/leakage after new placement, supply return, internal
coupling, native setup/hold/CQ and first-use phase are not characterized by this
metal model. No zero physical energy penalty or timing qualification is inferred.

Run `python3 model.py` then `python3 plot.py`; only finite local geometry and
plotting run (~1 s /2 s), no synthesis/simulator/EDA. `SHA256.json` pins inputs,
model, scripts, refusal and PNG. `internal_pg_contract.png` shows both complete
masters, first supply stack and last/top stack, including the SC2 top obligation.
ROOT must review the full new contract before any engine or view-generation step.
