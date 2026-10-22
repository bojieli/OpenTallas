# Native59 terminal failure checklist

Original floorplan PNGs were personally viewed by the pickup worker. They depict the floorplan, not completed placement, CTS or routing. ROOT must personally inspect these originals before any later critical adoption; no REVIEW.json or submission is produced here.

| Obligation | Evidence and status |
| --- | --- |
| Source identity | PASS for immutable failure evidence: exact shipping manifests, remote executed scripts, and all 255/254 declared consumed files independently hash checked. No main-source equivalence claimed. |
| Pin registration / reset | Historical source contract says flop-first RTL and +1 calendar edge; original gate reports two reset landing stages. Pre-gate safe3/3b land forest has 32 copies / approximately 45 loads each, exceeding 32; safe3c later changes to 56 copies. No final native reset proof. |
| Wire reach | Historical textbook scalar estimate 82.9 um; actual pre-CTS/final all-role native reach is UNKNOWN. |
| Fanout | Historical reset overage retained. No final clock/reset/tie/BUF/INV-transparent native census or PG binding proof. |
| Depth and timing | Textbook estimate 561.8 ps; actual CTS repair ended negative. No final TT setup, FF hold, pin spread or neighbour timing. |
| Storage | Eight 32x512 SRAM instances appear in original floorplan. Macro source/LEF/TT-FF Liberty preserved; no current SRAM geometry or contact qualification transferred. |
| Floorplan | 518.4 x 648 um outline, eight macros in two columns/four rows. PNG is floorplan-only, no standard-cell occupancy rendered. Full-width single band, exact macro origin lattice, local macro contact density, and clock placement cannot be certified from this PNG. Original port-geometry PASS does not establish the whole checklist. |
| Clock | 23,421 root sinks is guidance only. Actual TT/FF insertion/spread are null. No rejection based solely on sink count or insertion. |
| Schedule | No source, cycle, calendar, budget, tool, constraint or profile changed. Native59 Q-ready age-20 certificate remains required before production binding. |
| Termination | Both genuine original client results FAIL. Remote script executes timeout -k 60 14400, then named docker kill and GATE_STALL. Rc137 alone does not prove OOM. |
| Routing | GRT/path classes/placed image/clock calibration skipped after CTS failure. No route or signoff closure. |

No new engine, rerun, source choice, gate record, binding, view, or submission was made.
