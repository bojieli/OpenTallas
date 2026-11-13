# HEAD recovered-clock density plan review — 2026-11-13

Picture actually viewed: epyc9:/srv/opentallas-scratch2/claude/hold-tap-1/secondary_clock/hd_recovered_density_model_v2.png. The earlier v1 plot used a guessed 2000 DBU/um; actual snapshot is1000, so v1 plot is INVALID and retained. v2 reads actual DBU.

Exact3_place source f6470fa3a0f9ae664fff534e16dfd6dc48d4b728f50c307f66690316e81ca821. Actual source pma_rck[0] owns13,520 standard clockpins +4 macroclockpins (dualclock dmem rclk ANDwclk); all_registers alone omittedwclk. Existing833ps recovered-clock/CDC constraints retained.

The active strip is below the PHY exclusion y150um, across about2.9mm. Three real macros interrupt the W/centre strip; existing sinks occupy surrounding lanes and top/bottom pin strips. Proposed canonical density cohorts are local:106 groups, max845FF, maxmedoid L1radius79.488um. Medoids sit on existing standard-cell locations, not macro interiors. Actual inserted buffers must legalize while all original placements stayFIRM and thenrestoreoriginalstatus; runtime rejects source changes, ordinaryroot edits, missing sinkcoverage, load>1000 or finalradius>200um. Four macro clockpins remain on the recovered source via canonical interface-FF assignment.

SMELLS: long whole-shore trunk remains; thin top corridor aboveKPmacro; isolated originalFFs near PHY edge. No new macro/data placement or extra exported tap ports. Model is local topology/load only; global insertion/skew and actual hold are UNMEASURED. Canonical native-source density method builds trunk+localCTS, no aftermeasurement clock padding/trim.

Verdict ISSUES-ACCEPT for ONE composed HEAD primary/recovered-clock PLACE+CTS diagnostic only. No detailed route/batch release or signoff claim. Review actual postdensity/CTS images, domain attribution, internal TT/FF paths before a next physical step. Zero added data/control cycles.
