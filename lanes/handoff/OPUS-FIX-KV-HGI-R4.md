# OPUS-FIX-KV-HGI-R4 handoff (Opus; KV hg/hgi family owner). Successor: OPUS-FIX-KV-HGI-R5. CURRENT 2026-11-21 07:2x PST

## STAND-DOWN 07:2x PST (COORD, context). R5: read this section first, then the R4 sections below.
Running units (leave alone; re-arm waiters with OT_LANE=OPUS-FIX-KV-HGI-R5, ot-wait <unit|pid>):
- prep_d26 (mine): epyc7 oth-ubuntu-2684513-1795273452, intel2 client pid 1216269, log intel2 ~/tmp/opusfixkvhgir4/prep_d26.log.
  Runs epyc7 /srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r4/prep_d26.sh: kst_xstreet_v2.py on the APPLIED D26 plan ->
  ana/plan_r4d26.json (+ kst_xstreet_d26_report.json, depth-3 report), private skeleton tree26 + rt launch tree launch26 (rt/current).
- b8 / b8d core-tap A/B GRT, epyc7 oth-ubuntu-1682127 / 1682133-1795238641 (R3 units). GRT round 2 (after NDR disable) extra it10 at
  14:44 UTC; congestion sum (capped 20k gcells) it10 b8 48,872 vs b8d 49,068: equal. Decision needs the GRT RC readback when 5_1_grt.odb
  exists (Fable handoff STATE 21:30 steps 1-3). Not decided.
- ft26 pilot (Codex) epyc9 oth-ubuntu-3222492-1795259200.
- relayfit A/B running on epyc10 as oth-ubuntu-3125913-1795262038 (intel2 client 42768).
- Stale record otrun-tolerant-swine-271965 (setup_r4 on epyc8): I killed that held client (my pid); nothing ran.

- UPDATE 07:3x: prep_d26 DONE rc 0 (oth-ubuntu-2684513-1795273452). epyc7 W/tree26 + W/launch26 ready, plan 8e916c6fcb01 (D26 a9f605cb1acf + x-street kst + v8 taps). Report W/ana/kst_xstreet_d26_report.json: all 11 hgi types 0 kst sites left in cores (v5/v6/v8 head2 now routed), depth-2 max centre hop 366 / bit 386; hg (8 types) still 136 inside + hg_v1 head0 e4 1806 um detour; 62 rows skipped (die-edge endpoints, mostly rows that need no move). Next: G0 + bind gates on W/launch26 (commands above), then gen_v1.sh.
kt re-site bind status:
- r3 plan 152d6c878972 (straight re-site): G0 PASS 0 errors (+61 station_core, +60 routed_reach: e4/e6 hops 546 um round the cores).
  Its strict bind oth-ubuntu-1244823-1795267991 I CANCELLED (superseded by the COORD 06:3x order; do not carry 152d rows).
- r4 x-street rows on D27d: epyc8 /srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r4/ana/plan_r4.json (report kst_xstreet_report.json,
  depth-3 report kst_xstreet_d3_report.json). NOT bound: epyc8 scratch2 fell below the 50 GB floor (200 GB/h, not mine), so setup_r4 never ran.
- r4 on D26 (epyc7): prep_d26 above. Next when it ends: ot-run --priority plan --hosts epyc7 --mem 56 --threads 3 --dir W --
  bash W/g0_d26r4.sh W/launch26 W/g0gate26 ; and bash W/bind_d26r4.sh W/launch26 W/bindgate26 (same flags). W = epyc7
  /srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r4. Bind green -> ot-run --hosts epyc7 --mem 24 --dir W/v1 -- bash W/gen_v1.sh
  (hgi_v1 wave-env replay of D25e3 attempt_4; already points at tree26/launch26), diff W/v1/gen/kv3_hgi_v1__cl141fc26e/config.mk vs
  epyc7 kw43-wave-1109/.../KV-D25e3/items/kv3_hgi_v1__cl141fc26e/attempt_4/gen/kv3_hgi_v1__cl141fc26e/config.mk, then run_kit.sh
  GOAL=route, read GRT congestion-10 at the head-core faces vs the wave kit, sign-off gates.

Open with COORD (posted 06:5x DECIDE): kt depth 3 needs RTL (kv_head_kst DEPTHS 0-2) + e0/ECTLK cores (HXK) + calendar D_QK; my default is
depth 2 (e6 hops 346-360 um, under 405). ectl 482 um is q (320,640) -> stale to_um (133,935); real consumers hst2_g/hst3_g (31/265 um);
check placed hst_g in the hgi_v1 kit before adding a station. hgi_v8 taps clk_t81/clk_t82 are in the r4 plans.
Generator gaps: v1 (plan_r4.json) skipped hg (8 types) and hgi_v5/v6/v8 head2 rows (endpoint at the die edge); v2 adds endpoint
snapping (used by prep_d26); check its report for remaining skips and the hg_v1 head0 e4 1806 um detour (astk cores).
Cleanup still to do (ot-delete refuses while the paths are live): epyc10 fable-fix-kv-hgi/{b8,b8d}, epyc9 ft26_middle_0/gen_ft26_relayfit,
after b8/b8d and relayfit end.


