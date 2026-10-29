# HEAD strip candidate, Codex continuation

PARTIAL plan event. Seven of ten FT types crop without changing any external data pin's absolute die position. hd_st_m becomes 1442.88 x 129.60 um, from 1442.88 x 1226.88. The other crops and per-type load/track estimates are in report.json. No RTL or token-cycle change.

Recovered the predecessor's uncommitted draft read-only from intel2 dh21-resize. Corrected its tap inventory: the face/FT-only `sinks` mode omitted internal CA reader banks. The candidate uses the existing density planner with each reader bank's four corners and its declared reader-flop load. Across the ten FT types plus ctl/host/mesh, planned sink radius <=237.8 um and reader-bank corner radius <=195.38 um (own runs, UNCHECKED by independent number check). Writer banks remain on their forwarded clocks.

Six focused checks pass: die-coordinate preservation at mirrors, CA reader-bank load/extent included, invalid geometry detected. Viewed png/hd_st_m.png and png/die_hk4.png. The st_m strip has short face-to-bank routes and local taps along the transit stations; released whitespace retains the former top-clock coordinates in the report. No P&R or STA submitted.

OPEN: hd_spn/spn_end/n3 external face windows span their current frames. Their bands and pin contracts must be re-composed together with neighbors to reduce the outlines further. This candidate changes clock-tap counts on all 13 types; the die clock provider and CA/START bind must be regenerated before routing. ctl/host/mesh retain their outlines pending true cell/macro-based refloorplanning. G0 reports are diagnostic, not a pass. Shared HEAD source prerequisites were merged into the private worktree for generation; merge only the source/result delta commit from this branch when integrating.
