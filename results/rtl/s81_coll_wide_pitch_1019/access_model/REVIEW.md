# Explicit SRAM side-channel access model

MODEL ONLY, pending ROOT review. No new LEF, Liberty, behavioral RTL, gate,
placement or route was generated. Existing memory views and compiler defaults
remain unchanged. This packet replaces the unsupported straight-lead assumption
with a complete analytical access architecture at the existing compiler's
research evidence level. It does not require transistor layout or GDS.

Proposed distinct master: `ot_sram_1r1w_512x128_m4_r2c2_p192_sc2`.
The source is the exact `eb8141cf8` 512x128/mux4/2r2c analytical macro. Its
registered read, disabled-read hold, masks, repair, same-edge OLD collision,
clock and storage bits remain unchanged. The source abstract box stays
174.120 x 29.736 um; the priced core remains 173.948 x 29.5631632605793 um.
Translate the whole inherited box by (21.360,0) um. The translation preserves
all inherited port-to-core boundary anchors, 77 actual PG rectangles and all
four original body obstructions. No invisible new core terminal is invented.

`full.png` and `corner.png` visualize the full paid outline and lower W
access corner from the exact analytical rectangles; these are not placement
or routed screenshots. `input.json` pins every original endpoint and its kind, PG, OBS, geometry,
corner model and calibration. `model.json` enumerates every complete path,
its metal rectangles, exact native VIA45 cuts/enclosures, layer lengths,
resistance, capacitance, and every per-pin input/clock capacitance.

## Constructive geometry

The two 21.360 um side channels pay for distinct M5 vertical columns at
96 nm spacing. Each of the 437 source M4 pads connects horizontally on M4 to
its assigned column, traverses M5 to its new y coordinate, then runs
horizontally on M4 to its new outer pad. Use the exact native VIA45 at both
bends. The two zero-jog pins use one continuous M4 wire and no coincident
vias. Total: 437 connected paths and 870 vias.

Column order is reversed relative to pin order. Source y = 0.780 + k*0.096 um;
terminal y = 0.780 + k*0.192 um. In outward distance from the inherited edge,
column t = 0.228 + (218-k)*0.096 um. When source k=2*j shares the terminal j
track, its shorter source segment stops before terminal j begins. This
prevents the shorts produced by a naive same-order column assignment.

The new outline is **216.840 x 43.752 um, 9487.18368 um²**, versus the
previous endpoint-only proposal's 174.120 x 43.752 and 7618.09824 um².
219 W / 218 E terminals remain at 0.192 um pitch, full-face density
5.0055 / 4.9826 per um. Heights and widths remain 24 mod 48 nm; source and
terminal phases and inherited translation are compatible with the earlier
R0/MX/MY/R180 phase model at 43.2 um origins. No R90 substitution is proposed.
Actual parent DEF track access remains unqualified.

Preserve the entire original PG mesh inside its translated box. No passive
upper or side channel needs an invented supply stripe, and no source PG
stripe is removed, narrowed or relocated relative to its core.
The77 are39VDD/38VSS actual source rectangles, checked independently
against the exact hashed source LEF in `pg_source_mapping.json`. The earlier
9c18 endpoint-only model allocated113 hypothetical stripes (57VDD/56VSS)
across a regenerated43.752um-height mesh; those were never generated views.
This construction preserves the actual77 original rectangles; it does not
remove36 existing stripes. Passive side/top access areas add no new powered
devices. Their absence of extra PG is explicit, not an erased source contact. M4/M5 signal
leads stay outside original M1-M4 body OBS and at least 72 nm from wide PG
metal. Proposed parent-visible OBS only adds reserved area: full M1-M3,
full M4 body except outer pin strips, plus M5 side channels. Parent signal
and PG routing must respect those channels; the inherited core M5 access
remains available for its real PG contacts. Full parent power connectivity
and external access are pending.

Native rules are copied in `asap7_tech.lef`: 24 nm M4/M5 width, 48 nm pitch,
2000 nm² minimum area, VIA45 M4 enclosure +/-23x12 nm, M5 +/-12x23 nm,
cut +/-12x12 nm, and 34 nm cut spacing. All complete wire/enclosure unions
meet minimum area. Exhaustive model checks find zero overlap/spacing,
outline, minimum-area, original-OBS or PG-spacing errors. Minimum cross-net
axis gaps are M4 **50 nm**, M5 **72 nm**, cuts **72 nm**; scalar metal check
uses 48 nm, exceeding 40 nm EOL/corner scalar spacing and covering the
largest listed 48 nm keepout extension. Native PRL rules are checked
separately: every signal wire is exactly 24 nm wide and uses the 24 nm
spacing-table entry; 96 nm PG metal uses the 72 nm wide-wire entry.
Minimum parallel-run gaps are 72 nm on both M4 and M5. The smallest
connected same-layer patches are **6600 nm² M4 / 3408 nm² M5**, each
containing its complete native via enclosure and independently exceeding
2000 nm². Separate M4 patches are not summed through a different-layer
connection to manufacture minimum area. This covers the enumerated
geometry, width/PRL and enclosure checks, not all LEF58/density/fill/antenna rules.
Native DRC and a complete external contact/PG/OBS proof are still required.

The positive and two causal mutants ran on the fleet, unit
`oth-ubuntu-1619042-1792439973`, using the exact planner source hash in
`input.json`. All 437 source-to-terminal paths connect. Reversing the columns
back produces an actual M4 cross-net overlap; removing source vias leaves
`r_ce_in` disconnected. Both witnesses are retained in `model_witness.log`.

## Electrical and clock price

