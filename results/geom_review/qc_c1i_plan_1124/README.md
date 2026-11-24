# QC C1i plan review

Exact source 3e46ebd69a971444d5b2ed36fa06557680fa3714210e2bdb2fe16dc1bd01b362 on epyc9 QC-ALLFIX/cI. G0 reports zero errors and zero pending views across 377 partitions and 130 types. Peak die cut ratio 0.2369 and partition segment ratio 0.5336.

The [plan region view](c1i_changed_regions.png) highlights the 41 physical partitions belonging to the 14 changed types relative to C1h. The edits occupy the center strip and west CB banks. This is a plan-level view. Each affected kit still needs its exact placed geometry reviewed before route or STA.
