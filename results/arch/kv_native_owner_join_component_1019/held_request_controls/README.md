# Selected held-request protocol: baseline and causal evidence

The actual selected station contract is one outstanding held request with registered acknowledgment and WAIT_DROP. In the passing source8afdbb1e9 baseline, cases0–3 complete all four real steps. Every AW/W payload remains stable through its first actual independent acceptance. The traces separately record bridge capture acknowledgment, returned core acknowledgment, output VALID drop and source VALID drop. Actual bridge capture pulses and final read/write packet counts reject duplicates even when VALID falls.

All three actual one-source DUT controls are CAUGHT against their exact passing case1/2 baseline: AW address changes before first AW acceptance, W data changes before first W acceptance, and an extra bridge AW capture acknowledgment. The duplicate control records two captures versus one unique offer on the VALID-drop edge. Each control has a named invariant failure, nonzero actual process receipt, exact single-source delta, immutable logs and changed source snapshot. No timeout is counted as causal evidence.

The preceding generic checker failure remains in attempt2. The next landed-CQ observer-source failure remains in attempt3. Attempt4 health case4 reached a genuine native error CQ but failed because its offered key was saved only for healthy cases; that failure is preserved separately. The held-request proof does not turn that health failure into PASS.

This is FUNCTIONAL_ONLY minimum native owner join component evidence. It does not qualify a generic AXI fabric, the full root, native clock/reset phase, complete health inventory/calendar, physical SRAM, timing, or MU4.
