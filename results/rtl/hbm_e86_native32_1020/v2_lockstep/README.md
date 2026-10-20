# V2 lockstep terminal

Source4aa724d4e, FAN32=1/PRE1/CREP1 vs generic PRE1/CREP0 reference;
Verilator5.050 full64-seat/86-bit element,4000cycles. Positive PASS with
2139insertions/2034overflow events/173convey-up changes/1995tau hits.
CMUT1 actual control hold error FAIL132; CMUT2 comparator capture forcedzero
FAIL2835. All outputs compared every edge. Fleet stdout, exact runtime logs
and source hashes retained. This is initial-zero simulation with real clear
and midstream single-cycle clear stimulus, not arbitrary-init qualification.

The same binary reused with independent randreset2 seeds17/1020 aborts at the
first5ns edge in the existing unconditional simulation legality assertion,
before clear has propagated. This is preserved as a precontract diagnostic,
not a DUT functional failure or a passing random-init proof. No mismatch is
hidden. Actual-parent protocol continuation uses narrow test-only assertion
epoch and removes only artificial SRAM zero-init, as documented separately.

Mapped native32, boundary/area and production pulse/phase receipts are separate
and pending. No physical gate or rate adoption follows from lockstep alone.
