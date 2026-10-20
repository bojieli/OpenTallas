# Parameterized DC current-versus-drop envelope for exact 5de master

This finite resistor surrogate prices the explicit new analytical SRAM supply
interfaces. It establishes **conditional current/drop sensitivities**, with no
claim that either macro has adequate supply. Baseline geometry is unchanged from
5de283aad (c634 core/access, 899b trunks). No native engine, simulator, SPICE,
AP/PDN, GDS prerequisite, Liberty, production abstract or geometry edit is involved.
A4's independent owned-metal experiment remains separate. ROOT review is required
before adoption.

## Circuit boundary and coefficients

Each actual M1 port is a distinct load interface: 22 VDD plus22 VSS for Qwen,
39 VDD plus38 VSS for SC2. All121 interfaces retain one V1/V2/V3/V4 stack,
their actual M3 center offset, 120nm M4 rail and 24nm M5 trunk. Names do not
substitute for connections. The circuit is explicitly:

`ideal N/S parent port — shared segmented M5 — V4 — M4 branch — V3 — M3 — V2 — M2 — V1 — M1-center load`.

Pinned `current_setRC.tcl` specifies kΩ/µm: M1 .0704175, M2 .0297127,
M3 .031287, M4 .0180365 at24nm, M5 .0189935 at24nm. M4 is scaled24/120
for the actual120nm width. V1/V2/V3 each contribute .0172kΩ; V4 .0118kΩ.
These are analytical platform coefficients, not extracted temperature/process
resistance bounds. Via values are each charged once. Model JSON retains every
actual interface, segment length, full rail resistance and sensitivity matrix.
The M1 capacitance1e−10fF/µm is a placeholder; it is unused and establishes no
capacitance/transient bound. No capacitance is needed for this DC solve.

The declared interface load enters at the M1 pad center, coincident with V1.
V1 and V2 are coincident, so the centerline M1/M2 series lengths are zero.
M3 traverses the actual V2-to-V3 Y separation, and M4 traverses actual V3-to-V4 X
separation (.288µm VDD/.384µm VSS). The lower branch is64.186–65.096Ω,
including all four vias. An explicit alternative puts all current at the far end
of the84nm M1 pad, adding42nm × M1 resistance =2.957535Ω per loaded interface.
This is a distinct one-dimensional interface convention, not a bound on
unmodeled transistor/contact resistance, 2-D spreading, or body impedance.
The older5de full-pad/full-height guard path remains in the inventory for
comparison; it is not confused with shared-network resistance.

Full M4 rails are31.392µm Qwen /173.520µm SC2:113.2403616Ω /625.938696Ω
end-to-end under the scaled sheet model. Their long unused arms are not charged
as a series path to a centrally defined M1 interface. No distributed bitcell
loads along those arms are assumed. The core body consumes current through the
explicit M1 interfaces; all body distribution/contact resistance and the
feasibility of that core implementation remain unknown. If a future core
instead loads rail ends, it must supply those load nodes and resistors.

Both trunks are fed at their south Y=0 and north Y=H endpoints by independent
ideal fixed-voltage sources. Actual84nm external port rectangles are enumerated
in analysis.json. This is an endpoint abstraction of these port subsets; it does
not certify contact spreading or parent access. Full-height trunk resistance is
402.510252Ω Qwen /831.915300Ω SC2. The two net components are kept separate.
VDD withdrawal and VSS return are both solved; VSS at the core is not ideal
zero voltage. Equal total current I flows through each net at steady state,
with independently parameterized spatial distributions. This conservative
freedom includes every equal-total nonnegative distribution without inventing
which core VDD interface pairs with which VSS interface.

## Finite network and parameterized results

Let interface i be at y_i, with branch b_i, outline height H and M5 resistance
per length ρ. For each net, its exact transfer matrix in this declared circuit is

`K_ij = ρ min(y_i,y_j) [H−max(y_i,y_j)] / H`

`Z_ij = K_ij + δ_ij b_i`, and `drop_i = Σ_j Z_ij I_j`.

Using kΩ and mA gives volts. Positive VDD drop plus positive VSS rise reduces
local supply. These are linear DC equations, not a transient waveform model.
The uniform row maximum divided by interface count gives the worst observed
interface under equal per-interface current on that net. With only total I and
nonnegativity specified, the sharp worst observed drop is `I × max_ij Z_ij`:
for any fixed observation, a linear functional over the current simplex attains
its maximum at one current-injection interface. The reported loop envelope adds
the two independent net maxima. It permits arbitrary observation pairs; an
actual core pair map could tighten it.

| Loop supply loss coefficient, V per mA total macro current | Qwen | SC2 |
| --- | ---: | ---: |
| Uniform current per interface, each net | .123256970 | .252218024 |
| Arbitrary nonnegative distribution, M1-center interface | .330498856 | .545447954 |
| Arbitrary distribution, far-M1-end interface variant | .336413926 | .551363024 |

