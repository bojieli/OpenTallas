# L0r write-enable candidate

Inherited c17 CTS setup report: bgh[1] -> rs[33][11], 1078ps data arrival and -326.28ps setup at833ps. The cone contains x6/x192 address arithmetic, decode, and high-fanout write-enable buffering. The inherited GRT job remains running unchanged.

WRITE_DECODE=1 captures 64 A/B one-hot group selects beside existing input payload/valid registers, and generates static store-word writes. All six-bit {bank,group} addresses cover exactly64groups; no address is outside the384-word store. B assignment remains last on a collision. Existing reset/valid and data capture edges are preserved; zero new data cycles. WRITE_DECODE defaults0 and no current master recipe is changed.

Old/new actual-module miter compares all384 store words every edge and all valid output fields, including simultaneous writes, bank/address sweeps, active-stream writes and reset. PASS368 output beats,246 collisions,1050 write edges; a mutant changing collision priority is caught. New synthesis/formal and named-sink slice qualification are still required before physical adoption. Additional enable flops change the clock sink census; no reuse of the old c17 clock slice is claimed.

## Preferred native-boundary variant WRITE_DECODE=2

Mode1's input predecode may remove the original planned raw face registers; it is not adopted. Mode2 captures raw six-bit bank/group separately per group (kept), then uses local constant6bit comparisons. Group0 uses the original named agh/bgh/wb captures, so they remain meaningful. Every new pin path lands directly in an FF at the original edge. No dynamic address arithmetic or global decoded-enable tree remains. The price is~756extra raw address FFs, requiring a fresh clock-sink census and face placement. Same full-store/output miter PASS368beats/246collisions/1050writes, priority mutant caught. Candidate recipe selects mode2; defaultsource remains0. Synthesis/formal/face_guard/slice gates remain before adoption.

## Final candidate refinement:16 raw capture clusters

Four adjacent groups share each raw capture pair. Cluster0 still owns original agh/bgh/wb captures,15additional kept A/B pairs add180FFs. Input address pin fanout16 and bank pin fanout31 before merging stay below32. Actual local decode fanout and face placement require synthesis qualification. Golden full-store/output miter again PASS368beats/246collisions/1050writes; priority mutant caught. Same mode2 opt-in and default0; prior mode2 receipts remain historical evidence.

## C19w native-boundary FAIL and mode3 correction

C19w source14527769c9 SYNTHESIS passed, but raw face_guard FAIL724/735:11address pins shared15/30loads. The one-capture-per-pin rule is stricter than the32fanout budget; run stopped before floorplan and no exception was applied. Raw-copy modes are not physically qualified. Failed receipt retained separately.

Mode3 retains only the original agh/bgh/wb input captures, uses direct constant six-bit group comparisons and static store indices. It removes the x192/x6 arithmetic while preserving onecapture/pin, collision priority, all ports and all data edges, adding zeroFFs/cycles. Full-store/output miter PASS368beats/246collisions/1050writes, prioritymutant caught. Candidate recipe now selects3, defaultsource remains0. Fresh synthesis/face_guard/fanout and current formal/slice remain required.
