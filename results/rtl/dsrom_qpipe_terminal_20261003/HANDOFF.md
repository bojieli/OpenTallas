# Native q/BF pipeline terminal handoff

R_cap0 (+2 cycles) is terminal REJECTED_NO_RESCUE. R_cap1 (+3 cycles) remains live under EPYC launcher 292373 and existing post-STA chain 292372. No new jobs, retries, source changes, or rescues were launched. The live observation is a snapshot, not a routed verdict.

Both use source 281bde911d78081d9e21939351416696ea1594a6. R_cap0 completes the tool flow but fails SS setup (-236.373921 ps), separate FF hold (-214.981978 ps), and signal integrity (4 slew / 1 cap / 16 fanout). Zero DRC does not qualify it. The driver WC hold number (-11.1767 ps) is preserved separately and must not replace the final FF result.

Worst reported SS data path is r_i2_bk to p0_wq[55] in macro lane1; worst FF path is o_val[15] to output pval[15]. Recovery/removal paths also occur in the raw reports, so this is not a reset-only diagnosis. Original reports and terminal receipts are preserved verbatim.

Actual POST_TAPCELL alignment passes for all four real 4096x274 ROMs: 1152 pins, zero offtrack, zero gridless pins. Final mapped netlist/DEF extraction retains all four placements. This matches S82 ROM geometry at 8c6d5bd7521a1a7788cd6babda624d0b5bceac36; parent clock/PG/escape/deadline/abstract qualification is still absent. Final ODB/V/SDC/SPEF/GDS remain at their original remote paths with hashes; no qualified LEF is delivered.

No BF element route launcher was found in the read-only local, EPYC, VM128, or PVE1 process checks. The retained c8 record is historical DRT-0255 failure and has no abstract; it is not a verdict for current S82 or a repaired BF successor.

Selection remains empty. The inherited differential does not independently prove the configuration decoder or full arithmetic oracle; both compared namespaces retain the historical decoder problem. Necessary next hierarchy is a source-bound mandatory-decoder/full-oracle functional gate and measured performance gate on the proposed successor before any additional element closure. The zero-extra-cycle x-need lookahead model dbdf10638c4a4106554c1b0fe1598728a78c1b29 remains model-only, not a rescue or selected abstract. No stage/die/rate rows were regenerated.

Replay: python3 tools/assess_dsrom_qpipe_terminal.py --output /tmp/qpipe-selection.json
Tests: python3 -m unittest discover -s tests -p test_dsrom_qpipe_terminal.py -v
