# HBM SU00 paired-entry PREP independent review

Verdict: PASS-COND scoped to the SU00 entry proposal. Full lane routing remains held.

Image personally viewed: `/home/ubuntu/coord/tmp/codex-hbm-d44r-2039/su00_entry_review.png`. Read the paired-entry ledger and actual hop-check output in the same directory. Both NW and NE views preserve the paired B113 E / SU00 W abutting entry while moving the window down to 136.128–413.2947 um. The seven internal bank rows now occupy the open south street beneath the macros rather than reaching from an entry above the first bank. Eight station stages remain; the reported maximum interbank hop is 287.28 um, below 405 um, with zero added cycles. The new red entry band is aligned on both sides and clear of the neighboring macro footprints in this outline view.

Conditions before any route:
- B113 output source locality must be checked against its actual final-bank/output-flop placement: the pin window moves 511.52 um and an outline image does not qualify its internal egress path.
- B001 downstream native-input hops remain 556 um and FAIL in `entry_hop_checks.json`; this entry repair does not close that separate station geometry.
- The full source/clock event, actual pin order/channel demand and clock lattice remain held. PDN/clock are unchanged by this pin-only proposal, with no new clock qualification implied.
