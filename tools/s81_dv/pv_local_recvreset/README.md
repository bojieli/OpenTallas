# Receiving-clock D32 mechanism

This is an unselected candidate, not a replacement for current die profile b.
The fixed profile remains D32/K17. Its 32 data slots and live age are unchanged.

The kit contributes two real ck reset edges. The reader contributes four more
ck reset edges. The writer asserts reset asynchronously while ck_f is gated,
then requires two real ck_f edges to release it. Those first two forwarded
edges are a reset preamble, before the first semantic payload epoch. Both
source first capture and reader startup are therefore explicit events. The
reader startup is two ck edges later than profile b; no production book is
created here. A future bound profile must provide that preamble and startup.

Source d2c02aa48 passed three original clock offsets at age18 with 222 word
checks each and zero mismatches/fault. The predecessor with only two reader
reset edges returns age16 and is caught by the same explicit book. The original
age mismatch is preserved separately. The event times in the logs are actual
component simulation ps; the raw receiver_m print may precede its same-edge
counter increment. It is not a production clock epoch.

The negative_reader_reset2.sv fixture is exactly source700c2f8a4. Compile it
exclusively with PV_RTL and run missing_reader_startup mode; expected exit1
requires real age16 mismatches and prints MISSING_READER_STARTUP_CAUGHT.

No mapped native census, physical reach, TT/FF clock closure, production clock
book, compiler binding, or die view is certified by this component proof.
