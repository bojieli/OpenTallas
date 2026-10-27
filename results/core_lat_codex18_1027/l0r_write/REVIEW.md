# L0r write-enable candidate

Inherited c17 CTS setup report: bgh[1] -> rs[33][11], 1078ps data arrival and -326.28ps setup at833ps. The cone contains x6/x192 address arithmetic, decode, and high-fanout write-enable buffering. The inherited GRT job remains running unchanged.

WRITE_DECODE=1 captures 64 A/B one-hot group selects beside existing input payload/valid registers, and generates static store-word writes. All six-bit {bank,group} addresses cover exactly64groups; no address is outside the384-word store. B assignment remains last on a collision. Existing reset/valid and data capture edges are preserved; zero new data cycles. WRITE_DECODE defaults0 and no current master recipe is changed.

Old/new actual-module miter compares all384 store words every edge and all valid output fields, including simultaneous writes, bank/address sweeps, active-stream writes and reset. PASS368 output beats,246 collisions,1050 write edges; a mutant changing collision priority is caught. New synthesis/formal and named-sink slice qualification are still required before physical adoption. Additional enable flops change the clock sink census; no reuse of the old c17 clock slice is claimed.
