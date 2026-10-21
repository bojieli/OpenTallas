# Actual q8a net42538 read-only diagnosis

One existing approved saved-ODB query ran ep7 unit1519212-1792620737, exit0, memory8GB/oneCPU. Same TCL/wrapper3f69d25fb, no STA/placement/repair/routing. Original and staged inputs compare unchanged before/after. Immutable checkpoint SHA7a3ef6bfd92e28c9e0db6ea949708f9720c9f8001fc247b907555333b2749e1b.

Actual net: hold42540/Y BUFx2 at(43.075..43.182,206.847..207.063)um -> _06451_/A INVx1 at(88.740..88.800,182.547..182.763)um. Driver ends18nm west of MY SRAM x43.200..77.784,y175.152..216.504; sink is east. Macro OBS M1..M3 cover fullrectangle; M4 x43.272..77.712. Adjacent lower macro ends175.128, making their24nm seam an actual narrow seam, not the intended27.3um group gap.

Saved source GCell75,363 has M2capacity/use14/14 and M4 12/12; M3 16/14 and M5 12/9. Sink155,320 has sparecapacity onM2..M5. This supports local cross-macro/entry congestion classification, not a globalcapacity-zero wall claim. The macro can geometrically be bypassed north above216.504um; source-to-top distance9.55um and top-to-sink33.85um make ~89um rectilinear detour before grid/spacing/othernets (direct~69.94um). No legal routed path is proved. Storedgrid aggregate does not preserve the last mazeheap and checkpoint dropped30 transient hookshapes.

Structural requirement before successor: actual repair/buffer placement must avoid sending a new hold segment between opposite macro sides without a reserved legal bypass and repriced hold/setup. Do not guess macro gap widening from globaloverflow0. The exact upstream chain/last transient restrictions remain unresolved; no geometry patch, reroute or acceptance claim.
