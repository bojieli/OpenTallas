# c21k saved gate pickup

HOLD, not submit-qualified. Original exact gate reports WARN with zero FAIL items; its actual trial_route.rc is 2. Congestion overflow 0 precedes terminal GRT-0183 in repair_design_helper. No complete 5_1_grt.odb exists; a diagnostic 5_1_grt.grt183_resume.odb survives. Gate parser currently accepts an available zero-overflow table without checking nonzero GRT return code. The original JSON/log/PNG are retained unmodified.

Visual review: 84 SRAMs on the existing lattice, one occupied full-width middle band (measured 49.68%), aspect1.44, S central clock, open macro channels. Native mapped census max32 and boundary clock spreads TT43.6/FF42.4 pass. Placement timing is TT diagnostic reg-reg -79.9ps, not signoff. No route closure or binding claimed. Full native placed endpoint Manhattan reach audit on immutable4_cts.odb is underway. No REVIEW approval written.