For example,1µA total is a unit normalization: the center-interface worst
coefficient corresponds to .330499mV / .545448mV; **no1µA operating current is
asserted**. Qwen worst injection sites are PG14 VDD / PG34 VSS; SC2 PG29 / PG66.
The per-net unrestricted coefficients are .165357531/.165141324V/mA Qwen,
.272757752/.272690203V/mA SC2. A chosen allowed loss Δ gives only a conditional
current limit `I_mA ≤ Δ_V / coefficient`, after choosing the distribution/interface
convention. Neither Δ nor an operating current is supplied by this packet.

For specified individual rail caps c_j and total I, feasibility requires
`0 ≤ I ≤ Σ c_j`. For every observation row, sort Z_ij descending and allocate
current up to each c_j until I is exhausted; `capped_max` implements this exact
continuous-knapsack optimum, also returning the adversarial allocation. Maximize
across rows, then add the independently constrained return-net maximum. This is
a parameterized per-interface envelope, not a guessed hotspot load.

The shared continuum contribution on either doubly fed trunk is at most
`ρ H I/4`; separate branch cost adds only `b_i I_i`. It would be incorrect to
charge every load the entire trunk resistance independently. South-only feeding
with north open is also computed: worst loop coefficient rises to .767577953
Qwen /1.248949217SC2 V/mA. Removing a feed is materially different from the ideal
four-port assumption. South/north reaction currents are respectively
`Σ I_i(H−y_i)/H` and `Σ I_i y_i/H`; they sum to I and are nonnegative.
Unknown parent PDN resistance/inductance, feed asymmetry, supply offsets and
coupling must be added separately. None is zero in a real implementation merely
because this sensitivity exercise idealizes its boundary.

## Concrete cost and conditional alternatives

The exact baseline remains52.440×21.192µm Qwen /216.840×43.800µm SC2,
with four M5 external PG rectangles on two existing nets,44/77 M1 interfaces,
132/231 lower vias plus44/77 V4s. Added M5 metal is1.017216/2.102400µm²;
lower exclusion area1.596672/2.794176µm². The SC2 dedicated north attachment
apron29.919056µm² is retained. Remaining original core capacity is542.469648 /
5139.833392µm², requiring conditional density multipliers1.002943339 /
1.000538010 for unchanged core state. Outline/lattice/cycles/state deltas from
5de are zero. Conditional density is not demonstrated transistor fit or parent
channel fit. No supply/body adequacy follows from capacity accounting.

No width increase is selected because required current and allowed drop are
unknown. analysis.json prices distinct mathematical q=2/q=3 trunk-width
proposals: trunk area/C scale q, ideal sheet/trunk K scales1/q, with branch/via
cost unchanged. Area additions are1.017216/2.034432µm² Qwen and2.102400/
4.204800µm² SC2. At unchanged centers these widths reduce the VDD/VSS gap
from72nm to48/24nm and violate the retained72nm conservative parallel-gap
predicate. They are **not legal in-place repairs**; track phase, native allowed
width, ports, corridor, enclosures and signal/OBS clearance need a new design.
For target loss Δ and I, a sufficient continuum proposal requires
`q ≥ [ρ H/2] / [Δ/I − b_VDD,max − b_VSS,max]`, only when the denominator is
positive. No finite trunk width solves a budget below the branch floor under
that sufficient envelope. Extra parallel trunks with proper taps could reduce
shared resistance, but require new metal, vias, ports and reservation corridors;
no unpriced parallel-wire fix is asserted.

c634's conditional TT full-toggle signal/access energy is276.534941fJ Qwen /
1192.386051fJ SC2 per declared activity event, including complete clock-pin
energy. This is not complete core energy. It can contribute only the conditional
average relation `I_avg = E_event × event_rate / V` after specifying activity,
rate, actual supply, missing core dynamic energy and leakage. It supplies no
instantaneous rail current cap, pulse width or peak-to-average ratio. New body
placement may alter energy. PG metal is not charged as toggling signal energy.
Transient IR, decap effectiveness, Ldi/dt and EM require missing independent
inputs and are not qualified by this DC model.

## Reproduction and finite controls

Run `python3 model.py` (Python with NumPy; finite local matrix operations only).
A separately constructed segmented-line nodal conductance matrix is inverted
and agrees with the closed-form Green matrix to <1e−12kΩ on all four nets.
Positive-definite passive matrices and nonnegative transfers are checked.
Uniform individual caps reproduce the uniform-current answer. Negative current
and insufficient summed caps are causally refused. Removing VIA34 makes a
positive-current lower node open: an actual singular nodal solve refuses a finite
solution. Loss of north feed increases every shared transfer coefficient.
These are circuit/model controls, not native DRC, physical IR or transistor tests.
`SHA256.json` pins scripts, complete5de/c634 source models and raw RC input.
