# S81 H2 recovered-clock model review — 2026-11-13

Existing E9 hold-tap-1 lane; no new worktree, RTL, domain or clock constraints.

Viewed actual terminal H2 PLACE images at `/srv/opentallas-scratch2/claude/hard-s81-serdes-1/kitH2/gen/serdes__t2/run/layout_review/place/{layout,density}.png`, then viewed `/srv/opentallas-scratch2/claude/hold-tap-1/secondary_clock/s81_h2_recovered_density_model.png` (source marker explicitly visible). Model JSON and direct source/geometry TSVs are beside it. Exact input is terminal H2 `run/results/asap7/dp_serdes__t2/base/3_place.odb`; captured RST_TREE=1.

Actual DB source connectivity: existing io_pma_rck[0], STA clock io_pma_rck, 833 ps. 28,371 DFF clock endpoints plus five macro clock pins: RXM pma_rck, decoder cmem clk, dmem wclk+rclk, dchn clk. All remain on their original source. Ordinary clk has 20,520 direct DFFs and TXM ck; the fclk source has 17 direct DFFs plus a buffer (not a full downstream census). Dump qualifies these as source-net connectivity, not independently measured propagated arrival attribution.

Proposed canonical density clustering has 114 local cohorts, at most 887 FFs, maximum medoid-to-sink L1 radius 79.866 um. Decoder cohorts occupy the existing west pocket around the three decoder macros; a narrow recovered RXI band still spans the full analog shore. Macro clock pins and source coordinates are actual DB locations. Medoids are models, not final legal buffer placements; existing macro channels and local density require actual runtime placement/radius/load checks. Final canonical F4/interface assignment can change membership.

The long source-to-leaf trunk remains unmeasured. No global insertion, macro/FF skew, native eye, timing closure or SIGNED claim follows from local cohort bounds. If HEAD's one density-tree pilot shows residual trunk failure, use an explicit selected-source bounded trunk with ordinary-root CTS protection; the old shallow_clock wrapper alone must not drop other clock roots.

Verdict: ISSUES-ACCEPT for this model only; HOLD before S81 physical adoption. H2 LEC failed from OOM and its 128 GB proof retry is owned by wave/S81; no CTS before proof recovery. S81 has no authoritative incoming TX/CDR arrival eye contract, an OWNER? already logged by S81. Receiver positive-edge capture is proved, but HEAD's eye numbers cannot be transferred. External eye remains UNQUALIFIED. No kit was mutated, no S81 CTS launched, no cycles added.

Read-only census used exact kit image openroad/orfs:asap7lock via ot-run E9 unit oth-ubuntu-1440195-1794615368, exit0. Model units oth-ubuntu-1456191-1794615493 and source-marker redraw oth-ubuntu-1466202-1794615564, exit0. Current HEAD composite canary remains the sole physical recovered-tree pilot.
