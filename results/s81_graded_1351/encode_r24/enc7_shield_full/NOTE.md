# enc7 — shield-full (COORD ruling (c))

Flags: `--gap-snap --phy-clip --shield-full` (intel1 run dir s81-graded-enc-r24c/enc7).

Status: ENCODED_CENSUS_FAIL, sole fail `shield_sides_missing`.
- metal shorts 0, spacing 0, PHY-band 0, via-outside 0, rail ends off-via 0, graph 1 component, tie/tree-plan errors 0.
- Width cap 1.6 um: 1528 segments narrowed (1.68/1.76 -> 1.6), R +10% max per narrowed segment, VIA89 cuts 1,963,176 -> 1,950,504.
- Shield census: 144,780 sides shielded, 378 sides unshielded (270.3 um total), all on 0.08/0.16 um PHY-domain rails;
  lengths 0.6 um (300), 1.2 um (72), 0.65 um (6) at PHY-domain VSS stripe ends where a drawn VSS fill would have to sit < 1.0 um (2-D) from the PHY stripe corner.
- Shield ties: 23,247 shapes, 933 groups, 11,757 VIA89 ties, 0 floating.
- Renders: zoom_7 W-most PHY clip end, zoom_8 E-most PHY clip end, zoom_9 VSS-side fill + bridge at PHY/core hand-over, zoom_10 1.6-um M8 rail with drawn VSS shield.
