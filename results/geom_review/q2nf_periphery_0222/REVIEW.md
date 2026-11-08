# Q2NF periphery conservative form, pre-placement review

Source vehicle: intel1 codex-q2nf-0222/kit, copied from die-hbm-89/q2nf vA1, 145409 synthesized cells; source semantics and pin cycles unchanged. The branch contains a candidate geometry, not a plan-of-record update or routing receipt.

Old actual kit:786.24x622.08um,19macros,6222pins. Total area66612.9um2, macroarea44117.2, standard22495.7 =>4.6% standardfill. Central six-row issuer stack and all40clock entries near E x748 are the SPARSE+CLOCK causes. Original image q2nf_plan.png viewed.

Candidate:708.48x311.04um. Six issuer memories on N/S periphery in three columns, link SRAMs along W/E, five smaller memories around the open clock band. No three-row wall through the centre.40clock entries are beside their regional sink groups, all clear of macro halos.6222pin identities retained, face pins redistributed uniformly on actual .024+n*.048 track centres. Macro halo4.32um,64.8um between opposing issuer faces. Image q2nf_periphery_candidate.png viewed. Area -55%, standardfill10.2%;19macros and the shared access/clock band account for the remaining space.

Actual mapped netlist plus LEF pin census:6712signal pin incidences,4861distinct nets,602shared between macros,19/19instances, zero missing pin mappings. The initial port parser omitted each cell's final wd_in argument; pin-name coverage caught it and the corrected census is used here.

Local gap budget: worst532opposing M4 pins,56.16um after subtracting both halos,702M5tracks at60% use. No reliance on M7. Actual macros obstruct M1-M4; signal M5 access remains above them, and PG pins are M4.

Shared cuts (periphery_demand.json): at x236.328/470.496um,599/532macro-connected nets cross. Charging all2793W/Eface pins and40clocks to each cut gives3432/3365tracks versus6358capacity (M2/M4 at50% availability for PG, M6 clear, then60% routing budget). At y67.392/155.52/237.024, north/south distinct macro nets plus the full respective external face and40clocks bound demand7265/5848/4473 versus8856M5tracks at60%.

Assumptions requiring the one PLACE pilot: each macro's nonshared logic stays in its column and N/S face traffic descends locally; the shared standard-cell network, density and actual clock sink placement must confirm these assumptions. This is an analytic estimate, not a routed result or a clock timing pass.

VERDICT: parent authorized ONE placement diagnostic in parallel with the ordinary complete LEC receipt, because the actual saved-AIG full miter proves55722outputs and small replica/parity negative controls pass. This changes only geometry. The ordinary receipt remains required for qualification. HOLD CTS/GRT/route until actual PLACE density, clock and macro/pin images are viewed and reach/locality are read. ONE PLACE-only pilot started on intel1 kit_periphery_vC via ot-run, unit oth-ubuntu-1194928-1794136555,32GB8T; mapped source reused with do-floorplan/do-place, signals<=M6. No further stage released. First smaller414.72x362.88 sketch was held for internal macro walls and is superseded by this periphery form.
