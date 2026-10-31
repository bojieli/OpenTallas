# OpenTallas release tree (pending only; refreshed 2026-10-30 18:09 PDT by CLAUDE coordinator)

_Updated 10-30 20:13 by COORD. OWNER 12.21 closure first; 12.22 watchdog + QC/HBM freeze + per-design count. Count S81 16/52, HEAD 2/3, QC 5/15 designs, KV 10/31, HBM 2 signed (cache on old plan). All lanes resumed 20:0x after session limit._

## EDIT · rules
- PENDING items only, one short line each, edited in place. Remove an item when done (evidence goes in PATH-FREEZE.md / lane files).
- Line form: `- [ ] ID task · OWNER · STATUS · current fact → DEP.ID` ; "→ X" means this item waits on X (each → is a link).
- Gate ids per die are PFX.INFRA / PFX.GRT / PFX.CLK / PFX.BIND / PFX.STA.
- OWNER 12.18 (2026-10-29 05:44 PDT): full-gate census per die -> lanes/CLOSURE-LIST.tsv (fixed list); rule freeze (new checks only by owner); hourly burn-down open/closed/added; all 5 dies in parallel.
- OWNER 12.17 (2026-10-29 05:31 PDT): freeze plan on die GRT0+clock pass (fix-only after); one clock tool ot_clk.py for all dies; 2 parallel fix variants per failing gate; strict bind clean before GRT counts.
- DIE METHOD = METHODOLOGY s12 v5.1 (v5.0: early taps = macro insertion balancing, AOCV 0.21%/mm gates; v5.1: trims/useful skew/pads sparse <=~5% + CLOCK-RESIDUAL ledger after structural fix; 5%/15% cost = targets) (OWNER 10-26, frozen; change only on measured failure + owner decision): 12.7 MASTER PLAN FIRST per die (census -> corridors <=0.6 -> bays <=405 um every path/layer -> M7 entry pins -> worst-case PG, PG-shielded clock, islands clock/reset only, one core latency) + static plan gates incl. analytic predictor BEFORE any block build; kits carry a plan slice. 12.8 clock by construction: plan-defined centre clock entry per core, 250 ps TT, structured core trees; NO early taps / post-measurement trims / clock ECOs / mesh-node CPPR (plan-computed per-tap sizing OK). Freeze = GRT0 incl clock (>=50 it) + DIE STA with the real clock on related pairs (TT setup, FF hold; CPPR to last tree node); 80 ps skew = design target only. v4.6-4.9: MSCTS H-tree->ONE continuous mesh (signed mesh = CPPR point)->short local trees; clock OCV = depth/distance table (draft, owner review); droop shared (clock charged differential only); data hold buffers allowed. 12.9: one owner per die plan/clock (lanes/OWNERS-DIE.md); gate numbers via NUMBER-CHECK.
- Release gate = die STA on real views + token pass.
- Status words: RUNNING WAITS TODO NEW COORD OWNER FAIL PASS FROZEN BLOCKED NOT RUN.

## DIE s81 · S81 (DeepSeek ROM layer die) · rev event3 + veskv (plan_h2_2249 bcfcb4e1737e + 070b83dd620) · HARD FROZEN 12.20
- [ ] S81.BIND Strict bind on event3+veskv+station form · DIE-S81-37 · RUNNING · veskv merged with bind verify as guard; station-form fix 90ba64737ef (+1 out-face reg on 207 unlanded slots) bind/clock rerun collecting → S81.STFORM
- [ ] S81.GRT Die GRT0 incl clock on event3 · DIE-S81-37 · PASS · event3 clock GRT TT/FF overflow 0 (10-30 03:39); rerun only if a one-block fix touches clock
- [ ] S81.CLK Die clock related-pair CA/OCV on event3 · DIE-S81-37 · RUNNING · CA PASS on event3; early-tap rows: attn/ve_m/vn_a merged, vn_b/vq rows + attn re-take from routed rt22 (one-block, die clock rerun)
- [ ] S81.STA Die STA on real views · DIE-S81-37 · FAIL · view STA -26.90 TT / -607.30 FF with missing core views (UNMEASURED ends) → S81.TILES
- [ ] S81.STFORM Station-form one-block fix (plan 42b082ebcc8c) · DIE-S81-37 · RUNNING · then move kit-wave source to new main + release station-kit hold
- [ ] S81.KVLEAF kv_leaf__t2 400,659 cells > 400k cap: cut on natural boundaries inside its slot · DIE-S81-37 · TODO · estimate first
  - [ ] S81.TILES Tile sign-offs · S81-CORES-KITS-6 / KIT WAVE / SIGNOFF-SPRINT-8 · RUNNING · 16/52 hard cores, 0/171 types (4 type records retired: views lacked plan pins); vq + NNfu retired (pins off plan / DB lost) and rebuilt; 11 cores LEGACY-NO-DB
  - [ ] S81.RT22 rt22 regional-tap core kits attn / ve_m / vs / vn_a / vn_b · S81-CORES-KITS-6 · RUNNING · GEOM PASS / PASS-COND (aspect only); route → sign-off → LEC