Native setRC gives M4 R/C = 0.0180365 kohm/um / 0.178475 fF/um,
M5 = 0.0189935 / 0.164264, and VIA45 R = 0.0118 kohm per cut.
Every full metal enclosure is counted as area/width-equivalent wire length.
Via enclosure metal is therefore charged; separate cut fringe capacitance
is not characterized by this platform model. This is the same platform RC
evidence level, not a new parasitic extraction claim.

For each pin, C = sum(layer length * layer C), R = sum(layer length * layer R)
+ via count * via R. The positive RC-tree bound used here is
**D(load) = Rtotal*(Ctotal+load) + max(INV4_R,output_R)*Ctotal**.
It includes the actual receiving load and bounds the represented distributed
Elmore sums without the former 0.38 lumped-wire shortcut. Existing compiler
internal devices and calibration are untouched. All six decompressed native
INVBUF/SEQ Liberty hashes match the frozen calibration despite the image ID
changing from af971... to 16470.... Exact receipts and hashes are retained.

| Quantity | TT | FF | SS sensitivity |
| --- | ---: | ---: | ---: |
| Actual clock capacitance, fF |13.1623094|14.1897094|12.5002694|
| Clock lead upper bound, ps |8.559227|7.894429|10.228103|
| Input lead upper bound, ps |13.012915|11.043298|16.645043|
| Max CQ at 0.72 fF load, ps |433.695738|362.208848|547.271145|
| Max CQ at 46.08 fF load, ps |484.448106|406.655767|609.458386|
| Min CQ lower bound, ps |415.195299|346.043664|524.072474|
| Input setup upper requirement, ps |49.828321|43.632498|66.673687|
| Input hold upper requirement, ps |30.159486|27.566649|40.302123|
| Minimum period upper requirement, ps |424.030130|355.908530|534.079476|
| Minimum pulse upper requirement, ps |169.472793|143.002089|212.589479|
| Output resistance upper bound, kohm |1.118879|0.979870|1.370971|
| Read energy, fJ |1629.129421|1938.828614|1346.118637|
| Write energy, fJ |2064.391885|2473.476007|1692.152296|
| Extra clock switching energy, fJ |1.870090|2.262808|1.514773|

Do not add maximum lead delay to FF minimum CQ: doing so could manufacture
hold margin. Added minimum CQ is conservatively **zero**, while input hold
charges the maximum clock lead delay. Positive max delays and minimum-delay
bounds remain separate in this model. A generated Liberty policy must be
reviewed explicitly before emitting views; a single optimistic nominal table
is insufficient. Bounds shown apply within original 0.72..46.08 fF loads
and 5..320 ps slew domain, not uncharacterized extrapolation.

Energy convention is supply energy **C*V² per complete 0→1→0 cycle**,
which contains one supply-charge event. It is not C*V² per edge. Each
read/write number charges every nonclock lead one such cycle, including
unused and repair pins: a conservative activity allowance, not measured
switching. Clock access energy is one complete clock period and is separate
in the table. Add it **once per clock period**, including when read and
write happen concurrently. JSON fields explicitly provide read+clock,
write+clock, and simultaneous-read/write+one-clock-access totals. Do not
sum two per-operation clock charges for simultaneous read and write.

The unchanged source core-energy formula prices wordline, decoder, bitline
and per-bit periphery; it does not explicitly include charging the external
clock pin. `complete_boundary_clock_driver_energy_fj` reports the original
clock-pin capacitance plus its new lead. Upstream CTS and the rest of the
clock tree remain outside this macro model and must be composed once.
Ten TT payload clock pins total **131.623094 fF** before CTS.

The original source macro's area-proportional leakage is25888.1616 nW,
unchanged source devices. The previous proposal's38090.4912 nW arose from
applying that compiler assumption to its stretched outline; it was not a
measured core number. This model conservatively retains the compiler's
**5 nW/um² full-outline leakage budget**, now **47435.9184 nW** per macro,
including passive channels. Both the unchanged source number and full
budget are explicit in JSON. No leakage saving is claimed. Output slew
and complete load-dependent values are in JSON. No signoff margin, external
clock insertion, SS acceptance, or production bandwidth is inferred.

## Composition and next step

Ten new payload macros, five exact bb61ae67c p192_rc credit macros and ten
exact e26d92503 dual-clock 32x64 gearbox macros total **110679.05088 um²**,
35 real clock contacts, 696320 logical physical bits / 716960 including
native payload repair cells, and the same 573076 useful client bits.
This is +18690.8544 um² versus the earlier endpoint-only proposal, before
channels, clock, bands and client logic. No extra register or external cycle
is proposed. Native latency, throughput, real W595 forwarding/collision,
complete fanout/reset repair and actual parent scheduling remain open.

The widened macro exceeds 216 um: horizontal lattice-origin spacing is at
least **259.2 um**, and vertical spacing at least **86.4 um**, before actual
parent channels. Its parent fit is NULL. This is not an inherited COLL slot
grant, and it cannot repair the old 1080 versus 950 um parent mismatch.

The planner is reusable only for source-pinned two-face, uniform 96 nm
anchor orders expanded to 192 nm with the same native M4/M5 rules and
analytical core contract. Other 256x256/128x256/16x546 families need their
own exact anchors, corner model, chosen height, counts, PG/OBS, inventory and
parent model before any claim. No compiler-wide default is changed.
Existing bc42f77a8 n64 families remain separate alternatives; their true
dual-clock/collision/reset/array costs are not replaced by this model.

ROOT review must cover geometry/RC assumptions, the conservative FF minimum
policy, native-rule coverage, actual storage/client semantics and parent
area/clock/latency price. Only after review should a fresh owner emit one
distinct analytical source prototype and its consistency/function mutants.
Then prove full contact/PG/via/OBS/min-area access on the actual primitive,
followed by the actual client array. No new GDS or full internal memory
layout prerequisite is introduced by this review packet.
