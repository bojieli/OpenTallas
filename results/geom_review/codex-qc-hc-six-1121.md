# Qwen Compute R6V1 HC plan review

Viewed intel2:/srv/opentallas-scratch2/claude/qc-hc-six-1121/qc-hc-six-review.png from current plan SHA-256 aeae201486278deeda39471ba160e3b4fe02318a30e0953249010855ce9be9e0. The six variants cover 13 actual partition instances. Each has its own module and parameter set and five differ in clock form from the live same-prefix sibling.

South pin banks carry most of the interface width. HC0 also uses long east and split north banks; its explicit registered path crosses the right half. HC1 paths follow the west-side interior and HC2 uses a nearly straight column. Longest displayed declared legs are 192.75, 180.94, 180.94 and 161.91 µm. The two HC3 rows use generated transport and have no explicit segment plotted. Each type declares two internal clock taps. The exact generated kits will show the actual macro, transport, clock and PDN structures.

Verdict PASS-COND for generation and placement. Each newly built route requires the exact placed-kit image and verdict. The intake addition uses the existing event SHA and names all six items explicitly.