## DIE s81_head · S81 head die · rev l44 (80bde90d2a2 = l43 + pinslot one-block fixes) · FROZEN 12.20
- [ ] HEAD.BIND Strict bind on l44 · DIE-HEAD-45 · RUNNING · l43 strict bind PASS (358 inst / 6108 nested); l44 guard rerun after merge (FAIL -> revert)
- [ ] HEAD.GRT Die GRT0 incl clock · DIE-HEAD-45 · PASS · l44 = l43 exactly: GRT overflow 0 TT/FF
- [ ] HEAD.CLK Die clock related-pair spread/OCV · DIE-HEAD-45 · PASS · spread 122.3/120.1, OCV worst 149.78/142.16 (<=150), duty 0 outside 45-55
- [ ] HEAD.STA Die STA on real views · DIE-HEAD-45 · WAITS · → HEAD.TILES
- [ ] HEAD.RST HEAD die reset contract 64 edges (6e99021f310 merged) + HOST LEC rerun same netlist · DIE-HEAD-45 · RUNNING · HOST NOT EQ was LEC reset window, not logic; A/B LEC ETA ~23:30
  - [ ] HEAD.TILES Tile sign-offs · DIE-HEAD-45 · RUNNING · 2/3 hard cores, 0/16 types; LEP ECO5 e/f routing (11 macro clock leaves re-mastered, predicted pair skew 77.6/77.1 vs 80); SerDes ECO1B DRT 1 viol; 4 pinslot kits re-place on l44; wshim_rx lone-sink tap event

## DIE qwen_compute · Qwen compute · rev plan_qc49 (freeze-gate candidate, NOT frozen)
- [ ] QC.PLAN Freeze gate on plan_qc49 (G0C 0 new, strict bind 0, die GRT0 incl clock >=50 it, related-pair CA/OCV <=150 on routed clock) · DIE-QC-50 · RUNNING · routed-clock measure 2 ways (DRT NDR clock + RCX); gen47 Route A prebuild + NDR DRT live
- [ ] QC.STM stm/slice slot fix: every plan_qc49 slice type aspect 2.15-2.18, fill 0.03-0.09, clk_t6 15,603 sinks, r2r ~1565 um → all 11 stm kits GEOM FAIL · DIE-QC-50 · COORD · plan delta (slot/outline + tap split, estimate + render first) inside the freeze-gate work
- [ ] QC.BIND Strict bind on plan_qc49 · DIE-QC-50 · PASS · 0 errors (377/119/1921/790393) on the 11 stm kits' bind
- [ ] QC.GRT Die GRT0 incl clock · DIE-QC-50 · WAITS · → QC.PLAN
- [ ] QC.CLK Die clock CA/OCV on routed clock · DIE-QC-50 · RUNNING · → QC.PLAN
- [ ] QC.STA Die STA on real views · DIE-QC-50 · WAITS · → QC.GRT, → QC.TILES
- [x] QC.PHYPG QC PHY PG contact model (30 um finite M9 pad 11.2 mV vs point contacts 39.7 mV) · OWNER · DONE · OWNER chose A: modeled 30 um contact, flagged as assumed IP geometry
  - [ ] QC.TILES Tile sign-offs · QC-KITS-AB / DIE-QC-50 / SIGNOFF-SPRINT-8 · RUNNING · 5/9 hard cores, 0/68 types; rp1 old f62 record retired, re-signed 17:55 at f-qc on the plan-of-record f4g DB (QC-RP1-1); BTAB P4 NOT SIGNED (slew/DRC), P5 variants running; 11 aspect-OK kits placing (glue, tt_ctlm, coll_n/s, native59, sle_ctl x4, coll_ft x2)

## DIE qwen_kvsys · Qwen KV · rev event28w_c · HARD FROZEN 12.20
- [ ] KV.BIND Strict bind on event28w_c · DIE-KV-48 · PASS · plan of record bind clean; SD re-site 5aa1fd08b77 merged
- [ ] KV.GRT GRT0 incl clock at >=50 it · DIE-KV-48 · PASS · tap-only GRT on sd47 spread 69.8/56.6, 0 illegal sites
- [ ] KV.CLK Die clock CA on the sd47b tree · DIE-KV-48 · RUNNING · sd47 as merged FAILS 4 SD->io ports (TT -195.9); sd47b (0aa0b4f032c merged) PASS TT 110.4/111.7, FF 100.0/228.1; KV clock rerun + START emit on sd47b next; SD kits count only on sd47b
- [ ] KV.STA Die STA on real views · DIE-KV-48 · WAITS · → KV.CLK, → KV.TILES
  - [ ] KV.TILES Tile sign-offs · DIE-KV-48 / KV-KITS / SIGNOFF-SPRINT-8 · RUNNING · 10/31 hard cores (q0, PHY103, CDC319, Q1, e1 counted today), 0/40 types; Q2 FF -1.52/5 EP + slew → ECO + re-sign at b-kv (→ FLOW.KVTAG); RX SDC regen + re-sign same DB; core_tx placed TT -423 -> -57, LEC ETA ~20:30 then route

