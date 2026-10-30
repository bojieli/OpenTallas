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
