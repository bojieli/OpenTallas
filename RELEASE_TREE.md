# OpenTallas release tree (pending only; refreshed 2026-10-25 23:33 PDT by CLAUDE RELEASE-TREE lane)

Snapshot: 2026-10-25 23:33 PDT · main cfea7b3a12 (= 877cfdeb28 + autopilot canary-gate fix) · FROZEN: QC plan@54a1aeb5 (441d1401 + batch 1), S81-HEAD plan@d7b8d1eb · no die has die STA on real views · flow tag flow-20261025-b not cut.

## EDIT · rules
- PENDING items only, one short line each, edited in place. Remove an item when done (evidence goes in PATH-FREEZE.md / lane files).
- Line form: `- [ ] ID task · OWNER · STATUS · current fact → DEP.ID` ; "→ X" means this item waits on X (each → is a link).
- Gate ids per die are PFX.BIND / PFX.GRT / PFX.CLK / PFX.STA (die gate = GRT0 incl. clock + related-pair skew <=80 TT/FF (owner 10-26) -> FROZEN; release gate = die STA on real views).
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS FROZEN BLOCKED NOT RUN.

## DIE s81 · S81 (DeepSeek ROM layer die) · rev main 9101a4f1 · est. after FT re-lay
- [ ] S81.GRT Die GRT0 · PATH-S81 / DIE-PROTO · FAIL · main 4.37M (L1 leaf FT); a8 re-lay die GRT 1,802,971 (21:12, unposted) → S81.FT
  - [ ] S81.FT FT window/station re-lay to a legal chain on every seam · PATH-S81 · RUNNING · a8 G0C PASS but GRT FAIL; coupons t53/t29 PASS, t24/t44 FAIL 26571/47247
  - [ ] S81.SST Knee bit-sites + tap_mode for t31/t43/t44/t49/t52 (one plan delta) · PATH-S81 · TODO · GEOM-8 STRUCTURAL FAIL → S81.FT
  - [ ] S81.PRICE Price FT stations (a8: 21 lanes +1..+8, 16,400 bit-cyc) · TOK-DS · WAITS · → S81.FT
- [ ] S81.CLK Die clock route + related-pair CPPR <=80 · CLOCK · NOT RUN · → S81.GRT, → SEAM.CLK
- [ ] S81.BIND Strict bind, 0 ties, on current main · TOK-DS · TODO · fresh bind on main877 not launched; PHY reset hop 788 um fix 0adb2ea659 unmerged → INFRA.MERGE
  - [ ] S81.TIES Svc dead-input proofs, relay pads, cfifo strap, no-repair SRAM view · TOK-DS · RUNNING · COORD 21:21 rulings; ABI fix 162f0033d
- [ ] S81.STA Die STA TT/FF on real views · DIE-PROTO · WAITS · → S81.GRT, → S81.CLK, → S81.TILES
  - [ ] S81.TILES Tile sign-offs (path parts trial-only until die gate) · PATH-S81 · WAITS · HCPL 1 DRT trial WAIT-CANARY; HCORE cap24 FF -5.34 → S81.GRT, → FLOW.TAG
- [ ] S81.XDIE PHY footprint, power and bump contract · OWNER · OWNER · research data still missing; diagnostics only

## DIE s81_head · S81 head die · rev FROZEN d7b8d1eb · est. after HEAD8 batch
- [ ] HEAD.GRT Die GRT0 · DIE-PROTO · FROZEN · ovf 0 on d7b8d1eb; re-run needed if the HEAD8 batch is adopted → HEAD.B8
- [ ] HEAD.B8 HEAD8 clock-tap + global START batch · CODEX / COORD · RUNNING · 187b63494b G0C+visual running; +8 slot cycles; needs ROOT approval
- [ ] HEAD.CLK Die clock route + related-pair CPPR <=80 · CLOCK · NOT RUN · → HEAD.B8
- [ ] HEAD.BIND Whole-head as-built bind · CODEX · WAITS · source d0eb3d3d01 ready; host/mesh/rank-row contract open (owner question in WAITS)
- [ ] HEAD.STA Die STA on real views · DIE-PROTO · WAITS · → HEAD.CLK, → HEAD.TILES
  - [ ] HEAD.TILES Head tile sign-offs · S81-HEAD · RUNNING · 16 hd_* WAIT-GEOM FAIL rows need successor/withdraw → FLOW.TAG

