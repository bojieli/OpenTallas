# Actual original-slot gate: FAIL, no unchanged retry

Source7110ec4a7 exact dsfd_hstnh_1024, original17.256x53.976um outline. The auto-admitted EPYC4 gate completed and refused during pre-placement anchor packing, before CTS. 1024 actual sinks are present; no measured clock insertion/spread or native setup/hold/DRC qualification exists.

The exact error is `OT_ANCHOR_PACK: no legal free row site for u_0.o_d[248]$_DFF_N_`. The generated source is functionally proven at20,0001024-bit words, including all1024 basis vectors, with actual wrong-edge and payload mutants rejected. Its original physical placeholder is too small for the required boundary implementation.

The actual IO ODB contains354.13362um2 standard-cell area and637.68546um2 row-site area. The gate inserts2048HB2 cells and3072BUFx4f cells in input/output hold stages. Geometry from that same actual database gives an additional507.61728um2, for a lower bound861.75090um2, or135.14%of available rows. This excludes future CTS and required whitespace. Packing or density tuning cannot resolve an absolute area excess. The isolated read-only capacity audit was admitted as EPYC4 unit167218, exit0; no failed snapshot or native source was modified.

A read-only countershape screen34.56x53.976um was explored before root stopped further geometry trials. Fixed E anchoring collides at four of81 instances. A mixed-anchor/two-translation screen can place all81 with zero rectangle overlap/outside, preserving all other boxes. It still lacks every incident pin/route/cut/clock check and is explicitly NOT_ADOPTED. ROOT instructed that the dependency is to be handed to Claude; no countershape gate or generator was launched. A larger leaf cannot inherit the old physical contract.

Next: establish a real slot and all81 incident placements, include clock/PG/track access and wire-stage timing, then qualify the explicit changed geometry. Keep this failure and the original immutable current GEN jobs. No recipe1/hold-stage bypass or timing threshold relaxation was used.
