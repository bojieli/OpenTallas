# CTLM safe13a: actual load-side copies and spatial clocks

Component candidate on exact RR2 base263ad92c3. Same777.6x734.4 outline and13 hard blocks.
Tok/Pos move to E beside actual CLOSED h16c ports. No old-view alias: H16ZA binds only
after its actual view closes and an enlarged parent is generated.

14 actual placed mixed-copy groups,1119 pins,+2 identical combinational copies,0 FF or
state/clock/data edges. Canonical comparison finds0non-identical drivers. Helpers are
byte-identical RR2.82 copy owners are assigned W0/W1/E0/E1 from actual placed sinks;
unknown groups remain explicitly unchanged. Clock spine:existing ck_core/ck_hr,bin30,
leaf16. Same clock families and existing core/hr landed crossings; no new exception.

Checklist: pinsFIXED Tok/Pos E grants; reachPENDING actual wirelint; fanoutPENDING
mapped32 census; depthUNCHANGED identical operators; storageUNCHANGED macros;
floorplanSAME as actual safe12c GPLRC0; clockPENDING CTSspread; scheduleUNCHANGED0edges.
Not selectedQ73, HP/RR2 integration, physical timing PASS or new H16ZA binding.
