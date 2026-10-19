# HIDX exterior escape: conservative PG-clear ray MODEL

Immutable input: original placement c74808561, fixed 140.4um outline, core2.16..138.24, 2609 functional/clock pins, all504 legal rows. Proposed source band56.16..84.24; no cells, pins, PG, or checkpoint changed. MODEL ONLY; original physical quality HOLD persists. No implementation engine, CTS, route or simulation was launched.

Finite conductor scan ran unpinned through ot-run: ep7 unit oth-ubuntu-174696-1792449562,16GB/2threads, real RAN exit0. Maximum resident memory1,486,492KB. Identical five immutable inputs staged ep4/5/6/7/8 before placement. All2,117,134 native POWER/GROUND shape rectangles,39,895 via objects,22,290 native PG pin records retained; routing and cut rectangles both included. Input SHA256 receipts are in ledger.json. Actual source PG contacts remain actualPG, not signaltracks or omitted shapes.

Track contract is exactly24nm+48nm*k on M2-M5,2835 coordinates insidecore. No substitution of finer nativeM2pitch. A rectangle blocks an entire candidate ray if its conservative expanded rectangle intersects the ray. This is an intentionally pessimistic projection, not an exact detailed-route capacity or DRC result. Same-role PG still blocks a signal ray.

| Horizontal region | Gross perlayer | M2 wire / via envelope clear | M4 wire / via envelope clear |
|---|---:|---:|---:|
| South2.16..56.16 |1125|700 /650|300 /250|
| Band56.16..84.24 |585|364 /338|156 /130|
| North84.24..138.24 |1125|700 /650|300 /250|
| Wholecore |2835|1764 /1638|756 /630|

Full-span vertical M3 has2627/2835 projected PG-clear coordinates; M5 has2575/2835. Same counts hold separately for north/band/south rays because the relevant PG rectangles repeat in each. These counts do not reserve different vertical rays for competing signals. Nearest M3 clear coordinate is <=0.216um from ANY core x, and <=0.214um over original80,526 M1 signal-rectangle centers. This is a geometric horizontal-distance fact only: native M1 pin legal VIA12 contact, M2 jog, neighbor nets, and cut/metal DRC remain OPEN.

Band combined via-envelope capacity468 rays is a PG-only ceiling. Reserving64long Hclock rays on each halfband consumes128, leaving340 potential signal rays before internal conflict/access. The actual clocksource topology and use are not proven by this subtraction. Exterior belts supply900 such Hray candidates per side (M4 first250, then M2 650). There are293 fixed E/W port contacts in the band (W147 includingclk, E146),253 perface in each exterior belt; N/S each652. Assigning distinct horizontal belt rays therefore has ample scalar cardinality, but NO complete registered-IO escape construction is asserted: fixed-port ingress, vertical net ownership, crossings, coupling, and the parent's new source placement must still compose. In particular, the failed869internal cuts cannot be repaired merely by counting exterior belt lanes.

## Conservative spacing and actual default vias

Native M2/M3:18nm minwidth/spacing,31nm end-to-end/EOL envelope,20nm corner rule. For wire projection,9nm halfsignal+31nm envelope=40nm. Native M4/M5:24nm width,24nm minimum,40nm end-to-end/corner and48nm EOL extension; wide PG >25nm invokes72nm spacing-table value. We conservatively use72nm throughout:12+72=84nm. These bounds preserve native LEF facts and are NOT a claim every native rectangle needs the maximum applicable distance.

Potential-via projection expands PG metal by actual landing halfextent plus the same conservative envelope: M2 45nm, M3 48nm, M4/M5 95nm. PG cut obstacles on adjacent native Vlayers additionally expand46nm (max12nm signal-cut halfextent+34nm cutspacing). This guards any candidate via anywhere on the ray; a real routing algorithm can reclaim rays with restricted via locations. It does not replace conditional LEF58 cutclass/stack/EOL checking.

| Defaultvia | Lower metal rectangle nm | Upper metal rectangle nm | Cut rectangle nm |
|---|---|---|---|
| VIA12 |M1[-9,-11,9,11]|M2[-14,-9,14,9]|V1[-9,-9,9,9]|
| VIA23 |M2[-14,-9,14,9]|M3[-9,-14,9,14]|V2[-9,-9,9,9]|
| VIA34 |M3[-9,-17,9,17]|M4[-20,-12,20,12]|V3[-9,-12,9,12]|
| VIA45 |M4[-23,-12,23,12]|M5[-12,-23,12,23]|V4[-12,-12,12,12]|

For one registered output using M2/M3/M4: M1source→VIA12→M2local→VIA23→M3lead→VIA34→M4belt→VIA34→M3portlead→VIA34→M4fixedport. Thus a W/E M4 port path has FIVE base native vias (1VIA12+1VIA23+3VIA34); actual source/port topology may require extra bends. N/S M5 port termination instead replaces the last VIA34 by M3→VIA34→M4→VIA45→M5, adding one, six basevias. Alternative M2belt reduces layertransitions but still needs explicit legal connection; no zero-via/cap claim.

Raw native setRC coefficients: M2 R0.0297127/C0.174942; M3 R0.031287/C0.155554; M4 R0.0180365/C0.178475; M5 R0.0189935/C0.164264, perum in loadedtoolunits. VIA12/23/34 resistance0.0172, VIA450.0118. For140.4um one-axis wire: M4 R2.5323226/C25.05849, M3 R4.3926948/C21.8414376. Every real output retains80fF external cap in addition to wire and native via/fringing cap. Actual total length, via counts, native source Dcalc, slew, hold, clock phases, signal conflicts, full DRC, allnativePG connectivity and physical timing remain OPEN. Parent owns integrated finite construction; no physical authorization follows from this packet.
