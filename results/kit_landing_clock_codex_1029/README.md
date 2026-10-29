# Partition count-aligned clock entry contract

KV sys_c generated real forwarded-clock inputs from landing_contract.json,
but clock_pin_geometry required every input to appear among ordinary
budget.clock.taps_snapped. It now also accepts declared landing pins only
when kind=clock, dir=in, finite xy_um, layer=partition signal_max. Existing
pin size, actual location, routing-track and ordinary tap checks still run.
Conflicts with an ordinary tap or invalid metadata fail closed. No fclk
name regex waiver is added; data/reset/output pins get no clock-root entry.

Actual retained kit intel1:codex-kv-kits-1028/sysc/kits2/kv3_sys_c has23
false missing-tap errors before, zero after; all29 constraint clock ports
are geometrically accounted for. The original failure is preserved.
28 kit-contract tests PASS including missing declaration, wrong kind,
direction, location/layer and pin-size controls. This does not qualify the
landing implementation physically or clear macro-grid/LEC/other holds;
KV kits owns those. No allocation, P&R or STA run.
