# Reviewed native-clock density canary

LOOKED at review.png before CTS. Scoped clock-plan PASS-COND: preserve all9native input roots independently, use unique tap namespaces, keep4macro-only roots, place density taps in actual standard-cell spaces, and run common postCTS alignment. No clock inputs merged; no RTL/period/uncertainty/cycle change. Full tile data/channel failures remain explicit.

Both independent CTS-only canaries returned0 on the original source f1a8dcffa6e / VMS f50d62432a5f. BUFx12 alignment delay cells measured TT placement-RC tapmean491.6..511.3ps =19.7ps spread (<=20 planningtarget). BUFx24 measured497.4..517.8=20.4ps, MISS and not selected. Each retains12212sinks,0unrooted,9native roots including4macro roots, and0trace errors. Actual own-driver clockleaf reach65.83um passes the220um CTS gate in both trials. This is not routed pin-to-flop skew or SIGNED timing evidence; TT setup/FF hold and80ps routed relatedpair skew remain owed. The informational intermediate clockleg249.59um is preserved.

Reproduce selected delay quantum with existing `--orfs-var OT_DTAP_DELAY_CELL=BUFx12_ASAP7_75t_R` alongside `--clock-taps density --clock-density-contract contract_density.json`; contract enables the opt-in calibrated alignment step. No recipe/default has been changed to enable this flow. Production adoption requires the exact module/native clock profile and rendered plan review.

Actual self-contained kits epyc2:/srv/opentallas-scratch2/claude/codex-hbm-multitap-1101/{density_b12,density_b24}. Controllers intel2 PIDs2096407/2096408, both DONE. Geometry dumps are cts_geom.tsv, raw logs cts.log, cts.rc. Fulltile signal route uses a separately repaired data placement and is still running50iterationbudget; no DRT launched.
