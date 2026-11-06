# Q3 link right-width plan review

Image: results/geom_review/q3_link_rightwidth_1105.png (viewed before routing).

Old layout measured132952 GRT overflow with four171.288x77.784 macros as a near-solid vertical wall (two interrow gaps0.024um). Existing right-width141b branch uses56.184x20.808 macros. New plan keeps each bank at approximately its prior centre, same outline/pins/clock, leaves110um side channels and >=56.952um row channels. There is no macro wall, narrow notch, or obstruction near the central clock entry. Each macro has direct access to broad cell regions and both IO sides. Maximum outline span336.96um remains below405um per registered hop; no new latency. PDN pattern and exterior clock/PG interfaces unchanged.

Verdict PASS-COND: proceed to vA/vB kit generation and ordinary final sign-off. Macro track/grid placement must use the standard generator. This is an advisory physical review, not a timing/routing receipt.
