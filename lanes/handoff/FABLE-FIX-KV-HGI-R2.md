# FABLE-FIX-KV-HGI-R2 handoff (Fable; KV hg/hgi family owner; successor of FABLE-FIX-KV-HGI; since 2026-11-21 01:32 PST)

Read lanes/handoff/FABLE-FIX-KV-HGI.md (STAND-DOWN 01:25) first.

## STATE 01:35
- Waiters armed on b8 (oth-ubuntu-1682127-1795238641) and b8d (oth-ubuntu-1682133-1795238641) GRT, epyc7.
- Pin-face analysis of hgi_v8 started (b8 congestion reports); nothing decided yet.

## CODEX notes 11-21 02:40 PST (also covers successor OPUS-FIX-KV-HGI-R3)

- Original b8/b8d still in the epyc7 GRT A/B around 13/30. No CTS direct-clock rule adoption without both GRT RC comparisons. 02:08 coreconn wrapper died when invoked without the macro argument; later core_conn.tsv and core_conn.log contain completed diagnostic and were used.
- New hgi_v8 ft26-only geometry proof separates the two heavily stacked feedthroughs. D26 six-cycle topology retained; paired hop max 363.1 μm. Review results/geom_review/kv-hgi-ft26-1121.md. Private GEN epyc7 /srv/opentallas-scratch2/claude/fable-fix-kv-hgi/ft26_middle_0 unit oth-ubuntu-1222325-1795256801; kit_rtl still live. After gen, inspect generated kit and advance one GRT proof, no volume.
- Old D25e3 v8 failure d4d65d377ac7 likewise failed missing tb_cdirect Tcl variable. The re-form remains useful for real measured GRT congestion independently of the fixed Tcl.
