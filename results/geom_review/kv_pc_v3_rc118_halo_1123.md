# KV pc_v3 rc118 halo probe

The 4.32 µm pcc/pcf halo probe on kit A placement was rendered and inspected. Teal shows macros, blue is 25 µm placed standard-cell density, and red marks measured global-routing overflow.

Picture at epyc9:/srv/opentallas-scratch2/claude/fable-open-kv/p2/codex_density.svg. The adjacent geom.tsv.gz and cong.rpt contain the placement and overflow data.

Five-iteration GRT overflow moved from 11,671 on the original placed DB to 3,284 with the four slit blockages and 3,220 with the macro halos. The residual clusters run along the inward faces of kvpc3/2 and kvpc0/1. Their footprints contain 3,119 of 3,220 overflow. Heavy named groups are the 491 hroot o_chN ring select, 206 slg o_dn, and the kvpc1/2 next/previous chains. Excluding cells addresses the narrow outer slit, while inward macro-edge demand remains concentrated at the capacity-zero pin escapes. The middle channel stays open outside the SRAM rows.

**Verdict FAIL for route.** The candidate needs same-face landing and short registered legs for the residual groups. Carry slit placement blockages as one contributor. The pc_v3 PCST row targets hroot o_chN and the kvpc/slg output legs. The composed placement must confirm those changes relieve the inner-face demand.
