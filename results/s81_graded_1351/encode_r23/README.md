# S81 graded-mesh encoder receipts (S81-CORES-R23, 2026-10-27)

Encoder `tools/s81_dv/graded_mesh_encode.py`, renderer `tools/s81_dv/graded_mesh_render.py`, tests
`tools/s81_dv/test_graded_mesh_encode.py`. Input: Codex p128_stage18 (graded_metal.json sha 5bb26a05...), plan
pd14 die_plan_phy_contents.json sha 5b91b798... (immutable). Runtime intel1:/srv/opentallas-scratch2/claude/s81-graded-enc-r23/{enc1,enc2}.
Geometry only; physical_encoder_qualified = False.

- enc1 (Codex rail axes, drawn rail shields): FAIL. The actual die PG (die_infra.pg_rects on the plan) alternates VDD/VSS
  every 4.32 um (0.48 um core, 1.92 um VDDPHY/VSS in PHY domains); graded_mesh_physical.axis() assumed one stripe per
  8.64 um. Result: 4683 shorts (1257 rail-PG), 25442 spacing, 294 rails < wide-row spacing to PG. Drawn rail shields do not fit.
- enc2 (`--gap-snap`: every rail moved to the centre track of its ACTUAL 4.32-um PG gap, max move 1.52 um, mean 0.62;
  same rails/widths/segments/via arrays/attachments; PG stripes both sides = rail shields, 12.7a pg mode): metal shorts 0,
  via-outside-incident 0, PG-gap sharing 0, graph 1 component / 36481 = expected cycles, bank/stub ties 0 errors, tree
  re-route 18270 nets / 77079 segs / 0 plan errors. Remaining FAIL: 1422 M8 rail segments in 1.92-um PHY PG bands
  (2.40-um gap) are 0.40..1.76 um wide and miss the 1.0-um wide-row spacing (gap 0.28..0.96 um). Fix needs a design
  choice (cap graded width <= 0.32 um inside PHY PG bands, or route those rails around the PHY domains).
- Not yet encoded: junction VIA89 collector->rail / VIA78 riser->collector shapes (attachments + 48021 M1-M7 pin stacks are
  recorded only), VSS shield ties, forbidden-area census beyond PG, extraction/EM/IR/timing.
