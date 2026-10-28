# enc8 — shield-full + PHY VSS stripe-end abutment (COORD R24 ruling (c), option (a))

Flags: `--gap-snap --phy-clip --shield-full --phy-vss-abut` (intel1 run dir /srv/opentallas-scratch2/claude/s81-cores-r25/mesh/enc8;
plan die_plan_phy_contents.json sha 5b91b798..., build codex-s81-graded-1351/p128_stage18 = enc7 inputs). 3:32 wall, 1.07 GB.

Status: ENCODED_CENSUS_PASS, fails [].
- Shield census: 145,158 sides shielded, 0 unshielded (enc7: 144,780 / 378 sides, 270.3 um).
- Change vs enc7: exactly 450 drawn VSS shield strips extended by 0.6-0.65 um to end at the PHY-domain VSS stripe end
  (same net); 0 shields added/removed otherwise; mesh, vias, tree, ties, PG identical (metal shapes 410,012 both; pg_rects sha equal).
- Same-net waiver scope: 450 shield strips sit < 1.0 um (min 0.76 um) from a PHY stripe, ALL VSS; 0 shield/mesh shapes
  < 1.0 um from any VDDPHY/other-net PHY stripe (phy_band_findings same_net_ok=False on non-VSS = 0).
- metal shorts 0, spacing 0, PHY-band (mesh + shields vs other-net PHY) 0, via-outside 0, rail ends off-via 0,
  graph 1 component (36,094 cycles), tie/tree-plan errors 0; ties 11,757 VIA89 / 933 groups / 0 floating.
- Width cap unchanged from enc7: 1528 ck_mesh segments 1.68/1.76 -> 1.6 um (287.9 mm = 2.7% of 10,503 mm rail), R +10% max/segment.
  These are CLOCK-mesh rails (net ck_mesh); the die PG grid is not touched by the encoder.
- Renders: zoom_11 (M8 0.08 rail, side +1 abut at x 3482.88), zoom_12 (M9 0.08, side -1 at y 1115.52),
  zoom_13 (M9 0.16, side -1 at y 23629.44), zoom_7/8 W/E PHY clip ends, die_full_metal.
