# Independent A40R existing-clock-cell relocation review

LOOKED actual prepared image /home/ubuntu/coord/tmp/caprt1101/A40_driver_relocate_plan.png and read the exact A40_relocation_plan.json plus A40_driver_relocate.tcl. PASS-COND for the A40R own-copy relocation and incremental-GRT prototype. No timing, sign-off or detailed-route claim.

The two real load clusters lie south of the SRAM; their old branch drivers were north of it. New driver centers158.4855,28.2375 and142.8768,9.225 occupy those south load islands and are clear of the shown SRAM body+halo. Existing dummy clkload29 goes160.6455,28.7775 and clkload26 goes145.0368,9.765, offset2.16umX/0.54umY from the driver, rather than coincident as the overview markers might suggest. No new cell, RTL, cycle, port or constraint change.

Actual master dimensions convert centers to origins at runtime. The copied flow firms all other PLACED instances, runs detailed placement and check_placement, and errors if any unapproved instance moved before incrementalGRT. That actual result establishes legal placement; this prepared image alone does not. Preserve the original A40 failed result and collect the legalized four-mover image, GRT/timing and unchanged clock policy. The owner reports TT−43.15 with125.53ps launch/capture skew and FF+20.50 on A40; relocation targets that diagnosed clock topology, not a relaxed uncertainty.
