# QC node structural CTS fallback: placement trial review

Image viewed: results/codex_qc_a0_2340/node_a0k8_clocks.webp (actual completed node a0k8, same RTL/outline/pins).

The 47.52 x 432 um slot has continuous legal logic rows and local arithmetic groups along its height. The symmetric frozen lattice routes numerous long spine legs through the same narrow centre corridor and leaves load spread 2..101 sinks/leaf; actual propagated clock window is 43.31 TT / 44.31 FF versus planned 16.97/15.95. DRC0, PG0 opens and data reach max243um establish no macro-wall or missing-relay failure. Worst FF register path is u_w.q[644] -> g_add[4].x_code[4]; repeated internal hold failures remain despite the symmetric topology. The centre M5 entry and all data pin positions stay fixed in the successor.

Verdict PASS-COND for PLACEMENT TRIAL ONLY with native sink-clustered TritonCTS (authorized fallback in QC-A0-KITS-9). This replaces the frozen unequal-load leaf assignment with CTS clusters derived from real sinks; two-mode TT setup/FF data hold repair remains enabled. Placement and CTS/GRT must be reviewed before detailed route. No clock/uncertainty/IO budget change; no RTL/cycle change. Existing GEOM46 aspect and partial-face conditions still apply.
