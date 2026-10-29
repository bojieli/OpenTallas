# TOKEN-COVERAGE (lane TOKEN-COVERAGE-1) — token-pass evidence audit, all 5 dies
## 2026-10-28 20:08 PDT TOKEN-COVERAGE-1 RESULT (ESTIMATE/AUDIT ONLY; no builds, no code changes)
Trigger: KV 4051 tok/s was a composer number; whole-die vehicle never ran on a bound die; V/command 16-114-cycle misalignment unseen (CLOCK-KV DIE-KV-16/17).
Labels: CHECKED = read from a log/file today by this lane (or its read-only sub-audits); UNCHECKED = copied from a lane line or an estimate.
Release gate = freeze gate + token pass. ANSWER: NO die has a whole-die token simulation on its current bound netlist + compiled image. Every tok/s headline is an analytic composer.

### Summary table
| die | tok/s source | whole-die sim on current bind? | image/programme compiles on current bind today? | current bind strict-clean? | whole-die sim cost (est.) |
|---|---|---|---|---|---|
| S81 | composer: 3655 MTP / 1260 AR (compose_tok_s, 10-26) vs 2749 / 785 (compose_tok_ds, 10-25 lat table) — two composers disagree | NEVER (L14 carve OOM 96 GiB 10-26) | NO: L0 24 LOWERED/41 PARTIAL/0 GAP on stale die_b178 (10-27 18:01, CHECKED log); L2/L14/L20/head/MTP have GAPs | NO: die_b178 strict FAIL (81 tied, 59,845 unread, 31 open); vehicle predates plan_s10/s11 | 400-700 GB, 8-16 h build, 1-4 h per layer; intel1 only (disk) |
| s81_head | per-token cycles 9,294 (+171 landed, analytic) inside S81 10,357 window | NO (TOK-15 die spine 8,691 cyc bit-exact + mutants, but on 10-27 top WITHOUT clock landings; DIE-HEAD-17 landed bind never simulated) | rank-0 ROM images 253/253 OK (straps unchanged, CHECKED); rank 1-3 never generated; START programme/boot not compiled | DIE-HEAD-17 CA bind (scratch inputs, not in main plan) | (A) TOK-15 vehicle regenerated --clock-landing: 30-60 GB, <1 h; (B) full 264 bundles 250-500 GB, 3-8 h |
| qwen_compute | QCE composer 296,341 cyc = 4051.0 tok/s (QC v7, 10-20 die edges, branch not on main; CHECKED README) | NEVER (v7 whole-QC lint stopped at 83 GB) | NO: qc-programme BLOCKED by design (head_prepare_edges=null, exit 2) | NO current RTL bind (main bound = qc10 10-23; plan moved CB16/A0/12.16e) | 400-600 GB, 4-8 h build; 1-3 cyc/s -> L0 1-3 h, one token 27-80 h; epyc2 |
| qwen_kvsys | same 4051.0 composer; est. -0.71..-0.75 % on bind5 (UNCHECKED) | NEVER reached token phase; B48 BOOT PASS + native calendar FAIL @27998 (10-27, CHECKED log) | NO: native compile on bind5 FAILS "attention service needs 1697 edges, link slot 1689" (CHECKED intel1 die-kv-17-1028/boot5/native_compile.log); legacy: no collision-free MU frame | YES bind5 0 errors (DIE-KV-16, UNCHECKED here) | build ~253 GB/~4.2 h (CHECKED), run 1.09 GB RSS 8.6 cyc/s (CHECKED): boot 1.3 h, 1 token <=9.6 h (UNCHECKED proj.); intel1/epyc2 |
| hbm | 1906 accepted -> 1851 (tok_rerun_c22) -> 1829 (with REBAL-9) all price model on a 10-10 programme; base inconsistent (1906 / 1836.5 / 1902.26) | NEVER; VMX-TOK-1 (epyc2) runs a 10-23 SW-quadrant slice: 8/9 replays SLICE_FAIL all checks INCLUDING base (CHECKED acceptance.json); 9th live 5 h, failing | NO: layer_images only against stale r18h5 slice; no unified 4-role top, no 4-role calendar/START authority; reporter hard-codes INCOMPLETE (CHECKED) | NO: sbind c20j 473 errors; SU/SFU bound to STUB RTL (COORD 19:48 blocker) | 120-270 GB, 8-12 h build, 10-20 h per layer; epyc2 |

