# Actual r10bfp late fault landings

Read-only bounded model of the existing final r10bfp case, fleet unit `oth-ubuntu-2849181-1792615751`, admitted 4 GB / one thread, exit 0. No GEN rerun, new geometry, reach exception or source repair was needed.

The `FAULT_EMIT late` line and the retained `unrepaired` strings describe the search before zero-stage cross-root landings. The final dump already has one stage on each supposedly open edge. The emitted actual `die.v` contains both landing instances, and the existing final pin-bit audit reports zero over 405 µm. This model resolves the intermediate/final ambiguity using the actual LEF rectangles, emitted nets and placement.

| Actual chain | Master | Native pin-to-pin hops (µm) |
| --- | --- | --- |
| d2d_rom_g3 → native59_g1 | qfd_landh0_1_ES_65x30 | 190.152, 202.200 |
| native59_g1 → sys_face_g0 | qfd_landh0_1_WE_65x30 | 239.136, 236.280 |

Both physical landing frames are 64.776 × 30.216 µm and have zero overlap against all 30,471 actual emitted frames. The emitted upstream/downstream nets match exactly; each landing ck_s matches the source root clock and ck matches the destination root clock. Their actual reset/en nets are retained. Scalar geometry is derived from the actual native LEF pin rectangles, with missing/ambiguous bit identities rejected, without a block or port centroid fallback.

`FINAL_FAULT_LAND.json` retains source/target points, all native rectangles, frames, clock/reset identities and hashes of the actual case LEF, Verilog, placement and manifest. `model.py` is the bounded reproducer. Its scope is these two final chains only. Strict native binding, the real root sink and whole-die clock/reset/timing qualification remain owed. In particular, r10bfp remains a failed full chain at static_link_bind's physical-port mismatch; this receipt does not promote it to a die result.
