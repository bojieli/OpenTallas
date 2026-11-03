The five-FF variant is not currently qualified. Public PART1 accepts a new GO
when ready1/idle0, before previous raw publication drains. The actual caller
ready bit is literal1 and idle is aggregate station status. Fixed-calendar
unavailability produces a fault but does not suppress the scheduled GO.
HEAD barriers therefore do not constitute a local native-drain proof, and
1024-cycle fixture gaps cannot be promoted into a production lease.

A3-bit slot counter may free-run on UNMASKED raw_v modulo8, reset only with the
unit. An additional2-bit publication mode could keepall/q4slot<3/q5none, but its
accepted-GO latch needs an exact no-mode-change-before-drain premise. At the
inner PART1 publisher, require native idle already true on each accepted
mode-changing GO. A later outer publisher must include TOREG/face delays.
The robust per-word predicate remains necessary for the unrestricted native ABI.

Assessment/caller source reports preserve exact pointers, descriptor decoding,
proxy-status qualification and a source early-GO counterexample. This is not an
RTL implementation, changed contract, physical claim or dispatched test.
