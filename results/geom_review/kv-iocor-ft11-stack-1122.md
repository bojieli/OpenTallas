# IO corner ft11 clock-stack clearance

I viewed the overlay of the permanent clock-tree obstruction and the exact `ft11_i` pin shapes. The old D26 FF GRT checkpoint and TT routed checkpoint agree on the obstruction. It occupies the pin shapes of bits 2 through 7. The FF DRT stops at the input buffers of bits 3 and 7. The TT detailed route reports six DRCs in the same interval.

The selected D28 post14 plan (`5f76a4cc2ed9`), the D29 m7 carrier (`588415920bef`), and the E9 band B specimen (`kv3_io_cor_v1_1122092146`) all have the same re-seated clock stack. The type-local `clock.reserved_sites_um` row changed from `[1277.154,517.860,1278.720,518.940]` to `[1275.102,517.860,1276.668,518.940]`. The `stack_um` rectangle equals the row bounds and keeps layers M3–M7. The base reservation keeps M1–M2.

The generated E9 obstruction ends at x=1276.704 µm on M4/M5 and x=1276.672 µm on M6/M7. The affected face pin boxes begin at x=1278.528 µm. Bits 2, 4, and 6 are M4 with 1.824 µm clearance. Bits 3, 5, and 7 are M6 with 1.856 µm clearance. Both plans reproduce all 522 E9 `ft11_i` pin coordinates and layers, including the matched `L664_1` bus window. Carry forward the existing reservation row as-is. No signal pin, PG, landing-band, or cycle change is required for this overlap.

This review establishes clearance to the measured permanent obstruction. E9 band B detailed-route timing and input-buffer access are separate open measurements. No new route was submitted. Evidence is available under Intel2 `/srv/opentallas-scratch2/claude/tap-grid-r4/kv_iocor_ft11_1122/`.
