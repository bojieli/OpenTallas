# QC and KV die prototype review

Opened the exact die outlines and TT route-guide demand at epyc12 `DIE-PROTO/views_1125`.

- QC C1o `aa3a14fb7484`. Reviewed the floorplan, congestion and hop renders. M4–M7 demand is concentrated in the middle provider strip and the west collector seam. Maximum raw track use in 200 µm bins is 46.1% on M7, 34.7% on M8 and 40.5% on M9. The abstract die views support a nominal advisory STA read using the already routed clock arrivals and the corrected wall-aligned count plan.
- KV A5t8 `6cd026683af9`. The horizontal hub band carries the cross-die fanout. M7–M9 show the busiest north–south paths along the PV/HGI pair columns, with stressed bins near the hub seam. Maximum raw track use is approximately 45% on M8 and 54% on M9. The inherited CA run has measured hold failures of -5.58 ps intra-partition and -26.82 ps landed. Type reviews and routed timing remain separate qualification gates.
