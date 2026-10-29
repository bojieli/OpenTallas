# QC31 vK independent arithmetic check

Existing artifacts: intel1:/srv/opentallas-scratch2/claude/die-qc31.
No routing, STA, simulation, or physical changes were run.

Independently enumerated 378 load pairs from the stored 61 MC sample rows
per corner/edge. Computed the larger of observed absolute pair differences
and absolute sample mean plus three sample standard deviations, then added
the Euclidean differential gradient vector. No die_sta_related code was imported.

| Variant | Rise TT / FF, ps | Fall TT / FF, ps | Result against 80-ps target |
|---|---|---|---|
| vK keep-out | 43.3304 / 40.5813 | 44.4631 / 41.8988 | PASS, all four |
| vT track corridor | 77.8642 / 73.2146 | 83.1265 / 80.0472 | FAIL, both fall corners |

All eight reported rounded maxima and worst-pair identities reproduce.
vK worst pair is L_clk / L_clk_t15 throughout. This confirms the reported
pilot calculation; it does not qualify a die clock or a die freeze.

Independent rectangle intersections of the existing c1_shapes.json dump
confirm three positive-area M9 n_P1u/ck_mesh overlaps on the baseline,
with longitudinal sum 358.4 um. The same selected-net/mesh test has zero
intersections in vK. The original README's approximate 345-um length is
imprecise; it does not change the short diagnosis. The stored vK ECO DRC
report is empty. This bounded check does not reproduce the broader all-net
rrcheck or make a full DRC/no-shorts claim.

The stored vK rec.log reports driver input TT spread 28.44 ps rising and
30.31 ps falling, matching the README's rounded 28.4/30.3. The current HEAD
hk5 flow uses ordinary inverter trees, so its separate old explicit-mesh
risk is inapplicable (reviewer branch codex/geom-0822).
