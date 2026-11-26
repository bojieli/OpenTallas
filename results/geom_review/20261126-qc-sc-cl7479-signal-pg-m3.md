# QC SC cl7479 M3 signal-to-PG review

The exact iteration-10 DRT report has 375 signal-to-PG M3 marks on 275 nets. All mate with a 90 × 34 nm M3 pad connected to a live M2-to-M5 power pickup. The marks include 279 metal-spacing, 55 shorts, 25 EOL keepout and 16 EOL spacing findings. I viewed the extracted marker map and candidate geometry. The main concentration sits around x=280–315 µm and y=1497–1525 µm, with smaller clusters farther east.

The 375 marks reduce to 338 signal, pickup and track cases. A track beside the pickup is geometrically possible in all 338 cases. The jointly allocated local tracks have at least 33 nm modeled clearance from PG, including competition with the existing clock candidates. The exact technology LEF requires up to 31 nm at M3 ends and up to 72 nm beside wide M4 metal. The companion model applies those bounds and checks native guides and routing obstructions.

| Retained guide result | Cases | Marks |
| --- | ---: | ---: |
| Alternate fits an existing M3 guide | 103 | 105 |
| Local companion connects to retained guides on both sides | 140 | 162 |
| Two-sided local guide connection remains open | 95 | 108 |

An old-track mask is geometrically clear of PG in 291 cases. Forty-seven old track centers intersect PG and need a different approach at the pickup. After accounting for overlap with the guide failures, 211 cases have both a PG-clear mask and a guide witness. The other 127 cases remain held. The EOL examples explain why a common old-track mask cannot cover the entire cohort.

Keep the power stack and its pads. Price signal track moves and guide attachments around it, including an axial route turn where the old center intersects the pickup. The retained GRT database lacks actual DRT signal wires, EOL endpoints, and final occupancy. This review supplies geometric witnesses and a per-case residual ledger. No source packet was transferred, no database was modified, and no CAD run was launched.

E7 artifacts are under `/srv/opentallas-scratch2/claude/QC-DRT-ECO/cl7479_signal_pg_1126`, including `cl7479_signal_pg_review.png`, `companion_extended.json`, and `unsupported_source_scope.json`. Input fingerprints are DRT report `63a06ec99322`, GRT DB `93dc82a8e813`, and final guide `0afd50047559`.
