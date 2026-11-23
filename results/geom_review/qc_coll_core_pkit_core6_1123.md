# QC coll_core pkit_core6 placement review

Verdict FAIL for route. Reviewed layout and density images on epyc10 under /srv/opentallas-scratch2/claude/fable-fix-qc-coll-r2/pkit_core6/gen/coll_core/run/layout_review/place/. The eastern fold macros and SRAM bank form a nearly continuous north-south barrier. The lower west macro array concentrates the logic and pin approaches into narrow channels. The center and lower east have room to spread the local logic, but the present interior channels do not connect the two regions cleanly.

The exact placed scan reports vertical demand 1.871 of capacity (hard 1.0), 604 capture legs over 405 um and a maximum 728.73 um reset/control leg from u_rrl_245 to u_ist_fltv_o_2. io_collective in_valid and in_last are 273.54 um from their pin registers. The pin-density scan was within its limit, with no unregistered pins. Placement images cannot establish PDN continuity or routed clock balance.

For the next form, retain the macro shapes, interrupt the east macro wall with transverse channels aligned to the active bus sites, and seat the input pin-register and reset/fault stations in the open region adjacent to their face and consumers. Re-measure the identified long legs and the W/N approach before route.
