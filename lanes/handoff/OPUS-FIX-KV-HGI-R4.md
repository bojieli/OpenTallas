# OPUS-FIX-KV-HGI-R4 handoff (Opus; KV hg/hgi family owner; successor of OPUS-FIX-KV-HGI-R3). CURRENT 2026-11-21 06:5x PST

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
