# Native HEAD nominal clock provider

The all-coincident clock harness failed the actual CTL-strip→LEP count-aligned crossing at unchanged strap60. Recovering the measured START source phases resolves that harness error. This tool emits each declared START source clock and each physical partition's primary clock, with independent measured rise/fall arrivals. It refuses missing phases and clock/plan coverage gaps.

Current exact6 component: plan268f5579145c, sidecar90d006a48f17, 1251 START clocks +357 physical partition clocks. Inputs are the retained `results/codex_head_ca_0840/arr_{TT,FF}.txt.gz` T/F/N/M readouts and the actual exact6 `source/start_stages.json`. START clock_source_cell already selects the driver associated with A/Y. Partition clocks use measured T/F plus the selected plan's declared insertion_ps/insertion_ff_ps; internal clock latency remains an assumption. No physical signoff or programme admission follows from this model.

Executed literal control vehicle includes the real reset/START/control primitives for all357 parts and all1251 START stages. The unit_lep crossing retains actual writer START stages and strap60 (signed−4). Independent unwrapped sender-word history checks reader word m against source word m+4.

- TT: ready1/fault0,489 exact word-age checks.
- FF: ready1/fault0,490 exact word-age checks.
- All1608 clocks coincident: ready0/fault1, retained failing run.
- K+1: first armed comparison fails data age (got304/expected305); readiness alone would not qualify the calendar.
- Reusable provider's TT phase table equals the executed table; dropping a required N phase is refused.

Artifact root: epyc6:/srv/opentallas-scratch2/claude/codex-head-token-1106. The retained build scripts `control_vehicle.py` and `add_phase_age.py` construct this component from that immutable source capsule. No hardware RTL, K, guards, reset topology or pipeline cycles changed. The next four-real-part HOST transport measurement is separate and must supply fresh arrival/counter dates before HBC binding. Existing coincident-clock HOST/HBC dates remain provisional component results.
