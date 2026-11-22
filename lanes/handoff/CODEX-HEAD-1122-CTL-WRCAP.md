# HEAD CTL write-capture carry, Nov 22 11:2x PST

The exact private kit4 signed with 833 ps achieved, TT +1.46 ps, internal FF zero, DRC and antenna zero, and 4,468/4,468 pins. Its wrapper contains `.SRAM_WRITE_CAPTURE(1)` and uses the same 65 per-port offset and 65 per-port window values already carried by r18jk and r18m. Both newer candidates omit that parameter. The r18jk counting rebuild ctl1 is the offsets-only control. The older r17b route had DRC zero and missed TT by −80.03 ps on `wd2[878] → xb1/wd_in[366]` (467.57 ps final data segment) and internal FF by −6.89 ps.

Private epyc9 deltas are in `/srv/opentallas-scratch2/claude/fable-fix-head-lep0n-1122/ctl_wrcap_1122`.

- r18m `d6aa1940a08c` from `3dd49f406010`
- r18jk `0a6823ebba5e` from `5e1f38e1530b`

Each changes only `partition_types.hd_ctl.contents[u_core].params.SRAM_WRITE_CAPTURE` to string value `1`. Plan lanes and cycle counts stay the same. In the local core the complete high-half SRAM write beat is captured one cycle later. Its memory write completes six edges before the first eligible read. The exact earlier coupon at epyc10 `head-crossing-1119/ctl_write_stage_codex/exact.log` passed 2,560 writes and all 2,560 eligible SRAM reads over 32 epochs. The monitor also detects the data/control skew mutant.

The signed proof used three rows on its four landing strips, automatically selected by the same `OT_CLAND_STRIP_DENS=1` setting verified in the official r17b kit. Use that existing density handling. Current reset sites and sink bins are part of the new candidate. The older kit4 has explicit relay sites absent in r18, so its physical sign is a witness for the missing parameter. The kit4 routed LEC client was waiting on E9 admission at 11:2x. New private place requires republishing just the CTL wrapper from the chosen exact plan; review the resulting placement before any new route.