### Per-die detail
#### S81 (DS ROM array) — owner DIE-S81-16/17, token TOK-DS
| q | answer | label |
|---|---|---|
| 1 | composer only (two composers, 3655/1260 vs 2749/785); compose_tok_ds --layer-cycles never fed measured replays. Components bit-exact: L0 gu 30/30 rows, vs family (swearly mutant ESCAPED), svc s1/s2 PASS + 3 controls FAIL as intended, GB one-frame + 3 controls, GB 6-lane landing 44/44, XR7 vpx 5/5 + 10/10 mutants | components CHECKED/UNCHECKED mixed per sub-audit; composer UNCHECKED |
| 2 | NO full image anywhere; nothing compiled today; compile targets die_b178 (10-27, a5778b98), not plan_s10 5f014a8d3554 / s11 778e9af860b0. Light compile ~12 min/0.3 GB + 4x16 GB frame extraction, but still stale b178 -> not run | CHECKED (logs, git) |
| 3 | per-frame landing-K gate (static frame_lk.json K=2, 10-27), as-built calendar extraction + sha256 plan check, GB manifest guards — only when compile_layers is run by hand. NOT checked: count-aligned crossing latencies vs compiler frame K/calendars (tools/s81_dv never reads count_align); die_b178 vs current plan; composer lat table (10-25, plan v4.8) vs plan; ROWX/XR; DS collectives cross-die; S81<->HEAD seam; u_phy_hbm inputs; 41 PARTIAL producer lifetimes | CHECKED (grep main 410e940f4) |
| 4 | 400-700 GB / 8-16 h build, 1-4 h per layer (13-28k cyc); full AR token ~950k cyc = days -> target whole-die L0 replay; intel1 (756 GB avail, 1.8 TB disk) | UNCHECKED |

#### s81_head — owner DIE-HEAD-17
| q | answer | label |
|---|---|---|
| 1 | head_native_1351 one partition 128 rows PASS_PARTITION_ONLY (codex/head-token-1351@a83b322b56); TOK-14 253/253 tiles bit-exact one at a time; TOK-15 die spine (c4147504b5) 8,691 cyc bit-exact golden argmax, GO_DROP/boost caught, built from main 542a4f321 WITHOUT --clock-landing, tile bundles replaced by 8,419-cyc view, serdes/mesh/host stubbed | CHECKED (result.json/README) |
| 2 | rank-0 images valid (straps unchanged vs DIE-HEAD-17 plan, CHECKED diff); rank 1-3 never; 264-tile source gen done 13.7 GB but never run; START programme not compiled | mixed |
| 3 | per DIE-HEAD run (own scripts): count_align_plan + MC 2000, count_align_bind, start_stage_emit proof (683 edges), die_sta_related. NOT checked: landed generated top vs reference with declared latency (no gen_rtl-top verifier; full lint OOM 96 GB); equal K across one lane split over several crossings (KV-type valid/data skew); sp3->sp2 K 4->5 +1 cycle; HEAD<->S81 xb ingress 160 beats / 10,357 window vs current S81; rank merge vs real peers; host_tx/rx +42; START release cycle offsets over 358 stages; regen_constants has no s81_head mode | CHECKED (grep) / UNCHECKED (lane) |
| 4 | (A) <1 h, 30-60 GB on epyc2 — catches landing/START misalignment; (B) 250-500 GB, 3-8 h, 20-40 min per position | UNCHECKED |

#### qwen_compute — owner DIE-QC-23
| q | answer | label |
|---|---|---|
| 1 | QCE composer (claude/tok-qk-qce-1026@1121cb654, not on main); QCLM 259/259 = single-stage cases on ONE s8 slice row of 10-23 bound_r8 ("QC 36/36" is NOT 36 chained layers); MAT 112/112; XD4 QC<->KV: roundtrip 1957, period 7056, ovl4u 87,539.1 cyc/tok, 15+8 mutants (results/token_pass/qc_kv_link_b48_1026) on KV B48 seams 68/66/67 TXDP_K 03030489 | CHECKED (files on main) |
| 2 | NO (qc-programme deliberately BLOCKED; no current bind; HOST publication date unknown) | CHECKED README |
| 3 | per bind (recipe-wired): bind verify, strict port_bind, land_align=r8, coll_regen, qc_tree_pads. Lane-only: regen_constants (--peer), CB16 phase-class gate, count_align_bind. NOT checked: QC<->KV seams after KV re-bind (bind5 90/88/78 TXDP_K 030304a9 vs XD4 68/66/67: +~32 cyc each way, "fits slack" claim made for +130/layer, now ~+194, UNCHECKED); +3/+6 landing-seam repricing (143 seams); count-aligned sched_lat (g13b 2,537 crossings, +2 relay on 493) not consumed by any token tool; HOST publication; RoPE row cross-die; reset/START wavefront (origins up to 50 cyc) | mixed |
| 4 | 400-600 GB, 4-8 h; 1-3 cyc/s; epyc2 | UNCHECKED |

