Native final guide serialization check, 2026-11-01.

Intel2 retained immutable NL input: /srv/opentallas-scratch2/claude/codex-qc-nl-clock50-1504/input.odb.
Owned outputs: /srv/opentallas-scratch2/claude/codex-final-guides-1131.
Normal waiter was officially cancelled NOT RUN; ROOT nominated ONE identical 6GiB/2CPU/disk2 native export check --crit. Actual scope oth-ubuntu-2967208-1793576908 ran exit 0. Image openroad/orfs:asap7lock, OpenROAD26Q3-1510-g6cb3f2b704.

write.tcl reads the retained DB, emits per-net/layer/rectangle records and PG attributes, then runs native write_guides. compare.py compares exact multisets to the native guide text. All 67826 SIGNAL and1184 CLOCK names plus652230 rectangles match. Old guide file lacks937 newSIGNAL nets. New file has no missing/extra/differing boxes. PG attrs unchanged; input SHA equals the retained input.sha.

Pinned global_route.tcl writes guides BEFORE POST GLOBAL_ROUTE; post repair updates DB guides. The patch adds native write_guides immediately AFTER a successful POST and before final DB write. Failed POST still fails without exporting a new final file. Existing saved results and live kits are unchanged.

Pinned detail_route.tcl calls load_design5_1_grt.odb and grt::have_routes, with no read_guides call; load.tcl loads read_db. Thus this fixes an export/coverage defect, without claiming demonstrated DRT failure or reroute/timing credit. No net, clock, source, timing, PG or routing changes.
