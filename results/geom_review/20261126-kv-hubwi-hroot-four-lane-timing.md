# HubWi X743 western HROOT timing

**Hold the four proposed additional cycles. The protected native pair passes, and the stock F5 compile has two unqualified timing effects.**

Native HROOT, drain and status components on Intel2 checked both 1118-bit request lanes and both 144-bit status lanes. The causal fixture observed 246 equal round-trip edges with the expected +2 shift, preserved the three-cycle WN/WS request skew for 22 pulses, suppressed two fixture-cancelled appointments, caught 44 late-return mutants, and cleared status between frames. The test uses modeled work at the group endpoints and actual drain, boot and ownership observers.

The current G4 F5 compiler accepted the exact private ages L1449 23→24, L1450 20→21, L1575 25→26 and L1595 28→29 and produced COMPILED_NOT_QUALIFIED. West ES player offsets account for the increased down age. The embedding return is unchanged, fill margin remains 808, and the token core remains 290059 cycles. All 108 common ctrl/kgo/vgo roots advance by one, preserving west capture dates and making east one edge early. The scalar compiler does not establish that the east K/V group consumers tolerate the shift. Its inherited K ring peak remains 80 for depth 64.

Native C32 with the actual ownership roots [3, 288099, 293441] rejects the latest legal original W drain when that drain is delayed one edge, with fault 0x10. An original trace with one edge of spare drain margin passes both arms. A modeled leave change to 288100 repairs the boundary case and preserves deadline 293441 and next-frame rearm. The stock candidate does not emit that leave change. No live F5 west group-drain receipt or east early-arrival qualification is available.

- Native exact modules, bench and receipts on intel2 at /srv/opentallas-scratch2/claude/kv-hubwi-age-codex-1126/native_hroot
- Exact four-lane compiler input diff and budget comparison on epyc12 at /srv/opentallas-scratch2/claude/KV-NOROW/hubwi_hroot_native_1126/price_comparison.json
