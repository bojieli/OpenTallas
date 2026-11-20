# HEAD r13r reset landing geometry, 2026-11-20

Viewed the exact [candidate reset anchor map](head-r13r-reset-exact.png) at plan SHA256 `eccfe487c2329b1d387e1c75903edab804c64310e27d163a01812055aeea7d77`. Architectural BTerm faces, type outlines, macro boxes and the reviewed clock rows were unchanged in this remap.

- LEP raw-reset export changes move four distinct anchors. The changes stay within the central corridor, top-center slot and right-side bay. On the central shelf the two preserved nominal writer START anchors for fault and LW cross a macro edge. The pinned generator relocates both complete groups to y=665.568 µm with no hard-core overlap.
- Six SerDes exports moved along the south face below the SRAM and channel macro cluster. None of their target points overlap a hard macro.
- All eight remapped host-west consumer anchor positions stayed fixed in the plan. In the two nominal macro-edge cases, the pinned generator places the complete coll_i0 first START group at x=274.344 µm and local reset k2 at y=365.040 µm. The resulting rectangles clear the modeled hard cores.

The inherited 405-µm START scan passes for these three types. For the next event's 300-µm design target, exact emitted-region Manhattan results are LEP reader 354.0 µm (four branches), writer 380.1 µm (five), SerDes reader 388.0 µm (one), writer 337.5 µm (one). Host-west reads 286.6 µm and writes 268.9 µm. The 300-µm RST-FAN-1d local reset tree and the 405-µm die START checks cover different paths.

Source-only preview GEN is queued for the three exact candidate kits. Review their emitted geometry before P&R. CTS, east-aisle GRT and placed per-bit reach remain open.
