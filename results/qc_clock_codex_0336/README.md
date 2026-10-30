# QC clock continuation 2026-10-30

QC46 refit ideal clock completed TT/FF:7889taps,313regions,0missing. Original standalone dump lacked slew and used833.333ps; own diagnostic uses833ps, measured slew+bothedges and all repeater/nodecells. Plain-tap nominal max spread91.92TT/77.09FF; no region above150. These are placement-RC estimates, not die gate numbers.

Fresh native target exported from exact-origin main die_trial preamble on plan_qc45 2257b9fb:377/377 origins exact,0off (old221off). 319MB native target at intel2:/srv/opentallas-scratch2/claude/codex-qc-clock-0336/nativekit/native_target.odb. No routing performed.

Retained actual clock CA diagnostic now reports2525/2525crossings timed,0unbound/0missing:86TT/56FF failures, unique86. Worst low margin-106.5TT/+50.4FF. See actual_retained_ca.json. Existing low-side K price is stale relative to real R7clock. Fresh shared planner running on QC46 exact endpoint map; no counter change adopted.

Native builder/provider rebuild owned by coverage_support; old3266stage mapping invalid for fresh tree and must not be reused. New tree50812cells vs old44590. Sources/scripts preserved here; bulk graphs/proof remain scratch.