## DIE qwen_compute · Qwen compute · rev FROZEN 54a1aeb5 · est. after die clock fix
- [ ] QC.GRT Die GRT0 signals + clock · DIE-PROTO · FROZEN · 54a1aeb5 ovf 0; batch 1+2 re-freeze pending → QC.B2
  - [ ] QC.B2 Batch 2: STM ROMs (24) + SRAM d4ae52687 + DEAD-FAULT 773a8e2ad · ROOT-MERGE · COORD · approved 23:26; merge, then combined GRT0+clock → INFRA.MERGE
- [ ] QC.CLK Die clock related-pair <=80 · CLOCK / DIE-PROTO · FAIL · native mixed-NDR 574/506 ps TT/FF (seams 260/235); 57/50 estimate withdrawn
  - [ ] QC.CLKFIX D-QC-CLKMESH M8/M9 500 um mesh (contour8 found no legal pad sites) · CLOCK-MESH · RUNNING · model 26-41 ps; routed RC pending
  - [ ] QC.FEREACH D-QC-FE-REACH landed relays on FE face crossings (>5k arcs >405 um/tile) · PATH-QC + KITS · TODO → QC.TILES
- [ ] QC.BIND Bound wavefront reset/START + CB16 phase classes · PATH-QC · RUNNING · CB16 13f33606a 79/79 G0C; capacity/clock/G2 open
- [ ] QC.STA Die STA on real views · DIE-PROTO · FAIL · stand-in 441d TT +555 / FF -73, pair 119/110; 0 real views → QC.CLK, → QC.TILES
  - [ ] QC.TILES Path tile sign-offs · PATH-QC · RUNNING · A0 requalify (PASS-COND withdrawn); N59 LEC KEEP fix; SRAMIF PROG/BTAB input hold 935/1061 → FLOW.TAG

## DIE qwen_kvsys · Qwen KV · rev main 36164be0 (e055) · est. after it5
- [ ] KV.GRT Die GRT0 it5, strict core OBS + die clock (ruling a) · DIE-PROTO · RUNNING · 816,190 at 25% share; it5 on canonical plan not run yet → KV.SHARE
  - [ ] KV.SHARE Kits hg/hgi/io_W* reserve 0.5 M2-M7 FT in die-model tracks · DIE-PROTO · TODO · if it5 != 0, fallback (b) io_W3 row-0 seam (owner question in WAITS)
- [ ] KV.CLK Die clock route + related-pair CPPR · CLOCK · NOT RUN · → KV.GRT
- [ ] KV.BIND Strict repo-relative bind of record · PATH-KV · RUNNING · b15 intel1; b21 pad_por_n ERROR; seam bus skew
  - [ ] KV.PC833 PC833 LEC · PATH-KV · FAIL · NOT EQUIVALENT 528 pts each; calendar lowering being isolated
- [ ] KV.STA Die STA on real views · DIE-PROTO · WAITS · → KV.CLK, → KV.TILES
  - [ ] KV.TILES Tile sign-offs · PATH-KV · RUNNING · ASTK native TT -85.91 / FF -13.22, AS6 cea44fd4c4 next; SYS_C ff3c8ad8fe not ready → FLOW.TAG

## DIE hbm · HBM B2n successor (next release) · rev main B2n f710e18c · est. next release
- [ ] HBM.GRT Die GRT0 · PATH-HBM / DIE-PROTO · FAIL · edge+band 998,223 (M7 wrong-way FT over cores); corridor plan 82e095df4 → HBM.CORR
  - [ ] HBM.CORR M7 bank-wall corridors + composite plan · PATH-HBM · RUNNING · 113 FT slots geometry PASS; SFU corridor repaired; compose + G0 next
