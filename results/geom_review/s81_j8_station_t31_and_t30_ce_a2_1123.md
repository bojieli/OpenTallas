# S81 J8 station t31 and t30 CE attempt 2

I viewed the exact intel1 layout, density and geometry overlay for both placed attempts. Both stay BAD for the named placement defects.

- `slice_station__t31` has 116,720 cells, max 360.75 µm data/relay hop and no missing nets. The south receive START pins ft3 and ft2 land 191.76 and 146.3 µm from their first capture. Other data captures top out around 89 µm, with longer p90 across the south bus. Move the two first START captures into their actual face band while retaining source reset and path depth. The two dense south strips and east landing also require the standard placed tap-cap check.
- `slice_station__t30__clcedefe91` has 25,406 cells, max 278.1 µm real sequential hop, and the same west monitor placement error already reduced by the staged row on t30 cl6a190133. Actual ready and fault distances are 253.2 and 254.86 µm. Its sparse far northwest branch is 416.47 µm from the nearest drawn clock entry and needs a named local tap review. A typical large raw central clock leg is excluded from these substantive reasons.
- Retained prior diagnostic GRT overflow is zero in both placed kits. Both candidate forms need fresh viewed placed images before routing.

Exact intel1 kits are under `/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items`, each item `attempt_2/gen/<type>`.
