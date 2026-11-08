# KV Wi split takeover 2026-11-08 02:28 PST

CODEX took over: reduce Wi split geometry failures on codex/kv-wisplit-0222. Private sparse repo: epyc6:/srv/opentallas-scratch2/claude/codex-kv-wisplit-0222/repo (main 289149dea5). No plan of record changed; no route launched.

## CODEX notes

Current: original column split B <=150k per part, 27 invariants PASS, G0 +64 vs baseline; 38 face errors, 8 actual-bit site/core overlaps, 5 long mandatory-pin hops, 4 cut overflows, 9 census errors. Causes include 112um LN/LE seam, short N band with 1.05 cut ratio, post-split FT bit sites placed inside cores, and missing per-part face probes.

Running: epyc6 own root, band_main_probe.sh (ot-run log intel2:/home/ubuntu/codex-kv-wisplit-0222/band_main.otrun.log), band geometry YN1563.84 / YC855.36; expands LN across whole top edge. Computes measured cell/crossing table then new split and invariant dry run. First probe mistakenly used fleet /home/ubuntu/OpenTallas stale plan (different SHA from main), retained only as stale-base diagnostic; current probe explicitly uses own main289 repo. No result from stale base qualifies current work.

Next: read band result, fix bus window straddle ft25_o without altering its payload; then reduce HB/HT cut by whole fdi_join relocation, eliminate actual-bit station/core overlaps, space mandatory station hops to <=405um, and produce render for visual review. No P&R before clean geometry.

OWNER? Existing pending policy from DIE-KV-91 00:02: soft Wi parts in 16-edge reset contract; generic registered cut +2 cycles and resulting token schedule. Default: retain private dry design, no adoption.

## 2026-11-08 02:37 PST private structural result

Saved branch codex/kv-wisplit-0222@7d49a7841a on hub, no merges/tags/POR changes. Main-base band first dry exposed collector code assuming E/W joins; corrected it for actual N/S face normals. The 1555.2 top cut avoids all external bus-window straddles after ingest shifts south8.64um and three nearby station clouds shift south17.28um; ft0/1/10 top excursions move below the new seam without changing station count. Candidate band1555b: 60 types/164 partitions, 105 new ports,20 generic cut lanes,31 existing lane latency rows changed; untouched rows0. Original 27 invariants now PASS (band1555b_dry.json). Complete station-cloud legalizer moves3 groups away from cores; G0 running on this legalized candidate.

Measured rejection: whole fdi_join->HT (55,150 cells) increases HB/HT crossing7424->8468 bits; abandoned. Structural label grouping at depths7/9/10 does not reduce the7424-bit cut; this is a real connectivity problem. One remaining generator finding is HB|HT needs13.2 pins/um versus12.2: no P&R released.

Current job: complete G0 on epyc6 own mirror_band1555b/qwen_kvsys/plan_of_record/plan_c.json, log g0_band1555b.log. No EDA job started.
