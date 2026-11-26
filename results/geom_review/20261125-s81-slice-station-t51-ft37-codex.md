# S81 slice station t51 FT3 and FT7 seat review

2026-11-25 PST. Viewed the retained attempt 9 exact placed density with the proposed FT3/FT7 bank locations overlaid. The north landing bands and outside pin axes remain densely packed. The first new FT3 and FT7 packs sit in open interior space under their corresponding landing rings. Their lower ranks sit beside existing strips. The proposed FF footprints clear the fixed cells in the retained database. The open lower lanes can accept a placed-density measurement with the new banks.

The retained netlist's virtual capture-distance replay moves 3,168 existing payload and epoch FFs. It reduces 576 captures above 405 µm to zero and the overall maximum from 498.12 to 401.54 µm, with all five emitted ranks per slot. The relay collapse count in the same replay drops from 486 to zero. E7 draft artifacts are `QC-DRT-ECO/t51-ft37-private/{ft_stations.txt,ft_bit_sites.tcl,receipt.json}`.

Release the copied attempt for a placement-only screen after the station table guard checks the emitted depth. Require placed pin-reg, partial-face, fill, empty-area and reach review before route.