- [ ] HBM.CLK Die clock route · CLOCK · NOT RUN · → HBM.GRT
- [ ] HBM.BIND Native one-clock bind · PATH-HBM · WAITS · q3 API ebeccf1c4 + oneclk 847a25a065 unmerged; 6 TR3 proofs live → INFRA.MERGE
- [ ] HBM.STA Die STA on real views · DIE-PROTO · FAIL · TKM root WNS -1180; rootpipe 47a537213 ready, unmerged → INFRA.MERGE, → HBM.CLK

## TOKEN · Token-pass gate per design
- [ ] TOK.DS DeepSeek ROM token pass (S81 array + head) · TOK-DS · WAITS · real hcore config (no FG3) → S81.BIND, → HEAD.BIND
  - [ ] TOK.DS.LAYER Per-layer bound runs · TOK-DS · RUNNING · attention 14bc4dedd4 exact; SVCv2 closing job live
  - [ ] TOK.DS.XDIE Head/array inter-die traffic co-sim · TOK-DS · WAITS · → HEAD.BIND
- [ ] TOK.QW Qwen ROM token pass (compute + KV) · TOK-QK · WAITS · → QC.BIND, → KV.BIND
  - [ ] TOK.QW.LAYER QC bound layer run on plan of record · TOK-QK · WAITS · fresh CB16 schedule, no +0 claim → QC.BIND
  - [ ] TOK.QW.KV KV boot + MU image (F=2) from strict bind · TOK-QK · WAITS · b15 MU833 image compiled-not-qualified → KV.BIND
  - [ ] TOK.QW.XDIE QC<->KV traffic co-sim · TOK-QK · WAITS · → TOK.QW.LAYER, → TOK.QW.KV
- [ ] TOK.HDS HBM-DeepSeek token (next release) · TOK-HBM · RUNNING · stage-B 0d5e8ca1e8 component PASS, unmerged; pricing job live → HBM.BIND
- [ ] TOK.HQ HBM-Qwen token (next release) · TOK-HBM · WAITS · → HBM.BIND
- [ ] TOK.FREEZE Final evidence run at RTL freeze · COORD · WAITS · → TOK.DS, → TOK.QW
- [ ] MU.CURVE Latency-throughput curve vs A100 80GB · COORD · WAITS · → TOK.FREEZE

## FLOW · Flow release (2x/day tag, commit-tied evidence)
- [ ] FLOW.TAG Cut flow-20261025-b · ROOT-MERGE · BLOCKED · KV core canary TT +3.77 vs golden +36.61 (cap64 c) → FLOW.FANOUT
  - [ ] FLOW.FANOUT KV core TT repair without losing setup (LT_COPY/fence kit) · FLOW-FANOUT · RUNNING · cap64 held; MCMM 20b6 rejected
  - [ ] FLOW.CANARY Current-main canary set PASS (s81, head, QC, KV core, HBM SRAM) · FLOW-CANARY · RUNNING · main877 canaries submitted 23:22
- [ ] FLOW.ROMGATE Wire rom_infer_gate (0b6be8e6d) · ROOT-MERGE · WAITS · → FLOW.TAG

## INFRA · Merge and coordination
- [ ] INFRA.MERGE Merge READY sources: dieproto 77b2eec49, rootpipe 47a537213, q3 ebeccf1c4, stage-B 0d5e8ca1e8, lint 66b5af5ed, S81 PHY reset 0adb2ea659, QC batch 2 · ROOT-MERGE · COORD · all unmerged on main877
- [ ] SEAM.CLK Industry MSCTS local trees: remove ~190 ps local insertion gap (E5) · CLOCK · RUNNING · E5 CTS04b trunk slew + macro CK early still FAIL

## WAITS · who
### Waiting on the owner
- (owner 10-26: none; published-figure assumptions, lane S81-PHY-ASSUME)
### Waiting on COORD / ROOT-MERGE
- KV FT reservation: COORD 2026-10-25 23:42 = explicit reservation hook in the kits (routing guides/blockage on the FT tracks); G2 half-share alone is not proof. DIE-PROTO then runs it5 → KV.GRT
- HEAD host/mesh framing, ch_b source, ctl role, rank-row mapping: spec items for PATH-S81 + TOK-SCHED (no owner input needed) → HEAD8 batch
- QC batch 2 merge + re-freeze run; HEAD8 batch approval; INFRA.MERGE list.
