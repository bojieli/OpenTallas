# SU1 balanced B native floorplan and ONEPLACE — 2026-11-08 04:20 PST

Parent /root/qc delegated earned B floorplan review and ONEPLACE only. Source codex/qc-su1-physical-0222@3c01955e7ad. Kit intel2:/srv/opentallas-scratch2/claude/codex-qc-su1-physical-0222-run2/gen/qfd_qc_su_lane_w_l4_mem9_balanced_b. A's compact planning FAIL is preserved. No new source, CTS, route or duplicate LEC.

## CODEX notes

VIEWED native 2_floorplan.odb layout/density/PDN PNGs (local /home/ubuntu/codex-qc-su1-review-b-0222/; remote intel2 /srv/opentallas-scratch2/claude/codex-qc-su1-place-b-0222/review_floorplan/). Native outline319.68x298.944, designarea32344um²/36% util. Two west MY SRAMs, clear clock entry,1010 pins. Actual hard standard-cell dbBlockage spans intermacro gap6.912,146.040–40.632,156.864; routing/PDN remain allowed. Halo placements clipped to native core. Viewed native PG grid; both macro VDD/VSS terminals connected; clock-PG same-layer metal overlap0. Pre-PLACE density flag3.785 is unplaced-cell artifact, not an actual placement verdict. Review.json PASS for ONEPLACE only; no clock/route/signoff claim.

One read-only PDN render failed on a Tcl whitespace typo and left the GUI active; stopped only own exact named container, corrected script and rerendered. Failed log retained as pdn_render_try1.log, successful try2 retained. A local admission pick failed localhost SSH authentication; launched nothing. Correct intel2 client used next.

Actual ONEPLACE admitted intel2 unit oth-ubuntu-2461883-1794140343,32GBcap/8T/disk4. Controller codex-qc-su1-balanced-b-place-0222.service. Own run area intel2 /srv/opentallas-scratch2/claude/codex-qc-su1-place-b-0222, dispatch.log/place.log. Direct native make do-place, no run_kit make-chain and no resume.json/guard override.32 exact input hashes passed before launch, reused mapped netlist6206dc5ba25e…; same source proof remains with parent's existing A LEC unit552110, not duplicated.

Next: collect actual PLACE result, view its native density/macro/pin image and diagnose any failure. Recheck input guards after completion. No new PLACE of unchanged B; no CTS/route without parent assignment. B's new parent-slot adoption remains unqualified.

## Handoff to Claude 2026-11-08 04:22 PST

STOP NEW LAUNCHES received from /root/qc. No further checks or waits performed. All edits/scripts are complete; healthy B PLACE is left running.

- Active own job: intel2 oth-ubuntu-2461883-1794140343, controller codex-qc-su1-balanced-b-place-0222.service, docker codex-qc-su1-balanced-b-oneplace.32GBcap/8T/disk4. Native make do-place only; no CTS/route/new LEC. Last read showed active global placement; NOT a terminal result.
- Kit intel2:/srv/opentallas-scratch2/claude/codex-qc-su1-physical-0222-run2/gen/qfd_qc_su_lane_w_l4_mem9_balanced_b; source codex/qc-su1-physical-0222@3c01955e7ad. Own runner/guards/input manifest and dispatch.log/place.log under intel2:/srv/opentallas-scratch2/claude/codex-qc-su1-place-b-0222.32 input hashes passed before launch; mapped netlist6206dc5ba25ee00d343f5fce2108ceacaaeb62f6f1b8fb11984b93c508120d23. Runner checks inputs again after exit and refuses any repeated stage3 attempt.
- Native earned floorplan review PASSED for ONEPLACE: actual2_floorplan.odb rendered and VIEWED layout/density/PDN; outline319.68x298.944, designarea32344um²/36%util, two west MY SRAMs,1010pins, actual hard standard-cell dbBlockage in intermacro gap. Routing/PDN remain allowed. Halo clipping confirmed in actual DB. Both macro VDD/VSS terminals connected; clock-PG same-layer metal overlap0. Native pre-PLACE density advisory is an unplaced-cell artifact, not a placement result. Remote review images, dump, review.json and PG probes are under own run/review_floorplan; local viewed images /home/ubuntu/codex-qc-su1-review-b-0222. A's compact planning FAIL untouched.
- Diagnosed tool issues: first read-only PDN render had Tcl whitespace syntax error; stopped only own exact GUI container and retained failed log, corrected try2 passed. Local localhost admission probe failed SSH auth and launched nothing; correct intel2 admission client launched the one real job. No unhandled failures in this collection.
- Next: collect B PLACE terminal status and post-run input guard, view actual placed density/macro/pin geometry, diagnose any failure structurally. Do not retry unchanged B, continue CTS/route, or duplicate parent's existing same-netlist A LEC unit552110 without a new assignment. Parent slot adoption remains unqualified.
- Earlier completed source/proof heads: SU1 codex/qc-su1-prod-0222@1d0a060077e on intel1 ownrepo; FIFO2 codex/qc-cal-fifo2-0222@88a99cfa19d on intel1 ownrepo. Numerical proofs, real-macro mutants and baseline/EXTRA9 production elaboration all passed and are committed. Other seven SU source forms are prepared only, not physically released. Full details in CODEX-QC-SU1-0222.md and CODEX-QC-CAL-FIFO2-0222.md.
- OWNER? none. No merges, tags, POR changes or deletions.
