# S81 graded-mesh encoder receipts (S81-CORES-R24, 2026-10-27) -- COORD ruling 1 (PHY PG bands, VSS-only PG shields)

Same inputs as R23 enc2: Codex p128_stage18 (graded_metal.json sha 5bb26a05...), plan pd14 die_plan_phy_contents.json
sha 5b91b798.... Runtime intel1:/srv/opentallas-scratch2/claude/s81-graded-enc-r24/{enc3,enc4}. Geometry only;
physical_encoder_qualified = False.

- `--phy-clip`: every literal rail segment whose metal (incl. piece-end pad extension) is < 1.0 um (2-D edge distance)
  from a 1.92-um PHY PG stripe is dropped; each piece is trimmed back to a live VIA89 crossing (0 ends off a via); vias
  that lost a rail are dropped; floating pieces dropped (0 here); attachments that lost their rail move to the nearest
  kept rail point. Result: 747 segments clipped + 18 trimmed, 378 vias dropped, 0 rails removed, 8 attachments moved
  (4 driver banks, 4 stubs, max 10.9 um), 1 component, cycles 36481 -> 36094.
- enc3 (`--gap-snap --phy-clip`): ENCODED_CENSUS_PASS -- shorts 0, spacing 0, PHY-band mesh 0, via-out 0, gap-fit 0,
  tie errors 0, tree plan errors 0. Shield accounting (ruling: VSS PG may count, VDD never): VSS side counted on every
  segment (72579); VDD side UNSHIELDED on every segment (no drawn shields in this mode).
- enc4 (`--gap-snap --phy-clip --vss-side`: rail at legal wide-row space from its VSS stripe, drawn VSS shield on the
  VDD side stepping with the grading, cut >= 1.0 um before PHY PG and at width steps): metal shorts 0, spacing 0,
  PHY-band mesh+shield 0, via-out 0. VDD side: 52103 segs fully shielded + 7650 junction-trimmed; MISSING 10020 segs
  (1429 mm) + 2806 partial (164 mm): (a) graded rails >= ~1.44 um wide (a drawn shield needs 1.0+w+1.0+0.16+0.08 <=
  3.84 um, i.e. w <= 1.6 at the VSS-side axis) and (b) 0.08-0.16-um rails inside PHY domains (2.40-um gaps beside
  1.92-um VDDPHY: no room for a drawn shield at the 1.0-um wide row).
- phy_band_other_info 95 = router-placed tree/tie metal within 1.0 um of a PHY stripe end-on/perpendicular (census
  wide rule legal; info only).
- Open (unchanged): VIA89/VIA78 junction shapes, shield ties to the VSS grid, M1-M7 pin stacks vs signal routing,
  extraction/EM/IR/timing.
