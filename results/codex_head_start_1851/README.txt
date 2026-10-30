HEAD START diagnostic vehicle continuation, 2026-10-29 18:56 PDT.

Base: claude/die-head-33-start-1029@04c97271dc468062399bbaea28953d100045c9f6.
Run: intel2:/srv/opentallas-scratch2/claude/codex-head-start-1851.
Own source: intel2:/srv/opentallas-scratch2/claude/wt/codex-head-start-1851.

The current provider mapped 13264 cells and 4786 flops, equal to the planned
4786 flops/1226 stages. Existing 735403ad0 diagnostic pack requires native
row phase; the die tree put root b0 at y7740.44, which failed the packer.
legalize_clock.py supplies the previously unscripted native placement step:
5847 actual clock cells use legal complete cell bodies and native .27um rows,
.054um sites, preserving connectivity and all clock masters. Maximum move
1.235um. Pack now completes with all 13264 actual cells and 1226 stages.

No RTL or explicit latency changed. Clock arrivals MUST be remeasured after
this geometry change. This is an unmerged diagnostic vehicle, not a production
clock ECO or die STA claim. The latest source's DATA200 model FAIL500/3001 is
retained. Native leaf DD still requires each signed kit view. Next steps are
ports, uniform branch isolation/data buffers, local clock-entry buffers,
full-body/reach census plus visual review, then diagnostic GRT50 and DD parse.

prepare.sh completed via ot-run unit2815126. next.sh admitted as unit2878202.
No route or timing result is claimed by these receipts.

Explicit reset handback 19:03 PDT: no new engineering after root reset order.
Terminal next.sh PASS up to body construction, initial geometry FAIL3 reset
captures (max405.757) and a root-port diagnostic missing case, all preserved
in reach.json. Geometry-only r91_3 11-cell move(+.972,-5.4) plus root-input
accounting fixed those; reach_fix.json PASS24162 bodies,0overlap/illegal/
off-grid/missing,0hops>405. Actual reset max399.385, data181.602, FFclock20.034.
Rendered overview and root rows personally viewed; G1 review in geom_review.
Generated current src25m raw combo and overlay18315 START/localclock cells.
Before explicit reset submitted diagnostic TT+FF GRT50,833.000ps:
 TT ot-run unit3746047/containercodex-head-start-1851-TT, out_TT/run.log
 FF ot-run unit3754339/containercodex-head-start-1851-FF, out_FF/run.log
Both live at handback; no route/STA result claimed. Existing job/unit logs and
all outputs under run dir remain; do not restart or duplicate. Continue by
collecting GRT+SPEF+ODB and emit actual virtual DD with head_start_edge_sta.py;
native leaf DD remains from signed kit views, then data-aware replan required.
Only own duplicate ports.py process3013663 was stopped after launch-script
slicing accidentally repeated existing ports assembly; no other job killed.
