# HEAD W LEP paired pin-order projection, Nov 22 11:08 PST

The 688 residual overflow in Fable W6 is concentrated along the west edge of the mirrored `u_rg2.u_pair`. The current W face has increasing payload indices in y, while the exact signed pair face presents decreasing indices. A 34.56 µm west extension through this hotspot would overlap `nst4`.

Viewed the exact pin-coordinate projection for private r18m delta `3d154782b421`. Shared `coll_WN2_u__4` and `coll_WN2_d__0` segments reverse payload indices 0–511 within each M4 or M6 layer. The payload order now matches the mirrored pair except for small interleaving differences between layers. All status and epoch coordinates, layers, footprints, interface widths and lane cycles retain their original values. The two endpoints of each directly abutted port receive one shared track map, so the parent has zero pin-to-pin displacement.

- Input projected payload crossings 130,796 → 130, mean vertical span 171.56 → 76.86 µm.
- Output projected payload crossings 130,793 → 127, mean vertical span 209.24 → 167.78 µm. The output still has 193 raw projection spans over 200 µm.
- The full-plan schema, abutment and face checks match r18m. The six existing face G2 requirements still need actual route evidence.

Artifacts are on epyc9 at `/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-1122/w_order_1122/`, including `source_plan.private.json`, `face_delta.log` and `paired_order_projection.png`. The plotted lines are geometric projections. This candidate needs ordinary private placement on both changed types to show the landing flops track the new slot order and the inversion has not moved into the nst4 logic. Route remains held.
