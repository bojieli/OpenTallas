# S81 J8 t6 and t38 placed station review

Viewed 2026-11-23 09:05 PST.

## slice_station__t6__cl0755c26e

**PASS-COND**

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t6__cl0755c26e/gen/slice_station__t6__cl0755c26e
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t6__cl0755c26e/geom/auto_geom.png
- Clock and landing groups along the north-west corner and bottom align with separate relay strips. The plot shows clear lanes among the strips. Max pin capture 74.04 um, register hop 391.34 um and planned clock reach 262.89 um. The cap estimate reaches 1500. Run ordinary CTS and route limits.

## slice_station__t38

**PASS-COND**

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t38/gen/slice_station__t38
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t38/geom/auto_geom.png
- The north pin banks are distributed across most of the width. Staggered relay bars leave passages across the core. The central demand estimate reaches 0.704 at (720.0,617.5) um, and the completed placement congestion diagnostic has zero signal overflow. Max pin capture 98.38 um, register hop 378.65 um and nearest tap distance 396.15 um in the southeast. Apply ordinary CTS clock and timing gates, especially at the full tap and southeast edge.

## slice_station__t6__cl54a9ceeb

**PASS-COND**

- Exact kit epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t6__cl54a9ceeb/gen/slice_station__t6__cl54a9ceeb
- Viewed epyc8:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/891100ef774/items/slice_station__t6__cl54a9ceeb/geom/auto_geom.png
- Multiple north launch groups connect to discrete west and east relay columns with open space between. Max pin capture 126.86 um at cland_fstart_in_ft12_i[0], below the 150 um hard backstop. Register hops max 353.92 um and planned clock reach 258.74 um, with estimated largest tap at the 1500 cap. Retain normal CTS and route checks.

Each exact pre-CTS hook sources clock_taps.tcl to reassign raw placed clock nets.
