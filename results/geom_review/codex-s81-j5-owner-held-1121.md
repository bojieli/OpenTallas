# S81 owner-held J5 placements, 2026-11-21 02:22 PST

Event , attempt 1. Six existing  images viewed. Image paths are relative to
 on the named host.

| Picture | Findings | Verdict |
|---|---|---|
| epyc9  | Macro band spans the lower half; many nets converge in the opening west of the band. North and south pin clusters leave a central concentration. Review station placement around the macro ends in the successor. | FAIL |
| intel1  | Horizontal mid-die macro bands and lower-left pair cores squeeze north/south crossings into short openings. Visible fanout from south pads into the busy middle band. Use measured relay siting in the redesigned strip. | FAIL |
| epyc9  | Four upper macros and two lower macro bands leave a central street. Flop clusters along both inner macro ends compete for that street. Review ordered banks and reset sites in the successor. | FAIL |
| intel1  | Signal activity concentrates at north/east edges and one interior cluster. The sparse interior and long edge-to-core spans agree with the monitor-home and reset relay diagnosis. | FAIL |
| epyc9  | Dense central macro and tap cluster with heavily used west-edge pins. More local reset/START copies and sited monitor drivers are warranted. | FAIL |
| epyc9  | North-edge pin banks carry most of the activity despite a regular interior tap grid. The south-east concentration and long links call for the C1n monitor-home proof and J6 START siting. | FAIL |
| epyc10  | Registered path in the stale queue no longer exists. Use the reviewed replacement proof8 floorplan before any routing decision. | BLOCKED |

These placement renders do not show post-route PDN continuity. All seven old J5 rows already have owner plan holds. The current engineering actions are the J6 monitor-home and START relay rows, LEP proof8, and structural station and tap siting.
