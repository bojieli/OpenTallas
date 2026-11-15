# DIE-QC-GRT0 handoff (2026-11-14 ~22:10 PST)
## Scope
QC die GRT0 + die STA on plan of record zz_s29_qc103_s3r.json (sha 7480f383f88e), ADVISORY, DO_NOT_COUNT.
## Prior QC run found
DIE-PROTO-1 qc/s3d (epyc9 die-proto-1c): GRT 0 ov TT+FF, setup TT intra +362.0 / seam +536.6, hold BLOCKED(kits). Chain = qc_chain.sh (die_trial kit regional link_htree + combo GRT TT/FF 50 it + tap arrivals + die_sta_related).
## Run (nothing new written; copy of qc_chain.sh retargeted)
Script epyc9 /srv/opentallas-scratch2/claude/die-grt0-qc/qc_chain_s3r.sh (E=wt/qc-s29-tree2 tools, P=s3r, maps copied from die-proto-1c, stops after REG_STA). Region map regions_s3d.json (377/377 partitions match; plain-seam components may differ slightly for s3r - caveat).
Launch: ot-run --crit --hosts epyc9 --mem 32 --threads 24 --priority die (client log intel2 ~/dgrt0qc/run.ot), unit oth-ubuntu-625112-1794722912, started 06:08 UTC.
Out: epyc9 .../die-grt0-qc/qc/s3r/ (CHAIN.log, kit/, reg/grt_TT, reg/grt_FF, reg/sta, kitwin.json). Raw guide: reg/grt_TT/route_TT.guide (combo.tcl write_guides).
## Next
On CHAIN_DONE: overflow per layer/hotspots, STA per domain, clock-only M8/M9 guide filter, peak RSS (combo log /usr/bin/time). Re-run if S3R3b/S4 adopted.
