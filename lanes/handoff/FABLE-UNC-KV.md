# FABLE-UNC-KV handoff (Fable, started 11-23 ~01:45 PST; resumed after a 529 at 01:47)
Brief: rtx-pro scratchpad fable_uncovered_brief.txt + rules.txt. Local work dir rtx-pro scratchpad/unckv.
Scope (KV D29, cut 14:00, rows GATED by 13:00): one die-level port_in FF hold row (rc114 hroot, rc126 hgi, rc117 sys_c port part, pc port hold);
rc120 pc idpc y[2] detour cause; rc127 hg centre SRAM blob; rc113 hroot E strip; rc117 sys_c N-band taps + pin-reg insertion.
Owners: HROOT-R1 (RING/RES/EFS chain_j 56e157569c57), HG-R8 (rc126 REASONED 01:47; hg form writing), IOPC-R4 (keep pipe A/B), HUBC-SYSC-R2 (row C/D), TAP-GRID-R5 (sys_c 42 taps by 13:00).
Plan lane KV-PLAN-R6 (epyc8 kv-plan-r6/d29, base_d28 44c3cbf51e50, tree tools rt 94845431e6b2). Reviewer FABLE-RC-KVHEAD.
## log
- 01:55 read ledger, review TSV, owner handoffs/posts. No row of mine yet.
- 02:25 port_in hold classes measured (pregrt_ff_hold_open.tsv + reviewer paths.tsv): RING class = forwarded-clock landing ring inputs timed at plan clock.ring_hold.sender_ps -385 (not measured; KV-PLAN-R3 11-20 already ruled it CONSTRAINT for hroot, only hroot/io_cor/sys_SD_v1 got -50): sys_c 4 rings ~5.0k ends -40..-71, pc_v3 o_next -339 (receiver fclk tree 312-356 ps), hroot_Q_o_chN -231, hgi 143 ends >= -48. CTL class = start_i / arst_n / cland_tstart_in / ri_* spine resets on vclk in_min -75: hroot -105/-104.5/-33, hgi -77/-71/-40 and ri_head2 -165, pc ri_kvpc0 -106, sys_c -49; 1-5 ends per type, in every type; owner reset rule says these stay timed; die floor = kit slack + seam 100 - skew 25, so below -75 is open at die.
- Probes (ot-run from intel2 ~/tmp/fableunckv/rp_*.otrun.log, tools epyc8/9/10/intel1 /srv/opentallas-scratch2/claude/fable-unc-kv/tools/rprobe.{sh,tcl}, out .../rp_<n>/sender.tsv): min(data - fclk_out) per forwarded ring output on 4_cts DBs of hroot + hgi_v2cle (epyc8, disk-ETA hold), pc_v3 (epyc9), sys_c (epyc10).
- Forks: rc120 (pc idpc detour) and review of rc113/rc127/rc117 running; results come back to me.
