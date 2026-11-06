# HBM p35 geometry review

Reviewed 2026-11-05 by Codex before new route submission.
Picture: part35_tx.png; plan rendered by tools/geom_review/plan_review.py at intel2 /srv/opentallas-scratch2/claude/codex-hbm-wave/review35.

PASS-COND. TX gains 51.84um height at all five parent placements, preserving original origin and W/S coordinates; N pins move north exactly 51.84um. The image shows RX left-adjacent, dchn below RX, clear north expansion, no overlapping neighbor. Parent boundary and all hard-core pair overlap checks PASS. Clock entry follows the new TX center (142.584,103.68). No new macros, PDN or partition outline changes. Dataflow and face ordering preserved. Existing parent infrastructure advisories remain for die integration; new placement uses the standard kit PDN.

Twelve known two-clock M5 collisions are separated on existing legal tracks. RX rck_clk=147.48 and wbq_root hbm_clk=216.216 match their live vB choices; wbq_sw stream_clk=43.608. Other affected two-clock files move the second clock to first+0.384um. Clock pin widths/height unchanged, no cycle or timing-contract change. This event does not claim sign-off.

Estimate: +33.3% TX horizontal track supply reduces measured worst band usage1.18 to ~0.885; utilization0.39 to~0.29. This is the measured root cause and the owner-approved recommended form. Sign-off remains required.