#### qwen_kvsys — owner DIE-KV-17 -> DIE-KV-18
| q | answer | label |
|---|---|---|
| 1 | 4051.0 = nativev7 composer. Components: PV pair bench (V/cmd driven at pair pins), vport RT/DQ lockstep 128000 checks, pv_pair 12-cyc LEC 101305/101305 + mutant. kv_dieslice: B33 run7 BOOT PASS 7404/7404 (10-26); B48 BOOT_LOAD PASS, native calendar dcal FAIL fault1 @27998, frame mutant CAUGHT; token phase never reached; never run on DIE-KV-13..16 binds. bind5m V mutant caught only statically (V-D-H) | B48 CHECKED (intel1 codex-qk-boot-0818/nominal sim.log+time.log); rest UNCHECKED |
| 2 | NO (see table; PAD 8/16/32/64 does not close; DIE-KV-18 ASK DEFAULT YES fixes rule structurally) | CHECKED log |
| 3 | bind.py strict (port-bind NO STUBS, R8 align, straps); lane-only: regen_constants --die qwen_kvsys (pv_trunk, vport, seam/TXDP, ahub, ectl), r8/kv_pv_v_pads.py check (V-D-H, new 10-28), kv_bootage RT/DQ in prep. NONE called by bind.py or autopilot: recipe has a "must PASS" note only. NOT checked: PV service vs pair link slot (found only by compile); QC<->KV pair image vs bound seams unless --peer run with current QC bind (no current QC bind exists); dcal WE/data relation (Codex WE pad 2->3 candidate not on bind5); HOST publication interval | CHECKED (git grep main 410e940f4) |
| 4 | build ~253 GB / ~4.2 h (16 t); run single-thread 1.09 GB, 7.143 ns/s = 8.6 cyc/s; boot ~40k cyc 1:17:42; 1 token <=296k cyc <=9.6 h; ~15 h total; intel1 or epyc2 | build/run CHECKED; token h UNCHECKED |

#### hbm — owner DIE-HBM-10
| q | answer | label |
|---|---|---|
| 1 | tok_rerun_c22 (claude/die-hbm-10-1028@d543581cfe, accepted_cost + hgi_sim over 10-10 g25 rank-0 programme, base 576,702 cyc) 1851 (-2.98 %, bounds to -15.1 %); 1829 with REBAL-9. SU PR0/PR1 component PASS + RED/CAL/EPOCH mutants (pinned 262d, 10-27). P3 whole-MTP images model-only (native_execution=false). VMX-TOK-1: stale r18h5 slice, ALL replays SLICE_FAIL incl. base, 0 records commit, fr_SW__fault; its +10-cycle "delta" is an emit-time schedule length, not a measurement | file CHECKED, model UNCHECKED |
| 2 | NO: no unified 4-role top, 4-role calendar (WSC/PK5/PB5), 5 reset offsets, START authority MISSING; latest plan event C24 3ab76af4 (G0C 16 err) not plan of record | UNCHECKED (lane) |
| 3 | per plan event: G0/G0C, CA plan check, layer_images calendar assert (VMX LX only), native_su_calendar reserve-component. NOT checked: NW/NE hub split (sbind 2.7k UNPLANNED bits, TYPE_SPLIT), 17 far-link hop chains vs compiler fixed READ 22/WRITE 19 (hop adders only in the price model), MU hub legs (81/103 not promoted), HBM<->QC/S81 collectives (last 10-24 main RTL), 8SM->4-role fold steering (+1 cyc/record) | UNCHECKED |
| 4 | quadrant slice measured: build 2 h 46 m / 30 GB, 2.5-5 h per DS layer at ~38 GB (CHECKED); whole die 120-270 GB, 8-12 h build, 10-20 h per layer (UNCHECKED); epyc2 | mixed |

### Ranked risks (highest first)
1. ALL 5 dies: no tok/s number has an RTL anchor on a current bind; release token gate is OPEN everywhere and every headline (4051 Qwen, 3655/1260 or 2749/785 DS, 1829-1906 HBM) is a composer. S81 has two composers that disagree by ~25-38 %.
2. Cross-die seam drift is unwatched: KV re-binds moved QC<->KV seams +~32 cyc each way since XD4 (B48) and nothing re-ran regen_constants --peer / xdie / ovl4u; same class as the KV V/command miss.
3. Existing alignment self-checks are lane-script-only on every die (regen_constants, kv_pv_v_pads, frame_lk K gate, count_align_bind): neither bind.py nor autopilot runs them, so a lane that skips them ships a misaligned bind silently (KV-14d did exactly this). regen_constants has no s81_head mode.
4. Compiler/composer latency tables are not derived from the count-aligned plan on S81 (frame_lk static K=2, 10-25 lat table), HEAD (+171 analytic), QC (sched_lat unconsumed), HBM (hop adders only in price model).
5. HBM: no bind (473 err, STUB SU/SFU), no top, no calendar; VMX-TOK-1 is invalid as evidence (baseline fails) — its delta must not replace the VMX term.
6. KV: closest to a real run (bind5 strict clean) but image compile fails by 8 edges; dcal calendar fault from B48 still open.
7. HEAD: cheapest real check available (<1 h) and not yet done; landed bind never simulated.
