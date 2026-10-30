# Selector k26 A/B placement review

Independent reviewer Codex GEOM, 2026-10-30. Viewed both a.png and b.png. Verdict: **FAIL STRUCTURAL; no CTS/route**. These are placement-only diagnostic renders of the inherited actual geom.tsv; GRT50 was still running and its final verdict is NOT RUN in these receipts. A 600.048 x 450.36 um, B same outline. No thresholds or source changed.

A: two tall SRAM columns block the middle of each half, leaving most logic in the W/E strips, central street, and N/S bands. Fill .2658, empty .3498. The added 9 clock/reset islands improve entry reach to 205.20 um; the old corner-clock finding is therefore superseded on this kit. The decisive failure is 9,091 captures >405 um, worst 906.88 um u_fcore.pass_r[0] -> u_fcore.core.hist[236][2]. Output relay collapse remains75, worst selected_line[1644] -> u_bout_selected_line/q[1644], a 2-hop chain with one407-um hop.

B: distributing SRAM rows over the full height opens much wider horizontal streets and produces one contiguous logic region (empty .0748). It reduces failing captures to5,496 but worst remains823.66 um gq[2].fill[4] -> gq[2].buf_q[1121]. Its reset input first register is222.88 um away (A129.22); output relay collapse18, worst selected_line[1652] -> u_bout_selected_line/q[1652], 2 hops with411-um dominant hop. Clock entry reach205.74.

Required structural next step: give each gq/buffer quarter local control and local reset/state registers, place each quarter's data and state together, and assign output pipeline stages explicit street sites. If control distribution requires new registered hops, price the latency and prove lockstep+mutant before adoption. Moving macro rows alone cannot resolve the long control/state/data combinational cones. Maintain M5 route ceiling. Channel estimates are diagnostic until the inherited GRT50 finishes.

The placement-only invocation omitted the typed FT interface metadata: its36 mp_isl clock/reset pin-unregistered flags are not judged as data-pin failures here. Resolve using the kit's declared interface on its final AUTO-GEOM, without widening exemptions.

Sources: intel1:/srv/opentallas-scratch2/claude/hbm-cores-kits-26/selector/ot_hbm_idx_selector_static_sel_a8b6d07217f0-_k26{a,b}/rev/geom.tsv. Artifacts here are independent diagnostic outputs, not replacements for the author's pending GRT-backed verdicts.
