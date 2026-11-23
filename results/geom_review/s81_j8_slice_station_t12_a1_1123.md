# S81 J8 slice station t12 attempt 1

Reviewed 2026-11-23 08:43 PST. **PASS-COND** for the exact kit through normal CTS and route gates. Retain regular clock and timing limits.

- Exact kit , placed ODB SHA-256 .
- Viewed ,  and .
- North and south feedthrough faces line up around the west columns and the separate east station. The density view shows narrow repeated relay rows and clear space between them. No macro corridor blockage. Local peak 68.4%, worst pin-track use 16.6%, zero opposite-face pins.
- The placed flop hops peak at 322.33 um with no reach or station gaps. Pin registration p90 40.86 um exceeds the 30 um advisory, but max 77.58 um and no unregistered pins. The unused interior follows the parent station footprint.
- The raw port drives one sink 1,597.96 um before CTS. The exact pre-CTS hook sources clock_taps.tcl for reassignment. Nearest planned reach peaks 322.66 um and predicted largest tap fanout is 764 vs configured 1,500. The already-run placement diagnostic had zero signal overflow with clock nets excluded.