Work dir: epyc8 /srv/opentallas-scratch2/claude/opus-fix-kv-hgi-r4 (gen_v1.sh, kst_xstreet.py, ana/). R3 dir (read-only inputs): opus-fix-kv-hgi-r3.

## Units in flight (waiters armed by R4; OT_LANE=OPUS-FIX-KV-HGI-R4; cancel only with ot-run --cancel)
- b8 / b8d core-tap A/B GRT, epyc7 oth-ubuntu-1682127 / 1682133-1795238641 (logs intel2 ~/tmp/fablefixkvhgi/b8*_grt.log). Decide OT_TAP_CORE_DIRECT.
- ft26 pilot GRT (Codex), epyc9 oth-ubuntu-3222492-1795259200.
- relayfit A/B: RUNNING on epyc10 as oth-ubuntu-3125913-1795262038 (intel2 client 42768).
- r3 strict bind + LATCHECK epyc8 oth-ubuntu-1244823-1795267991 (plan 152d6c878972). r3 G0 DONE: PASS 0 errors, +61 station_core +60 routed_reach
  (the e4/e6 hops route 546 um round the cores) -> FABLE-PD-KV-0730 section 3 confirmed by the tool.

## COORD order 06:3x (FABLE-PD-KV-0730, lanes/FABLE-PD-KV-0730.md): do NOT carry 152d kst rows; re-emit e4/e6 x-street form +1 station;
   add hgi_v1 i_ectl_Q_N_tN station; add hgi_v8 t36 tap; prove in the hgi_v1 wave-env kit; rows to KV-PLAN-R5 for D28.
- kst_xstreet.py (r4 generator): grid street router round all hard cores (margin 12, near-core cost 25 um, turn penalty), stations at
  equal ROUTED arclength, per-bit kst sites spread 4 x 17 at 2.16 um (no point clusters). First run (row selection too wide) gave
  routed lengths e4 717 um, e6 1037 um (hgi): depth 2 -> centre hops 239 (e4) / 346 (e6). e6 needs depth 3 for <= 300 (259).
- DEPTH 3 IS NOT A PLAN ROW: tools/qwen_kv_die/kv_head_kst.py DEPTHS=(0,1,2) ("head RTL fails elaboration on anything else");
  KST also sets HXK (ECTLK quarter cores, +KST) and D_QK (attention calendar boot word), and the e0 core (gen_core_kit_kv.py --head-kst)
  -> RTL + e0 core + ectl cores + calendar change. Posted to COORD for decision.
- ectl i_ectl_Q_N_tN: the 482 um G0 hop is q (320,640) -> to_um (133,935) (stale "chain source home"). The real consumers are the
  relay_polylines hst2_g / hst3_g starting at (320,640) (n3_rows.py: q->hst2_g 31 um, q->hst3_g 265 um). Fable's +1 station at
  (320,~900) would then sit 525 um from hst3_g. To verify in the hgi_v1 kit after place (where hst2_g/hst3_g land), not added yet.
- t36: added clk_t81 at (931.9,1390.0) (2-means split of t36 1651 -> 1132) and clk_t82 (258.5,1508.4) for clk_t19 1277 > 1200.
- Next: finish r4 rows (debug "no street path" skips on hg + hgi_v5/v6/v8 head2), private tree r4 (copy setup_r3.sh pattern), G0 +
  strict bind/LATCHECK, then gen_v1.sh on it (point SRC/TS at the r4 tree), diff config.mk vs D25e3 attempt_4, run to GRT it10.

## hgi_v1 proof kit (task 1)
- gen_v1.sh replays the wave stages of D25e3 attempt_4 (spec intel2 ~/coord/autopilot/kit_wave/qwen_kvsys_kv3_hgi_v1__cl141fc26e_b3da9709dc96e/a4/spec.json):
  kit-rtl (+post.d + closure inputs, rt 4e87ef58a95f), kit_topology prepare-stations, closure seal + relocate, gen.py phys with the spec
  gen_env verbatim (OT_SIGNED_VIEW_SHA = tree copy), OT_KIT_WAVE=1, --cland-pinslot all, region guide from-plan, spec gen_args, flow refresh
  (rt/current, gen+place). Wave kit attempt_4: placed 05:11, geom running at 05:37 (compare its GRT congestion when it routes).

## Cleanup (task 4, not done yet): ot-delete epyc10 fable-fix-kv-hgi/{b8,b8d} (2.7G/0.85G copies; live b8 runs on epyc7),
  epyc9 ft26_middle_0/gen_ft26_relayfit (119M unused; live relayfit is epyc10's), epyc8 opus-fix-kv-hgi-r3/ana/plan_try.json.