## DIE hbm · HBM unified SU/MTP/MU · rev d41c (2371eaacbf9) · candidate d41f = d41d + d41v
- [ ] HBM.PLAN d41f as plan of record (strict bind 66 -> 46 pairs, 46,952 -> 31,310 b) · DIE-HBM-43 · RUNNING · G2 face probes on intel1 (q_hub_nw OOM at 160g -> rerun); face_budget.py must clear 16 face-density findings → G0/G0C 0 new
- [ ] HBM.GRT Die GRT0 incl clock at >=50 it · DIE-HBM-43 · RUNNING · windowed GRT d38a vs d38s (20 it: d38a wins hot window) ETA ~21:30; epyc2 50-it GRT ETA 00:30-01:00
- [ ] HBM.BIND Strict bind · DIE-HBM-43 · RUNNING · 46 residual pairs on d41f; full 26-pair V-A rejected (G0 +21 / G0C +62)
- [ ] HBM.CLK Die clock CA/OCV · DIE-HBM-43 · WAITS · → HBM.GRT
- [ ] HBM.STA Die related-pair STA real routed clock · DIE-HBM-43 · WAITS · → HBM.GRT, → HBM.TILES
- [ ] HBM.IDX IDX scorer glue b100->b102 (TOK-13 A1, ~1677 tok/s) · DIE-HBM-43 · TODO · build only if free for closure (OWNER 12.21)
  - [ ] HBM.TILES Tile sign-offs · HBM-CORES-KITS-29 / KIT WAVE (after freeze) · RUNNING · 2/210 hard cores (collar, ring), 0/49 types; EP205 routing; QUERY GRT hang stopped + relaunched 17:34; exp0_anchA GEOM PASS -> CTS/route

## TOKEN · Token-pass gate per design
- [ ] TOK.HBM HBM speed on plan of record · TOK-13 · PASS · d41c + V-A exact 1671.8; buildable best ~1677; OWNER 12.21: ~1677 ACCEPTED, tok/s loss from closure fixes is not a gate on any die
- [ ] TOK.DS DeepSeek ROM token pass (S81 + head) · TOK lanes · BLOCKED · 0/6 layer types on current die (last checked 10-28); waits S81 bind on frozen event3
- [ ] TOK.QW Qwen ROM token pass (QC + KV) · TOK lanes · BLOCKED · QC 36/36 PASS (10-28); KV boot bound measured cold 840 / warm 74 (owner-approved one-time boot charge); KV 0/36 → KV.CLK
- [ ] TOK.E2E End-to-end token pass · TOK lanes · NOT RUN · not passed on any die; components only
- [ ] TOK.FREEZE Final evidence run at freeze · COORD · WAITS · → TOK.DS, → TOK.QW
- [ ] MU.CURVE Latency-throughput curve vs A100 80GB · COORD · WAITS · → TOK.FREEZE

## FLOW · Flow release
- [ ] FLOW.TAGS Per-die flow tags 2x/day (12.9e) · FLOW-11 · RUNNING · 10-30 tags a..f per die cut (d-s81, e-head, a-kv, d-qc, f-hbm); re-sign tool resign.py + clock_family export + prov() kit-record skip merged
- [ ] FLOW.KVTAG Cut flow-20261030-b-kv (KV Q2 fails macro-lib check at a-kv) · FLOW-11 · RUNNING · canary NO-REG first → KV.TILES
- [ ] FLOW.COUNT Honest count: re-sign same routed DB at a tag + PROVENANCE; retire-by-name for records off the plan of record · SIGNOFF-SPRINT-8 · RUNNING · hourly forced count at :05

## INFRA · Merge, hosts, disks
- [ ] INFRA.MERGE Approved READY lines merged in order (results first) · ROOT-MERGE-AF · RUNNING · ~30 merges 15:00-18:10; main 202 commits since 03:30
- [ ] INFRA.DISK Disks · COORD / FLOW-11 · RUNNING · localhost root 92% (Codex *-1448 worktrees prunable after ~03:00 10-31, idle >12 h); epyc2 scratch 86% -> canary prune to <=80%; intel1 79%, intel2 71%

## WAITS · who
### Waiting on the owner
- (none open; QC.PHYPG closed by owner: A, 10-30)
- Older, defaults in force: S81 global START registered recompose, real PMA view/period/source, QC UCIe lclk, HBM stack3/Engram mapping, KV T6.
### Waiting on COORD / ROOT-MERGE
- none open (all READY lines through 18:10 ruled).
