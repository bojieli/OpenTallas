# HEAD native pass-through placement fix (trial)

Original hd_tile_so AP201f42719ae4 FAIL remains:929 captures>405um,max937.85.491output captures are caused by unconstrained source registers dispersed across upper/westchannels. The two existing512-bit pass-through stages now follow the actual WCAreader→centralcrossbar→Ecrossbar→Eoutput path. No RTL, IO, clock or cycle change.

Viewed bank_plan.png: both banks sit in the open upper horizontal channel, with the output leg along the macro E edge; wide buses do not cross macro bodies. PASS-COND for placement trial only. Independent actual placement census is pending. Alignment/shift/control families remain a separate source task.

Actual pilot epyc2:/srv/opentallas-scratch2/claude/codex-head-tileplace, unit2717589-1793257297, exit0: moved1024existing flops, detailed placement checkPASS, maximum legalization displacement10.4um. Synth aliases xo_q[511] to u_core.u_b.u_x.genblk1.g_line.line[255] (same D u_x.d[255]); that existing shared stage is retained and counted, no clone. Original countassertion and Tcl plumbing failures retained in trial1-4 logs. No P&R/STA/sign-off route.

The helper applies after the existing face/macro placement. It is not yet connected to production gen_phys. Remaining data path banks, full connected reach, clock assignment regeneration, image review and normal gates precede any route.

Independent follow-up GEOM FAIL: output family491violations removed, total929→671, max937.85→985.77um from moved xo_q[129] to retained u_x.line[897] feedback consumer. The shared full-graph placement successor owns this and all remaining controls/stages. Channel-h estimate2.47 at the new central bank also requires spreading/review before GRT. This pilot is not route-ready.
