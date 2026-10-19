# Reset-space and actual SerDes geometry candidate

This packet preserves the first physicalcase generation failure at
`st_rs_39_18_2`: no legal17.28square reset body within1200um of its old point.
The previous strict bind passed9130 connectivity checks; routing did not start.

The opt-in plan keeps25000um die height and every non-SerDes block dimension.
It adds30um to the south street and24um above the controller row, using54um of
existing north whitespace (north frame clearance256.56um). Service gaps grow43.2um
using151.2um of existing whitespace on each side; no estimated service reservation
is shrunk. Redistributing16um from column3E to4W opens the central reset corridor.
The four top host lanes use40um pitch rather than50um, with actual relay-body bands
checked. Every modeled coordinate payload hop remains<=404.9um; no block/band/body overlap is reported.

ROOT-approved prospective SerDes dimensions518.4x3844.8um enter all eight MU1 slots.
Array/lane translation259.2um and width growth518.4um give32486.9x25000um.
All full data-face bands fit with minimum3.924um clearance. This still fails the
existing500um horizontal reticle margin policy:256.55um remains. ROOT resolution
is required before a legal floorplan claim. MU2 copy-B has ten slots/six west,
and requires its own repack; `case_mu2` filenames refer to a generator revision
of MU1, not this separate multiplier.

The combined actual-LEF/body probe places5184 reset bodies at0.048um R0 origins,
with0.5um clearance,405um maximum displacement search, and352.732um largest move.
The exact-edge search projects every candidate onto that lattice; seven focused
placement tests include narrow legal pockets, continuous-only pockets rejected
without a grid point, over-distance refusal, and unchanged existing behavior.
OpenROAD `check_placement` accepted180 nonoverlapping BLOCK instances spanning all
joint0.054um site/0.27um row/0.048um signal/0.064um M6 phase classes in3695 rows.
The actual reset LEF has no SITE or SYMMETRY; only R0 is used. This is the top-die
BLOCK origin lattice, distinct from the43.2um hardened-child placement rule.

PG rectangles each admit2-3 complete M5 routing wires and at least202 M6 wire
crossings across every origin phase. This is potential metal access only:
The actual technology default VIA56 M5 enclosure fits at least two legal M5 centers per stripe and201 M6 crossings across all origin phases. Selected straps, local DRC and parent PDN connection remain owed.
The die-case pilot currently has no PDN generation. No PG-fit claim is made.

**This is not a bound reset network.** A405um displacement bound does not prove
that the moved parent-child reset edges stay within405um. Reset graph nodes must
be physically legalized before BFS/serve and release-calendar derivation; gate
calendar chains need physical placement and actual edge checks too. No GRT,
clock closure, actual parent child fit, or submission/adoption is claimed.

The new geometry changes11 link station counts (summary.json lists each), giving
3182stations/864100bit-stages versus3185/863424. Landing K/bundle ages and compiler
schedule must be regenerated coherently; no free rate/latency credit is taken.
The SerDes-only packet keeps the original ages and is separate from this packet.
Original non-reset-space plan and dv_links_record outputs remain byte-identical;
SHA256s are in summary.json. Existing parent area-fit estimates are retained only
as diagnostic metadata and do not replace actual hardened-child fit proof.

Reproduce the pre-SerDes reset-space plan with:
```
python3 tools/s81_dv/dv_plan.py --layout p4 --p4l --mu 1 --tier-w 276 --lanes 4 --p4h-drop 6 --frame-w 1436.832 --placefix --reset-space --lk-slots results/arch/s81_dv_1016/dieplace_1019/plan.json --out /tmp/reset_space
python3 tools/s81_dv/serdes_slot_candidate.py --plan /tmp/reset_space/plan.json --out /tmp/reset_serdes
```
The diagnostic reset probe uses `reset_space_probe.py` with the saved exact LEF
sizes, first-failure place_hints, original plan and combined plan; saved gate
trees are read only. `lattice_probe.py` runs in the ORFS image with the exact reset
LEF mounted at `/reset.lef`; `lattice_probe.log` preserves the actual fleet check.

Actual old-netlist replay confirms the missing reset physical proof. On the new
legal bodies,1003/5183 reset-to-reset connections exceed405um even by minimum
LEF-rectangle distance, max5107.624um. The original planned bodies already have
456/5183 such edges (max5130.392um), especially gate-calendar chains placed near
an endpoint while their reset leaf is far away. Three root/other edges are
excluded. These are failures, not newly accepted reach budgets.

A directed lower-bound .o-to-.i graph initially reaches4635/5184 bodies. Inserting
45 additional legal R0 bodies connects5228/5229 with maximum selected rectangle
distance404.933um and maximum depth213. One isolated candidate remains. This is
only a connectivity experiment: it has not proved both .i and .rs pin access,
all real sinks, root synchronizer placement, new calendar chains, or routed
paths. The .rs pin is a separate physical load of the same reset net. The isolated
candidate may be removed only after all real sinks are served by the rebuilt
graph. Existing orientation hints include reflections, but the current writer
uses R0 and the LEF declares no symmetry; no reflection credit is taken here.
