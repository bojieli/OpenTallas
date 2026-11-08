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

Actual review saved on hub branch8010063d2f: results/geom_review/codex_kv_wisplit_0222/{layout.png,review.json}, verdict FAIL. Current candidate all27 invariants PASS; three complete station clouds translated out of macros. P&R held. Next dry candidate band1555c moves host seam855.36->846.72 to provide8.64um halo at peer/tx south edges; adds crossing-source attribution to locate host cut drivers. No new stages in this geometry-only candidate.

## 2026-11-08 03:11 PST reach and full sizing

Latest saved hub source5f70b67773; own probe scripts are being extended before nextcommit. f focused checks:0 macro-site errors;0 density/track errors beyond required per-part G2 receipts; LN cut failures0. Five long hops413..695um remain in f; g legalizer now accounts for actual input/output windowcentres and both neighboringstagecentroids. g_reach_compact resolves those5 originalhopclasses; retains2 genericrelay hops479/452um and1 station-spacing error because1-stage relay slots have no bit_sites. gfinish2 adds pricedexplicit relaystage geometry; original gfinish failed an IndexError onmulti-stage synthetic templates, fixed to materialize each oldstage separately; failedlog retained.

Sizing: reach draft146 stationpositions =13,680 additionalFF bits, max additional8cycles onone lane (not146serialcycles). Perpart addedFF HB10,105/HT1,961/LN1,614. HB native127,559 +reachFF10,105 +generic-cutfaceFF17,598 =155,262 cells estimate before extraFT/buffers/CTS, above conservative150k target; NOT a hard newgate. No physical pilot. h exact-original-FT-FF attribution adds4239FTFF+13,829genericfaceFF to native130,883 =>148,951 FF-only estimate, plus INV/BUF/reset/CTS stillunpriced. Full record epyc6 ownroot/h_station_size.json; no final synthesizedcells claim.

RebalancingFAIL: naive110k native-cap split cut27,527-cell FDI qb bank from decoder, adding21,258 nets and31,562pins HB/HT. Cause MEMORY-CUT; never built. New h_atomic keeps entireFDI join atomic when relocating nativehostlogic; admitted epyc6, intel2 log /home/ubuntu/codex-kv-wisplit-0222/band1555h_atomic.otrun.log. h hostcut1175.04 has8.64um halos between rows and usesdirect LN/LE seam1192pins/146.88um rather than detouring651b throughHT; noPOR changed.

2026-11-08 03:43 PST stopped all flattened-label rebalances. Exact FDI module source found and full-depthRF proofPASS, privatebranch ebddca39df; continuation in CODEX-KV-FDI-0222.md. Westchannel34.56um independentdraft completes: bothLW cut failures resolved; remainingHTcut1.05 andnormalreach needsknownrelayer. NoP&R onWi.

## CLAUDE RESET handback

No new launches after reset instruction. Wi dry geometry branch `codex/kv-wisplit-0222@7921f6e53a` is parked. Exact FDI structural replacement branch `codex/kv-fdi-0222@40d31826b2` is pushed; see CODEX-KV-FDI-0222.md for all paths and live unit. The independent west-channel move removes both LW cut errors. Older five-part drafts still have host cut/reach errors and are NOT released to physical build. All flattened-label/BFS host rebalances are retired after they separated banks from anonymous decoder logic. Exact production hierarchy extraction now leaves a directly measured 17,500-cell HOST parent with the complete FDI block separate; this supports developing a unified HOST part and removing the speculative HB/HT seam, but requires fresh integration, clock/reset/station sizing and geometry. No production adoption or final fit is claimed. Live FDI CTS/GRT screen on intel1 unit `oth-ubuntu-3007534-1794140402` is healthy at last collection and must be left running; actual GRT review is required before detailed route. Existing owner reset/+2-cycle questions remain plain text in CODEX-LOG. No merge/tag/POR edit/deletion chain occurred.
