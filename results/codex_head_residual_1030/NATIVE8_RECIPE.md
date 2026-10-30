HEAD hd_tile native8 explicit kit attachment

Source: measured reviewed native8r DPL PASS0; pin p90 29.27um/max144.32um. Old wrapper overall G1 remains FAIL (old landing paths/taps/comb placement). No route approval.

Only adopt band metadata clock.landing_contract.bands.i.rect_um [12.96,708.48,47.52,1008.512], previously [17.28,708.48,47.52,1008.512]. Same outline, pins, macros, data cycles (0 added).

Copy head_native_pack.py,head_native_hook.tcl,install_head_native.py together. Install into an OWN generated ROOT88/R3/R1/W3 kit:

python3 install_head_native.py KIT --geom-tools CURRENT_GEOM_TOOLS [--core-hook tile4_hop.tcl]

CURRENT_GEOM_TOOLS contains geom_dump.tcl and geom_rules.py. Installer copies these into kit, inserts explicit u_cland_i override after helper definition/before calls. All other prefixes use unchanged helper. At actual PRE_GLOBAL_PLACE, override dumps current DB, derives actual typed captures and global-bit correspondence from source native RTL chunk equation, then writes/sources deterministic placement Tcl. No copied old netlist names are used by native generator. NEW wrapper remains independently subject to G0C/clock/fullG1.

Guards: exact band rectangle; actual native chunk formula; 568 live global bits each four writer slots; 568 matching read FF; 26 additional FSTART controls; total2941 ringFF; origin6FF. Source logical paddedwidth576 has8 optimized constant readbits: physical read568. Writer2272 plus26 FSTART controls=2298 forwarded-clockFF. Complete ring inventory2941=2272+568+36selector+65othercontrol. All actual ringFF covered once; unknown source/netlist shape errors immediately. Generated JSON records actual source RTL and current DB dump hashes.

Write strip12.96..22.14, y742..990; monotonic actual pin-Y targetminimum .27; FSTART26control x17.28..26.46 at actual inputY+-4.32. Matching read globalbit x32.4..47.52 same targetY+-1.08; selectors near actual mean own chunk pins.6originFF at alreadydeclared START capture rect509.76,854.304..527.04,871.584. Packing uses shared cland_put (hardblocks and clockreservations occupied). Installer backports hardblock occupancy only if helper lacks it (x,y,w,h signature).

Full core hook tile4_hop.tcl is separately nameguarded, actual old core graph same RTL; fail if any moved core instance disappears. New R1/R3/W3 landing not covered by old hook and use source-generated normal constraints. Full fresh GPL launched separately, never claim old-wrapper route.

Core placement follow-up profiles (conditional, no full G1 approval): tile5_hop fixes the sole unconstrained two-stage fault pair at centralV; broad A/B skew groups fill existing free bays by area; existing merge band expands internally330..380→330..430 in same Hstreet. Tile6_hop adds sibling tile6_repack.tcl: permutes only actual same-master+clock-root occupants at identical sites to bit-major16-lane order. ActualDPL0,0core hops>405, nativepin29.27/144.32 unchanged,25879root bins EXACTLY equal tile5. Actual19,264buffer/inverter-only skewedges total1,152,192→571,996um;mean59.81→29.69um. ProductionW16 source syntax guarded. Installer --core-hook tile6_hop.tcl now also copies required sibling tile6_repack.tcl. Canonical newR3/R1/W3 still requires fresh complete G1/clock; old72landing paths and oldtapprofile not routed. FreshGPL6 client2417405 with automatic collector2441081; lexicalGPL5 explicitly superseded/stopped, not policyFAIL.
