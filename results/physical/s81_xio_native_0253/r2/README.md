# Corrected XIO r2 CTS diagnostic

Source643419d7d, exact independent leaf kitsd29000ff7 (request RLAT15). Eight differential configurations and six mutants plus common-epoch warmreset proved in results/rtl/s81_xio_partition_0253; added independent fixed-scheduled gather phase queue proof and three observed mutants at b840d17ca. Fixed deltas request+2core, collective return+4core, Q/G+4core/+3serial, tuple0/II unchanged.

| Leaf | TT launch ps | TT capture ps | Boundary spread ps |
|---|---:|---:|---:|
| request | 187.10027 | 143.08627 | 24.3 |
| return | 193.58717 | 185.21675 | 43.8 |
| serial | 167.27900 | 123.33573 | 2.3 |
| fault_join | 171.84704 | 143.27314 | 1.1 |

Actual measured insertion references and zero combinational boundary pins for all four. All-layer CTS ODB PG census records M1/M2/M3/M5 only for VDD/VSS; no M6+. Initial PG attempt used the wrong design subdirectory and failed before opening an ODB; failed logs are retained beside corrected complete logs. Exact actual ODB4_1_cts, same as native timing probe, was audited.

Personally viewed actual floorplan.png and density.png pairs in all four physical/ref_tile/dsfd_vm_xio_*_native_1016_r2/gate_layout directories. Request has compact W cluster with a thin diagonal clock/control chain toward N clock and its own E capture. Return has W input pin wall, E output pin bands and intervening mux cells; it has4687 CTS sinks. Serial/join are compact43.2um diagnostic leaves. These images precede detailed route; no native routed closure claim.

R1 remains rejected on capture276.58174ps; r2 true request input capture reduces it to143.08627ps without changing Q/G phase delta. No cosmetic shape changes or clock relaxations. Complete final graph, exact homes, all-incident cut and die clock delivery still pending the combined70-source XML. Wholehub alternatives remain die/root-owned and held.
