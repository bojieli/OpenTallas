# HEAD NF15b selected transport composition

The existing HEAD schedule-constant compiler was run on exact NF15a and NF15b landed source plans and their own sidecars. It adds only sidecar cycles above each plan clock landing. Source hashes are in sources.json; the runtime inputs remain in the inherited token lane.

Exactly 22 lanes gain one cycle. The maximum selected spine path remains W5 at 240 cycles and worst gather m0S_rx remains 81, so the existing composed transport law is 240 + 2 * 81 = 402 cycles for both plans. This is a zero critical-path delta, not a blanket 22-cycle token charge. HOST TX/RX remain 58/58; separate LEP landing/fault legs remain 9/8. The corrected FREG logical K restores intended declared timing and is not charged again.

Reproduce with tools/s81_head/regen_schedule_constants.py --plan INPUT_PLAN --landed-sidecar MATCHING_SIDECAR --out-json NEW_JSON --out-sv NEW_SV for each source, then delta(baseline,candidate). No simulation was run.

This is plan-derived source scheduling, not a production START calendar, activation-source qualification, token-rate receipt or physical adoption. The actual selected native HEAD programme still requires the actual activation residence dates, peer timing, START authority and current source/reset identity required by head_static_programme.py.
